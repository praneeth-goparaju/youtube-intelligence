import { readFileSync } from 'fs';
import { Timestamp } from 'firebase-admin/firestore';
import { config } from '../config.js';
import { logger } from '../utils/logger.js';
import { chunk, delay, formatNumber } from '../utils/helpers.js';
import { formatDuration } from '../utils/duration.js';
import { initializeFirebase } from '../firebase/client.js';
import { saveChannel, saveVideosBatch, getProgress, getVideosByIds, getVideoCount, getThumbnailCount, getAllVideoIdsForChannel, updateVideoStatsBatch, saveUnresolvedChannel, getUnresolvedChannel } from '../firebase/firestore.js';
import { resolveChannelUrl } from '../youtube/resolver.js';
import { getChannelDetails, transformChannelData, getUploadsPlaylistId } from '../youtube/channels.js';
import { getPlaylistVideos, getVideoDetails, calculateVideoMetrics } from '../youtube/videos.js';
import { getQuotaUsed, getQuotaRemaining, isQuotaLow, setIgnoreQuota } from '../youtube/client.js';
import {
  getOrCreateProgress,
  updateProgressStatus,
  updateProgressVideos,
  updateProgressPhase,
  updateProgressThumbnails,
  updateProgressForUpdate,
  updateProgressForRefresh,
  getProgressSummary,
  loadSavedQuota,
  saveQuotaToProgress,
  completeProgress,
} from './progress.js';
import { processThumbnailBatch, processChannelThumbnail } from './thumbnail.js';
import { transformAndFilterVideos, applyThumbnailPaths } from './video-processing.js';
import { ChannelsConfig, ChannelInput, UnresolvedChannel } from '../types/index.js';

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

export function parseChannelsConfig(value: unknown): ChannelsConfig {
  if (!isRecord(value) || !Array.isArray(value.channels) || !isRecord(value.settings)) {
    throw new Error('Channels configuration must contain a channels array and settings object');
  }
  const channels: ChannelInput[] = value.channels.map((channel: unknown, index: number) => {
    if (!isRecord(channel) || typeof channel.url !== 'string' || channel.url.trim() === '' ||
      typeof channel.category !== 'string' || channel.category.trim() === '' ||
      typeof channel.priority !== 'number' || !Number.isInteger(channel.priority) || channel.priority < 1 || channel.priority > 3) {
      throw new Error(`Invalid channel at index ${index}: expected a URL, category, and priority from 1 to 3`);
    }
    return { url: channel.url, category: channel.category, priority: channel.priority };
  });
  const { maxVideosPerChannel = null, includeShorts = false, includePrivate = false, skipShortThumbnails = false } = value.settings;
  if (maxVideosPerChannel !== null && (typeof maxVideosPerChannel !== 'number' || !Number.isInteger(maxVideosPerChannel) || maxVideosPerChannel <= 0)) {
    throw new Error('maxVideosPerChannel must be null or a positive integer');
  }
  if (typeof includeShorts !== 'boolean' || typeof includePrivate !== 'boolean' || typeof skipShortThumbnails !== 'boolean') {
    throw new Error('includeShorts, includePrivate, and skipShortThumbnails must be booleans');
  }
  return { channels, settings: { maxVideosPerChannel, includeShorts, includePrivate, skipShortThumbnails } };
}

/**
 * Load channels configuration from file
 */
export function loadChannelsConfig(): ChannelsConfig {
  try {
    const content = readFileSync(config.paths.channelsConfig, 'utf-8');
    return parseChannelsConfig(JSON.parse(content));
  } catch (error) {
    const err = error as NodeJS.ErrnoException;
    if (err.code === 'ENOENT') {
      throw new Error(`Channels configuration file not found: ${config.paths.channelsConfig}. Please create a channels.json file in the config directory.`);
    }
    if (error instanceof SyntaxError) {
      throw new Error(`Invalid JSON in channels configuration file: ${error.message}`);
    }
    throw new Error(`Failed to load channels configuration: ${err.message}`);
  }
}

