import { readFileSync } from 'fs';
import { Timestamp } from 'firebase-admin/firestore';
import { config } from '../config.js';
import { logger } from '../utils/logger.js';
import { chunk, delay, formatNumber, QuotaExhaustedError } from '../utils/helpers.js';
import { formatDuration } from '../utils/duration.js';
import { initializeFirebase } from '../firebase/client.js';
import {
  saveChannel,
  saveVideosBatch,
  getProgress,
  getAllProgress,
  getExistingVideoIds,
  getAllVideoIdsForChannel,
  getVideosMissingThumbnails,
  updateVideoThumbnailPaths,
  updateVideoStatsBatch,
  saveUnresolvedChannel,
  getUnresolvedChannel,
} from '../firebase/firestore.js';
import { resolveChannelUrl } from '../youtube/resolver.js';
import { getChannelDetails, transformChannelData, getUploadsPlaylistId } from '../youtube/channels.js';
import { getPlaylistVideos, getVideoDetails, transformVideoData, calculateVideoMetrics } from '../youtube/videos.js';
import { getQuotaUsed, getQuotaRemaining, isQuotaLow, markQuotaExhausted, setIgnoreQuota } from '../youtube/client.js';
import {
  getOrCreateProgress,
  updateProgressStatus,
  updateProgressVideos,
  updateProgressPhase,
  addProgressThumbnails,
  updateProgressForUpdate,
  updateProgressForRefresh,
  getProgressSummary,
  loadSavedQuota,
  saveQuotaToProgress,
} from './progress.js';
import { scanPageForNewIds } from './playlist-scan.js';
import { processThumbnailBatch, processChannelThumbnail } from './thumbnail.js';
import { ChannelsConfig, ChannelInput, Channel, Video, UnresolvedChannel } from '../types/index.js';

/**
 * Load channels configuration from file
 */
export function loadChannelsConfig(): ChannelsConfig {
  try {
    const content = readFileSync(config.paths.channelsConfig, 'utf-8');
    return JSON.parse(content) as ChannelsConfig;
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


// Failed channels are retried on later runs until they have failed this many times
const MAX_CHANNEL_RETRIES = 3;

// Thumbnail paths and counters are written to Firestore after each chunk
const THUMBNAIL_CHUNK_SIZE = 200;

/**
 * Resolve a channel URL to its ID, at most once per URL per run.
 * `knownChannelIds` is seeded from stored progress records (sourceUrl → channelId),
 * so channels seen before cost no quota to resolve.
 */
async function resolveChannelId(url: string, knownChannelIds: Map<string, string>): Promise<string> {
  const known = knownChannelIds.get(url);
  if (known) return known;

  logger.info(`Resolving URL: ${url}`);
  const resolved = await resolveChannelUrl(url);
  logger.success(`Resolved to channel ID: ${resolved.channelId} (${resolved.quotaCost} quota)`);
  knownChannelIds.set(url, resolved.channelId);
  return resolved.channelId;
}

/**
 * Channel metadata for --update/--refresh. Omits scrapedAt and thumbnailStoragePath
 * so saveChannel's merge keeps the values from the initial scrape.
 */
function toChannelUpdate(info: ReturnType<typeof transformChannelData>): Partial<Channel> & Pick<Channel, 'channelId'> {
  const { scrapedAt: _scrapedAt, ...update } = info;
  return update;
}

/**
 * Download thumbnails for every stored video of the channel that has none yet.
 * The work list comes from Firestore, so an interrupted run or earlier failures
 * are picked up next time. Returns the number downloaded in this call.
 */
async function downloadMissingThumbnails(
  channelId: string,
  settings: ChannelsConfig['settings']
): Promise<number> {
  const missing = await getVideosMissingThumbnails(channelId);
  const pending = settings.skipShortThumbnails ? missing.filter((v) => !v.isShort) : missing;

  if (pending.length < missing.length) {
    logger.info(`Skipping thumbnails for ${missing.length - pending.length} short(s)`);
  }
  if (pending.length === 0) return 0;

  logger.info(`Downloading ${pending.length} missing thumbnail(s)...`);
  let attempted = 0;
  let downloaded = 0;

  for (const ids of chunk(pending.map((v) => v.videoId), THUMBNAIL_CHUNK_SIZE)) {
    const results = await processThumbnailBatch(ids, channelId);
    const updates = results
      .filter((r) => r.success)
      .map((r) => ({ videoId: r.videoId, thumbnailStoragePath: r.storagePath! }));

    await updateVideoThumbnailPaths(channelId, updates);
    await addProgressThumbnails(channelId, updates.length);

    attempted += ids.length;
    downloaded += updates.length;
    logger.info(`Thumbnails: ${attempted}/${pending.length}`);
  }

  if (downloaded < attempted) {
    logger.warn(`${attempted - downloaded} thumbnail(s) failed; they will be retried on the next run`);
  }
  return downloaded;
}

/**
 * Process a single channel.
 * Resuming is idempotent: remaining work is derived from what is already stored in
 * Firestore (videos saved, thumbnails missing), not from in-memory state.
 */
export async function processChannel(
  input: ChannelInput,
  settings: ChannelsConfig['settings'],
  knownChannelIds: Map<string, string> = new Map()
): Promise<{
  success: boolean;
  channelId?: string;
  videosProcessed: number;
  thumbnailsDownloaded: number;
  error?: string;
}> {
  let channelId: string | undefined;
  let channelTitle: string | undefined;
  let channelVideoCount = 0;
  let videosProcessed = 0;
  let thumbnailsDownloaded = 0;

  try {
    // Step 1: Resolve channel URL to ID (free for channels seen in earlier runs)
    channelId = await resolveChannelId(input.url, knownChannelIds);

    // Step 2: Check for existing progress
    const existingProgress = await getProgress(channelId);

    if (existingProgress) {
      // Skip if already completed
      if (existingProgress.status === 'completed') {
        logger.info(`Channel already completed, skipping: ${channelId}`);
        return {
          success: true,
          channelId,
          videosProcessed: existingProgress.videosProcessed,
          thumbnailsDownloaded: existingProgress.thumbnailsDownloaded,
        };
      }

      if (existingProgress.status === 'failed' && existingProgress.retryCount >= MAX_CHANNEL_RETRIES) {
        logger.warn(`Channel failed ${existingProgress.retryCount} times, skipping: ${channelId} (last error: ${existingProgress.errorMessage})`);
        return {
          success: false,
          channelId,
          videosProcessed: existingProgress.videosProcessed,
          thumbnailsDownloaded: existingProgress.thumbnailsDownloaded,
          error: 'Retry limit reached',
        };
      }

      logger.info(`Resuming from previous progress (phase: ${existingProgress.phase})`);
      videosProcessed = existingProgress.videosProcessed;
      thumbnailsDownloaded = existingProgress.thumbnailsDownloaded;
    }

    // Step 3: Fetch channel details
    logger.info('Fetching channel details...');
    const channelData = await getChannelDetails(channelId);
    if (!channelData) {
      throw new Error('Channel not found');
    }

    const channelInfo = transformChannelData(channelData, input);
    channelTitle = channelInfo.channelTitle;
    channelVideoCount = channelInfo.videoCount;
    logger.success(`Channel: ${channelInfo.channelTitle}`);
    logger.stats({
      'Subscribers': channelInfo.subscriberCount !== null ? formatNumber(channelInfo.subscriberCount) : 'Hidden',
      'Total Videos': formatNumber(channelInfo.videoCount),
      'Total Views': formatNumber(channelInfo.viewCount),
    });

    // Step 4: Download and save channel thumbnail
    const channelThumbnailPath = await processChannelThumbnail(channelId, channelInfo.thumbnailUrl) || '';
    const channel: Channel = {
      ...channelInfo,
      thumbnailStoragePath: channelThumbnailPath,
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

    // Steps 6-7 are skipped once the video details phase has finished
    const detailsDone = existingProgress !== null && existingProgress.phase !== 'scraping';

    if (!detailsDone) {
      // Step 6: Fetch all video IDs from the uploads playlist (always from the first page,
      // so nothing collected before an interruption is lost)
      const uploadsPlaylistId = getUploadsPlaylistId(channelId);
      logger.info(`Fetching videos from playlist: ${uploadsPlaylistId}`);

      const maxVideos = settings.maxVideosPerChannel;
      let pageToken: string | null = null;
      let allVideoIds: string[] = [];

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

        logger.info(`Fetched ${allVideoIds.length}/${page.totalResults} video IDs`);

        if (!page.nextPageToken || (maxVideos && allVideoIds.length >= maxVideos)) break;
        pageToken = page.nextPageToken;

        await delay(config.scraper.apiDelayMs);
      }

      // Apply max videos limit if set
      if (maxVideos && allVideoIds.length > maxVideos) {
        allVideoIds = allVideoIds.slice(0, maxVideos);
      }

      logger.success(`Total video IDs from playlist: ${allVideoIds.length}`);

      // Skip videos already saved by an earlier (interrupted) run
      const storedIds = new Set(await getAllVideoIdsForChannel(channelId));
      const pendingIds = allVideoIds.filter((id) => !storedIds.has(id));
      videosProcessed = allVideoIds.length - pendingIds.length;
      if (videosProcessed > 0) {
        logger.info(`Resuming: ${videosProcessed} videos already stored, ${pendingIds.length} IDs remaining`);
      }

      const totalExpected = videosProcessed + pendingIds.length;

      // Step 7: Fetch video details in batches
      await updateProgressPhase(channelId, 'scraping');
      const videoChunks = chunk(pendingIds, config.scraper.batchSize);
      let videoIdsAttempted = 0;

      for (const batchIds of videoChunks) {
        if (isQuotaLow()) {
          logger.warn('Quota running low, saving progress...');
          const lastProcessedId = videoIdsAttempted > 0 ? pendingIds[videoIdsAttempted - 1] : null;
          await updateProgressVideos(channelId, videosProcessed, lastProcessedId, null);
          return {
            success: false,
            channelId,
            videosProcessed,
            thumbnailsDownloaded,
            error: 'Quota exhausted',
          };
        }

        const videoData = await getVideoDetails(batchIds);

        // Track attempted video IDs (includes deleted/private videos that API didn't return)
        videoIdsAttempted += batchIds.length;

        // Log if some videos were not returned (deleted/private)
        if (videoData.length < batchIds.length) {
          const missing = batchIds.length - videoData.length;
          logger.warn(`${missing} video(s) in batch were not returned (possibly deleted/private)`);
        }

        // Transform and filter
        const videos: Video[] = [];
        for (const data of videoData) {
          const video = transformVideoData(data, channelId, channel.subscriberCount);

          // Filter shorts if needed
          if (!settings.includeShorts && video.isShort) {
            continue;
          }

          videos.push({
            ...video,
            thumbnailStoragePath: '', // Filled in by the thumbnail phase
          });
        }

        videosProcessed += videos.length;

        // Save batch to Firestore
        await saveVideosBatch(channelId, videos);

        logger.info(`Processed ${videosProcessed}/~${totalExpected} videos (${videoIdsAttempted} IDs checked)`);
        await updateProgressVideos(channelId, videosProcessed, batchIds[batchIds.length - 1], null);

        await delay(config.scraper.apiDelayMs);
      }

      await updateProgressVideos(channelId, videosProcessed, null, null);
      await updateProgressPhase(channelId, 'thumbnails');
    }

    // Step 8: Download thumbnails for all stored videos that still lack one
    // (no YouTube API quota is used here)
    thumbnailsDownloaded += await downloadMissingThumbnails(channelId, settings);

    // Step 9: Mark as completed
    await updateProgressPhase(channelId, 'calculations');
    await updateProgressStatus(channelId, 'completed');

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
    if (error instanceof QuotaExhaustedError) {
      logger.warn('YouTube API reported the daily quota is exceeded');
      markQuotaExhausted();
      return { success: false, channelId, videosProcessed, thumbnailsDownloaded, error: 'Quota exhausted' };
    }

    const errorMessage = (error as Error).message;
    logger.error(`Failed: ${errorMessage}`);

    try {
      if (channelId) {
        // Channel resolved but failed later — save to scrape_progress
        // (an existing record is kept as-is; only status/error are updated)
        await getOrCreateProgress(channelId, channelTitle ?? input.url, input.url, channelVideoCount);
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

/**
 * Incrementally update a completed channel by fetching only new videos.
 * Exploits the fact that YouTube uploads playlists return newest videos first:
 * scanning stops at the first video that is already stored.
 */
export async function updateChannel(
  input: ChannelInput,
  settings: ChannelsConfig['settings'],
  knownChannelIds: Map<string, string> = new Map()
): Promise<{
  success: boolean;
  channelId?: string;
  newVideos: number;
  thumbnailsDownloaded: number;
  error?: string;
}> {
  let channelId: string | undefined;

  try {
    // Step 1: Resolve channel URL to ID (free for channels seen in earlier runs)
    channelId = await resolveChannelId(input.url, knownChannelIds);

    // Step 2: Only update completed channels
    const existingProgress = await getProgress(channelId);
    if (!existingProgress || existingProgress.status !== 'completed') {
      const reason = !existingProgress ? 'never scraped' : `status: ${existingProgress.status}`;
      logger.info(`Skipping update (${reason}): ${channelId}`);
      return { success: true, channelId, newVideos: 0, thumbnailsDownloaded: 0 };
    }

    // Step 3: Refresh channel metadata (subscriber count, video count, etc.)
    logger.info('Refreshing channel metadata...');
    const channelData = await getChannelDetails(channelId);
    if (!channelData) {
      throw new Error('Channel not found');
    }

    const channelInfo = transformChannelData(channelData, input);
    logger.success(`Channel: ${channelInfo.channelTitle}`);
    await saveChannel(toChannelUpdate(channelInfo));

    // Step 4: Scan playlist pages (newest first) until the first already-stored video
    const uploadsPlaylistId = getUploadsPlaylistId(channelId);
    logger.info(`Checking for new videos in playlist: ${uploadsPlaylistId}`);

    let pageToken: string | null = null;
    const newVideoIds: string[] = [];
    let scanned = 0;

    while (true) {
      if (isQuotaLow()) {
        logger.warn('Quota running low, stopping update...');
        break;
      }

      const page = await getPlaylistVideos(uploadsPlaylistId, pageToken || undefined);
      const items = page.items || [];
      const pageVideoIds = items.map((item) => item.videoId).filter((id): id is string => !!id);

      if (pageVideoIds.length === 0) break;

      const storedIds = await getExistingVideoIds(channelId, pageVideoIds);
      const scan = scanPageForNewIds(pageVideoIds, storedIds, scanned, settings.maxVideosPerChannel);
      scanned = scan.scanned;
      newVideoIds.push(...scan.newIds);

      if (scan.done) {
        logger.info(`Reached already-stored videos (or the per-channel limit) — stopping`);
        break;
      }

      logger.info(`Found ${scan.newIds.length} new video(s) on this page (${newVideoIds.length} total new)`);

      if (!page.nextPageToken) break;
      pageToken = page.nextPageToken;

      await delay(config.scraper.apiDelayMs);
    }

    if (newVideoIds.length === 0) {
      logger.info('No new videos found');
    } else {
      logger.success(`Found ${newVideoIds.length} new video(s) to process`);
    }

    // Step 5: Fetch video details for new IDs only
    const videoChunks = chunk(newVideoIds, config.scraper.batchSize);
    let newVideosSaved = 0;

    for (const batchIds of videoChunks) {
      if (isQuotaLow()) {
        logger.warn('Quota running low, saving partial update...');
        break;
      }

      const videoData = await getVideoDetails(batchIds);

      if (videoData.length < batchIds.length) {
        const missing = batchIds.length - videoData.length;
        logger.warn(`${missing} video(s) not returned (possibly deleted/private)`);
      }

      const videos: Video[] = [];
      for (const data of videoData) {
        const video = transformVideoData(data, channelId, channelInfo.subscriberCount);

        if (!settings.includeShorts && video.isShort) {
          continue;
        }

        videos.push({
          ...video,
          thumbnailStoragePath: '',
        });
      }

      newVideosSaved += videos.length;
      await saveVideosBatch(channelId, videos);

      await delay(config.scraper.apiDelayMs);
    }

    // Step 6: Download thumbnails for new videos and retry earlier failures
    const thumbnailsDownloaded = await downloadMissingThumbnails(channelId, settings);

    // Step 7: Update progress
    await updateProgressForUpdate(channelId, newVideosSaved, channelInfo.videoCount);

    logger.success(`Update complete: ${channelInfo.channelTitle}`);
    logger.stats({
      'New Videos': newVideosSaved,
      'Thumbnails': thumbnailsDownloaded,
      'Quota Used': `${getQuotaUsed()} / ${config.quota.dailyLimit}`,
    });

    return {
      success: true,
      channelId,
      newVideos: newVideosSaved,
      thumbnailsDownloaded,
    };
  } catch (error) {
    if (error instanceof QuotaExhaustedError) {
      logger.warn('YouTube API reported the daily quota is exceeded');
      markQuotaExhausted();
      return { success: false, channelId, newVideos: 0, thumbnailsDownloaded: 0, error: 'Quota exhausted' };
    }

    const errorMessage = (error as Error).message;
    logger.error(`Update failed: ${errorMessage}`);

    return {
      success: false,
      channelId,
      newVideos: 0,
      thumbnailsDownloaded: 0,
      error: errorMessage,
    };
  }
}

/**
 * Refresh stats (views, likes, comments) for all existing videos in a completed channel.
 * Reads video IDs from Firestore, batch-fetches current stats from YouTube API,
 * recalculates derived metrics, and writes only stats fields back to Firestore.
 * lastRefreshAt is only stamped when every batch succeeded.
 */
export async function refreshChannel(
  input: ChannelInput,
  settings: ChannelsConfig['settings'],
  knownChannelIds: Map<string, string> = new Map()
): Promise<{
  success: boolean;
  channelId?: string;
  videosRefreshed: number;
  error?: string;
}> {
  let channelId: string | undefined;
  let videosRefreshed = 0;

  try {
    // Step 1: Resolve channel URL to ID (free for channels seen in earlier runs)
    channelId = await resolveChannelId(input.url, knownChannelIds);

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

    await saveChannel(toChannelUpdate(channelInfo));

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
    let failedBatches = 0;
    let quotaStop = false;

    for (const wave of waves) {
      if (isQuotaLow()) {
        logger.warn('Quota running low, stopping refresh...');
        quotaStop = true;
        break;
      }

      const waveResults = await Promise.allSettled(
        wave.map((batchIds) => getVideoDetails(batchIds))
      );

      for (const result of waveResults) {
        if (result.status === 'rejected') {
          if (result.reason instanceof QuotaExhaustedError) {
            markQuotaExhausted();
            quotaStop = true;
          } else {
            logger.warn(`Batch fetch failed: ${result.reason}`);
            failedBatches++;
          }
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
      if (quotaStop) break;
      await delay(config.scraper.apiDelayMs);
    }

    if (quotaStop || failedBatches > 0) {
      const error = quotaStop ? 'Quota exhausted' : `${failedBatches} batch(es) failed`;
      logger.warn(`Partial refresh: ${videosRefreshed}/${allVideoIds.length} videos (${error}); lastRefreshAt not updated`);
      return { success: false, channelId, videosRefreshed, error };
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
    if (error instanceof QuotaExhaustedError) {
      logger.warn('YouTube API reported the daily quota is exceeded');
      markQuotaExhausted();
      return { success: false, channelId, videosRefreshed, error: 'Quota exhausted' };
    }

    const errorMessage = (error as Error).message;
    logger.error(`Refresh failed: ${errorMessage}`);
    return { success: false, channelId, videosRefreshed, error: errorMessage };
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

  // Seed URL → channelId from stored progress so known channels need no resolution quota
  const knownChannelIds = new Map<string, string>();
  for (const progress of await getAllProgress()) {
    if (progress.sourceUrl) knownChannelIds.set(progress.sourceUrl, progress.channelId);
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
  let lastChannelId: string | undefined;

  for (let i = 0; i < channelsConfig.channels.length; i++) {
    const channelInput = channelsConfig.channels[i];

    // Check quota before processing
    if (isQuotaLow()) {
      logger.warn('API quota nearly exhausted. Stopping.');
      break;
    }

    if (updateMode) {
      logger.subheader(`Updating [${i + 1}/${channelsConfig.channels.length}]: ${channelInput.url}`);
      const result = await updateChannel(channelInput, channelsConfig.settings, knownChannelIds);
      lastChannelId = result.channelId ?? lastChannelId;

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
      const refreshResult = await refreshChannel(channelInput, channelsConfig.settings, knownChannelIds);
      lastChannelId = refreshResult.channelId ?? lastChannelId;
      totalVideosRefreshed += refreshResult.videosRefreshed;

      if (refreshResult.success) {
        if (!updateMode) channelsProcessed++;
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
      const result = await processChannel(channelInput, channelsConfig.settings, knownChannelIds);
      lastChannelId = result.channelId ?? lastChannelId;

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

  // Persist quota spent this run (incl. URL resolution) so a same-day rerun starts from it
  if (lastChannelId) {
    await saveQuotaToProgress(lastChannelId);
  }

  // Print summary
  const duration = Date.now() - startTime;
  const videoLabel = updateMode ? 'New Videos Found' : refreshMode ? 'Videos Refreshed' : 'Videos Scraped';

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