/**
 * Derive a stable Firestore-safe ID from a channel URL for logging failures
 * when the channelId couldn't be resolved.
 */
function urlToProgressId(url: string): string {
  try {
    const u = new URL(url);
    return u.pathname.replace(/^\//, '').replace(/\//g, '_') || 'unknown';
  } catch {
    return url.replace(/[^a-zA-Z0-9@_-]/g, '_').slice(0, 100) || 'unknown';
  }
}

/** Process durable metadata and any missing thumbnails before advancing progress. */
async function processVideoBatch(
  channelId: string,
  videoIds: string[],
  subscriberCount: number | null,
  settings: ChannelsConfig['settings']
): Promise<{ newVideos: number; thumbnailsDownloaded: number; failedThumbnails: number }> {
  const existingVideos = await getVideosByIds(channelId, videoIds);
  const existingIds = new Set(existingVideos.map((video) => video.videoId));
  const missingIds = videoIds.filter((id) => !existingIds.has(id));
  const videoData = missingIds.length > 0 ? await getVideoDetails(missingIds) : [];
  const newVideos = transformAndFilterVideos(videoData, channelId, subscriberCount, settings.includeShorts);
  await saveVideosBatch(channelId, newVideos);

  const pendingThumbnails = [...existingVideos, ...newVideos].filter((video) =>
    !video.thumbnailStoragePath &&
    (settings.includeShorts || !video.isShort) &&
    (!settings.skipShortThumbnails || !video.isShort)
  );
  const results = await processThumbnailBatch(pendingThumbnails.map((video) => video.videoId), channelId);
  applyThumbnailPaths(pendingThumbnails, results);
  await saveVideosBatch(channelId, pendingThumbnails);

  return {
    newVideos: newVideos.length,
    thumbnailsDownloaded: results.filter((result) => result.success).length,
    failedThumbnails: results.filter((result) => !result.success).length,
  };
}

/**
 * Process a single channel
 */
export async function processChannel(
  input: ChannelInput,
  settings: ChannelsConfig['settings']
): Promise<{
  success: boolean;
  channelId?: string;
  videosProcessed: number;
  thumbnailsDownloaded: number;
  error?: string;
}> {
  let channelId: string | undefined;
  let videosProcessed = 0;
  let thumbnailsDownloaded = 0;

  try {
    // Step 1: Resolve channel URL to ID
    logger.info(`Resolving URL: ${input.url}`);
    const resolved = await resolveChannelUrl(input.url);
    channelId = resolved.channelId;
    logger.success(`Resolved to channel ID: ${channelId} (${resolved.quotaCost} quota)`);

    // Step 2: Check for existing progress
    const existingProgress = await getProgress(channelId);
    if (existingProgress?.status === 'completed' && existingProgress.lastCompletedPlaylistVideoId !== undefined) {
      logger.info(`Channel already completed, skipping: ${channelId}`);
      return {
        success: true, channelId,
        videosProcessed: existingProgress.videosProcessed,
        thumbnailsDownloaded: existingProgress.thumbnailsDownloaded,
      };
    }

    // Older checkpoints may refer to unsaved IDs or unfinished thumbnails.
    // Re-enumerate from the beginning and skip only work present in Firestore.
    videosProcessed = await getVideoCount(channelId);
    thumbnailsDownloaded = await getThumbnailCount(channelId);

    // Step 3: Fetch channel details
    logger.info('Fetching channel details...');
    const channelData = await getChannelDetails(channelId);
    if (!channelData) {
      throw new Error('Channel not found');
    }

    const channelInfo = transformChannelData(channelData, input);
    logger.success(`Channel: ${channelInfo.channelTitle}`);
    logger.stats({
      'Subscribers': channelInfo.subscriberCount !== null ? formatNumber(channelInfo.subscriberCount) : 'Hidden',
      'Total Videos': formatNumber(channelInfo.videoCount),
      'Total Views': formatNumber(channelInfo.viewCount),
    });

    // Step 4: Download and save channel thumbnail
    const channelThumbnailPath = await processChannelThumbnail(channelId, channelInfo.thumbnailUrl);
    const channel = {
      ...channelInfo,
      ...(channelThumbnailPath ? { thumbnailStoragePath: channelThumbnailPath } : {}),
    };
    await saveChannel(channel);

    // Step 5: Initialize or update progress
    await getOrCreateProgress(
      channelId,
      channel.channelTitle,
      input.url,
      channel.videoCount
    );

    await updateProgressStatus(channelId, 'in_progress');

    // Step 6: Fetch all videos from uploads playlist
    const uploadsPlaylistId = getUploadsPlaylistId(channelId);
    logger.info(`Fetching videos from playlist: ${uploadsPlaylistId}`);

    let pageToken: string | null = null;
    let allVideoIds: string[] = [];
    let totalFetched = 0;

    // Get playlist pages
    while (true) {
      if (isQuotaLow()) {
        logger.warn('Quota running low, saving progress...');
        await updateProgressVideos(channelId, videosProcessed, null, null);
        return {
          success: false,
          channelId,
          videosProcessed,
          thumbnailsDownloaded,
          error: 'Quota exhausted',
        };
      }

      const page = await getPlaylistVideos(uploadsPlaylistId, pageToken || undefined);
      const items = page.items || [];
      const videoIds = items.map((item) => item.videoId).filter((id): id is string => !!id);
      allVideoIds.push(...videoIds);
      totalFetched += videoIds.length;

      logger.info(`Fetched ${totalFetched}/${page.totalResults} video IDs`);

      if (!page.nextPageToken || (settings.maxVideosPerChannel !== null && totalFetched >= settings.maxVideosPerChannel)) break;
      pageToken = page.nextPageToken;

      await delay(config.scraper.apiDelayMs);
    }

    // Apply max videos limit if set
    if (settings.maxVideosPerChannel && allVideoIds.length > settings.maxVideosPerChannel) {
      allVideoIds = allVideoIds.slice(0, settings.maxVideosPerChannel);
    }

    logger.success(`Total video IDs from playlist: ${allVideoIds.length}`);

    await updateProgressPhase(channelId, 'scraping');
    const videoChunks = chunk(allVideoIds, config.scraper.batchSize);
    for (const batchIds of videoChunks) {
      if (isQuotaLow()) {
        await saveQuotaToProgress(channelId);
        return { success: false, channelId, videosProcessed, thumbnailsDownloaded, error: 'Quota exhausted' };
      }

      const result = await processVideoBatch(channelId, batchIds, channel.subscriberCount, settings);
      videosProcessed += result.newVideos;
      thumbnailsDownloaded += result.thumbnailsDownloaded;
      await updateProgressVideos(channelId, videosProcessed, batchIds.at(-1) ?? null, null);
      await updateProgressThumbnails(channelId, thumbnailsDownloaded);
      if (result.failedThumbnails > 0) {
        throw new Error(`${result.failedThumbnails} thumbnail(s) failed; run again to retry them`);
      }
      logger.info(`Saved ${videosProcessed} videos and ${thumbnailsDownloaded} thumbnails`);
      await delay(config.scraper.apiDelayMs);
    }

    await updateProgressPhase(channelId, 'calculations');
    await completeProgress(channelId, allVideoIds[0] ?? null);

    logger.success(`Completed: ${channel.channelTitle}`);
    logger.stats({
      'Videos': formatNumber(videosProcessed),
      'Thumbnails': formatNumber(thumbnailsDownloaded),
      'Quota Used': `${getQuotaUsed()} / ${config.quota.dailyLimit}`,
    });

    return {
      success: true,
      channelId,
      videosProcessed,
      thumbnailsDownloaded,
    };
  } catch (error) {
    const errorMessage = (error as Error).message;
    logger.error(`Failed: ${errorMessage}`);

    try {
      if (channelId) {
        // Channel resolved but failed later — save to scrape_progress
        await getOrCreateProgress(channelId, input.url, input.url, 0);
        await updateProgressStatus(channelId, 'failed', errorMessage);
      } else {
        // URL resolution failed — save to unresolved_channels
        const unresolvedId = urlToProgressId(input.url);
        const existing = await getUnresolvedChannel(unresolvedId);
        const now = Timestamp.now();

        const entry: UnresolvedChannel = {
          id: unresolvedId,
          sourceUrl: input.url,
          errorMessage,
          retryCount: existing ? existing.retryCount + 1 : 1,
          firstSeenAt: existing?.firstSeenAt ?? now,
          lastAttemptAt: now,
        };
        await saveUnresolvedChannel(entry);
        logger.info(`Saved to unresolved_channels: ${unresolvedId}`);
      }
    } catch (saveError) {
      logger.warn(`Could not save failure to Firebase: ${(saveError as Error).message}`);
    }

    return {
      success: false,
      channelId,
      videosProcessed,
      thumbnailsDownloaded,
      error: errorMessage,
    };
  }
}

/** Fetch videos since the last fully completed playlist scan. */
export async function updateChannel(
  input: ChannelInput,
  settings: ChannelsConfig['settings']
): Promise<{
  success: boolean;
  channelId?: string;
  newVideos: number;
  thumbnailsDownloaded: number;
  error?: string;
}> {
  let channelId: string | undefined;
  let newVideos = 0;
  let thumbnailsDownloaded = 0;
  try {
    const resolved = await resolveChannelUrl(input.url);
    channelId = resolved.channelId;
    const existingProgress = await getProgress(channelId);
    if (!existingProgress || existingProgress.status !== 'completed') {
      logger.info(`Skipping update for a channel that has not completed its initial scrape: ${channelId}`);
      return { success: true, channelId, newVideos, thumbnailsDownloaded };
    }

    const channelData = await getChannelDetails(channelId);
    if (!channelData) throw new Error('Channel not found');
    const channel = transformChannelData(channelData, input);
    await saveChannel(channel);

    const completedVideoId = existingProgress.lastCompletedPlaylistVideoId;
    let firstVideoId: string | null = null;
    let pageToken: string | null = null;
    const candidateIds: string[] = [];
    do {
      if (isQuotaLow()) {
        await saveQuotaToProgress(channelId);
        return { success: false, channelId, newVideos, thumbnailsDownloaded, error: 'Quota exhausted' };
      }
      const page = await getPlaylistVideos(getUploadsPlaylistId(channelId), pageToken ?? undefined);
      const ids = page.items.map((item) => item.videoId).filter(Boolean);
      if (firstVideoId === null) firstVideoId = ids[0] ?? null;
      const completedIndex = completedVideoId ? ids.indexOf(completedVideoId) : -1;
      candidateIds.push(...(completedIndex >= 0 ? ids.slice(0, completedIndex) : ids));
      if (completedIndex >= 0) break;
      pageToken = page.nextPageToken;
      if (pageToken) await delay(config.scraper.apiDelayMs);
    } while (pageToken);

    for (const batchIds of chunk(candidateIds, config.scraper.batchSize)) {
      if (isQuotaLow()) {
        await saveQuotaToProgress(channelId);
        return { success: false, channelId, newVideos, thumbnailsDownloaded, error: 'Quota exhausted' };
      }
      const result = await processVideoBatch(channelId, batchIds, channel.subscriberCount, settings);
      newVideos += result.newVideos;
      thumbnailsDownloaded += result.thumbnailsDownloaded;
      if (result.failedThumbnails > 0) {
        throw new Error(`${result.failedThumbnails} thumbnail(s) failed; run again to retry them`);
      }
      await saveQuotaToProgress(channelId);
      await delay(config.scraper.apiDelayMs);
    }

    await updateProgressForUpdate(channelId, newVideos, channel.videoCount, firstVideoId);
    logger.success(`Update complete: ${channel.channelTitle} (${newVideos} new videos)`);
    return { success: true, channelId, newVideos, thumbnailsDownloaded };
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    logger.error(`Update failed: ${errorMessage}`);
    return { success: false, channelId, newVideos, thumbnailsDownloaded, error: errorMessage };
  }
}

/**
 * Refresh stats (views, likes, comments) for all existing videos in a completed channel.
 * Reads video IDs from Firestore, batch-fetches current stats from YouTube API,
 * recalculates derived metrics, and writes only stats fields back to Firestore.
 */
export async function refreshChannel(
  input: ChannelInput,
  settings: ChannelsConfig['settings']
): Promise<{
  success: boolean;
  channelId?: string;
  videosRefreshed: number;
  error?: string;
}> {
  let channelId: string | undefined;

  try {
    // Step 1: Resolve channel URL to ID
    logger.info(`Resolving URL: ${input.url}`);
    const resolved = await resolveChannelUrl(input.url);
    channelId = resolved.channelId;
    logger.success(`Resolved to channel ID: ${channelId} (${resolved.quotaCost} quota)`);

    // Step 2: Only refresh completed channels
    const existingProgress = await getProgress(channelId);
    if (!existingProgress || existingProgress.status !== 'completed') {
      const reason = !existingProgress ? 'never scraped' : `status: ${existingProgress.status}`;
      logger.info(`Skipping refresh (${reason}): ${channelId}`);
      return { success: true, channelId, videosRefreshed: 0 };
    }

    // Step 3: Refresh channel metadata (subscriber count needed for viewsPerSubscriber)
    logger.info('Refreshing channel metadata...');
    const channelData = await getChannelDetails(channelId);
    if (!channelData) {
      throw new Error('Channel not found');
    }

    const channelInfo = transformChannelData(channelData, input);
    const subscriberCount = channelInfo.subscriberCount;
    logger.success(`Channel: ${channelInfo.channelTitle} (${subscriberCount !== null ? formatNumber(subscriberCount) + ' subs' : 'subs hidden'})`);

    await saveChannel(channelInfo);

    // Step 4: Get all existing video IDs from Firestore
    logger.info('Fetching video IDs from Firestore...');
    const allVideoIds = await getAllVideoIdsForChannel(channelId);
    logger.success(`Found ${allVideoIds.length} videos to refresh`);

    if (allVideoIds.length === 0) {
      await updateProgressForRefresh(channelId, 0);
      return { success: true, channelId, videosRefreshed: 0 };
    }

    // Step 5: Fetch current stats from YouTube API in batches of 50,
    // running up to 5 concurrent requests per wave to speed up refresh
    const CONCURRENT_BATCHES = 5;
    const videoChunks = chunk(allVideoIds, config.scraper.batchSize);
    const waves = chunk(videoChunks, CONCURRENT_BATCHES);
    let videosRefreshed = 0;
    let failedBatches = 0;
    let quotaExhausted = false;

    for (const wave of waves) {
      if (isQuotaLow()) {
        logger.warn('Quota running low, stopping refresh...');
        quotaExhausted = true;
        break;
      }

      const waveResults = await Promise.allSettled(
        wave.map((batchIds) => getVideoDetails(batchIds))
      );

      for (const result of waveResults) {
        if (result.status === 'rejected') {
          failedBatches++;
          logger.warn(`Batch fetch failed: ${result.reason}`);
          continue;
        }

        const updates = result.value.map((data) => {
          const viewCount = parseInt(data.statistics.viewCount, 10) || 0;
          const likeCount = parseInt(data.statistics.likeCount, 10) || 0;
          const commentCount = parseInt(data.statistics.commentCount, 10) || 0;
          const publishedAt = new Date(data.snippet.publishedAt);
          const tags = data.snippet.tags || [];

          const calculated = calculateVideoMetrics(
            { publishedAt, viewCount, likeCount, commentCount, tags },
            subscriberCount
          );

          return {
            videoId: data.id,
            viewCount,
            likeCount,
            commentCount,
            calculated,
            statsRefreshedAt: Timestamp.now(),
          };
        });

        await updateVideoStatsBatch(channelId, updates);
        videosRefreshed += updates.length;
      }

      logger.info(`Refreshed ${videosRefreshed}/${allVideoIds.length} videos`);
      await delay(config.scraper.apiDelayMs);
    }

    if (quotaExhausted || failedBatches > 0) {
      await saveQuotaToProgress(channelId);
      return {
        success: false, channelId, videosRefreshed,
        error: quotaExhausted ? 'Quota exhausted' : `${failedBatches} video batch(es) failed to refresh`,
      };
    }

    // Step 6: Update progress
    await updateProgressForRefresh(channelId, videosRefreshed);

    logger.success(`Refresh complete: ${channelInfo.channelTitle}`);
    logger.stats({
      'Videos Refreshed': formatNumber(videosRefreshed),
      'Quota Used': `${getQuotaUsed()} / ${config.quota.dailyLimit}`,
    });

    return { success: true, channelId, videosRefreshed };
  } catch (error) {
    const errorMessage = (error as Error).message;
    logger.error(`Refresh failed: ${errorMessage}`);
    return { success: false, channelId, videosRefreshed: 0, error: errorMessage };
  }
}

/**
 * Run the main scraper
 */
export async function runScraper(options: { updateMode?: boolean; refreshMode?: boolean; ignoreQuota?: boolean } = {}): Promise<void> {
  const { updateMode = false, refreshMode = false, ignoreQuota = false } = options;
  const startTime = Date.now();

  const modeLabel = refreshMode && updateMode ? 'Incremental Update + Stats Refresh'
    : refreshMode ? 'Stats Refresh'
    : updateMode ? 'Incremental Update'
    : 'Data Collection';

  logger.header('YouTube Intelligence System v1.0');
  logger.info(`Phase 1: ${modeLabel}`);
  logger.divider();

  // Initialize Firebase
  logger.info('Initializing Firebase...');
  initializeFirebase();
  logger.success('Connected to Firebase');

  // Load channels config
  logger.info('Loading channels configuration...');
  const channelsConfig = loadChannelsConfig();
  logger.success(`Loaded ${channelsConfig.channels.length} channels`);

  // Get progress summary
  const progressSummary = await getProgressSummary();
  logger.info('Progress Status:');
  logger.stats({
    'Completed': progressSummary.completed,
    'In Progress': progressSummary.inProgress,
    'Pending': progressSummary.pending,
    'Failed': progressSummary.failed,
    'Total Videos Scraped': formatNumber(progressSummary.totalVideos),
  });

  // Apply ignore-quota flag
  if (ignoreQuota) {
    setIgnoreQuota(true);
    logger.warn('--ignore-quota: skipping saved quota restoration and disabling quota checks');
  }

  // Load saved quota from previous session (if same day)
  if (!ignoreQuota) {
    const savedQuota = await loadSavedQuota();
    if (savedQuota > 0) {
      logger.info(`Restored quota usage from earlier today: ${formatNumber(savedQuota)} units`);
    }
  }

  logger.divider();
  logger.info(`API Quota: ${formatNumber(getQuotaRemaining())} units available`);
  logger.divider();

  // Process channels
  let totalVideos = 0;
  let totalThumbnails = 0;
  let totalVideosRefreshed = 0;
  let channelsProcessed = 0;
  let channelsFailed = 0;

  for (let i = 0; i < channelsConfig.channels.length; i++) {
    const channelInput = channelsConfig.channels[i];

    // Check quota before processing
    if (isQuotaLow()) {
      logger.warn('API quota nearly exhausted. Stopping.');
      break;
    }

    if (updateMode) {
      logger.subheader(`Updating [${i + 1}/${channelsConfig.channels.length}]: ${channelInput.url}`);
      const result = await updateChannel(channelInput, channelsConfig.settings);

      if (result.success) {
        channelsProcessed++;
        totalVideos += result.newVideos;
        totalThumbnails += result.thumbnailsDownloaded;
      } else {
        if (result.error === 'Quota exhausted') {
          logger.warn('Stopping due to quota exhaustion.');
          break;
        }
        channelsFailed++;
      }
    }

    if (refreshMode) {
      if (isQuotaLow()) {
        logger.warn('API quota nearly exhausted. Stopping refresh.');
        break;
      }

      logger.subheader(`Refreshing [${i + 1}/${channelsConfig.channels.length}]: ${channelInput.url}`);
      const refreshResult = await refreshChannel(channelInput, channelsConfig.settings);

      if (refreshResult.success) {
        if (!updateMode) channelsProcessed++;
        totalVideosRefreshed += refreshResult.videosRefreshed;
      } else {
        if (refreshResult.error === 'Quota exhausted') {
          logger.warn('Stopping due to quota exhaustion.');
          break;
        }
        if (!updateMode) channelsFailed++;
      }
    }

    if (!updateMode && !refreshMode) {
      logger.subheader(`Processing [${i + 1}/${channelsConfig.channels.length}]: ${channelInput.url}`);
      const result = await processChannel(channelInput, channelsConfig.settings);

      if (result.success) {
        channelsProcessed++;
        totalVideos += result.videosProcessed;
        totalThumbnails += result.thumbnailsDownloaded;
      } else {
        if (result.error === 'Quota exhausted') {
          logger.warn('Stopping due to quota exhaustion.');
          break;
        }
        channelsFailed++;
      }
    }

    logger.divider();
  }

  // Print summary
  const duration = Date.now() - startTime;
  const summaryStats: Record<string, string | number> = {
    'Duration': formatDuration(Math.floor(duration / 1000)),
    'Channels Processed': `${channelsProcessed}/${channelsConfig.channels.length}`,
    'Channels Failed': channelsFailed,
  };

  if (updateMode) {
    summaryStats['New Videos Found'] = formatNumber(totalVideos);
    summaryStats['Thumbnails Downloaded'] = formatNumber(totalThumbnails);
  }

  if (refreshMode) {
    summaryStats['Videos Refreshed'] = formatNumber(totalVideosRefreshed);
  }

  if (!updateMode && !refreshMode) {
    summaryStats['Videos Scraped'] = formatNumber(totalVideos);
    summaryStats['Thumbnails Downloaded'] = formatNumber(totalThumbnails);
  }

  summaryStats['API Quota Used'] = `${formatNumber(getQuotaUsed())} / ${formatNumber(config.quota.dailyLimit)}`;
  summaryStats['API Quota Remaining'] = formatNumber(getQuotaRemaining());

  logger.header('Session Summary');
  logger.stats(summaryStats);

  logger.divider();

  if (getQuotaRemaining() < config.scraper.quotaWarningThreshold) {
    logger.warn('Quota nearly exhausted. Run again after midnight Pacific Time.');
  } else if (channelsProcessed < channelsConfig.channels.length) {
    const flags = [updateMode && '--update', refreshMode && '--refresh'].filter(Boolean).join(' ');
    logger.info(`More channels to process. Run again: npm start${flags ? ` -- ${flags}` : ''}`);
  } else if (refreshMode) {
    logger.success('All channels refreshed!');
  } else if (updateMode) {
    logger.success('All channels updated!');
  } else {
    logger.success('All channels processed! Proceed to Phase 2: cd analyzer && python -m src.main');
  }
}
