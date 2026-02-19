import { readFileSync } from 'fs';
import { Timestamp } from 'firebase-admin/firestore';
import { config } from '../config.js';
import { logger } from '../utils/logger.js';
import { chunk, delay, formatNumber } from '../utils/helpers.js';
import { formatDuration } from '../utils/duration.js';
import { initializeFirebase } from '../firebase/client.js';
import { saveChannel, saveVideosBatch, saveProgress, getProgress, getExistingVideoIds, saveUnresolvedChannel, getUnresolvedChannel } from '../firebase/firestore.js';
import { resolveChannelUrl } from '../youtube/resolver.js';
import { getChannelDetails, transformChannelData, getUploadsPlaylistId } from '../youtube/channels.js';
import { getPlaylistVideos, getVideoDetails, transformVideoData } from '../youtube/videos.js';
import { getQuotaUsed, getQuotaRemaining, isQuotaLow, setQuotaUsed, setIgnoreQuota } from '../youtube/client.js';
import {
  getOrCreateProgress,
  updateProgressStatus,
  updateProgressVideos,
  updateProgressPhase,
  updateProgressThumbnails,
  updateProgressForUpdate,
  getProgressSummary,
  loadSavedQuota,
} from './progress.js';
import { processThumbnailBatch, processChannelThumbnail } from './thumbnail.js';
import { ChannelsConfig, ChannelInput, Channel, Video, ScrapeProgress, UnresolvedChannel } from '../types/index.js';

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
  let videosProcessed = 0;  // Will be set from resume state if resuming
  let thumbnailsDownloaded = 0;  // Will be set from resume state if resuming

  try {
    // Step 1: Resolve channel URL to ID
    logger.info(`Resolving URL: ${input.url}`);
    const resolved = await resolveChannelUrl(input.url);
    channelId = resolved.channelId;
    logger.success(`Resolved to channel ID: ${channelId} (${resolved.quotaCost} quota)`);

    // Step 2: Check for existing progress
    const existingProgress = await getProgress(channelId);
    let resumeFromToken: string | null = null;
    let resumeFromVideoCount = 0;
    let resumeFromThumbnailCount = 0;

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

      // Resume from previous progress
      logger.info(`Resuming from previous progress: ${existingProgress.videosProcessed} videos processed`);
      resumeFromToken = existingProgress.lastPlaylistPageToken;
      resumeFromVideoCount = existingProgress.videosProcessed;
      resumeFromThumbnailCount = existingProgress.thumbnailsDownloaded;

      // Initialize counts from resume state
      videosProcessed = resumeFromVideoCount;
      thumbnailsDownloaded = resumeFromThumbnailCount;
    }

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
    const channelThumbnailPath = await processChannelThumbnail(channelId, channelInfo.thumbnailUrl) || '';
    const channel: Channel = {
      ...channelInfo,
      thumbnailStoragePath: channelThumbnailPath,
    };
    await saveChannel(channel);

    // Step 5: Initialize or update progress
    const progress = await getOrCreateProgress(
      channelId,
      channel.channelTitle,
      input.url,
      channel.videoCount
    );

    await updateProgressStatus(channelId, 'in_progress');

    // Step 6: Fetch all videos from uploads playlist
    const uploadsPlaylistId = getUploadsPlaylistId(channelId);
    logger.info(`Fetching videos from playlist: ${uploadsPlaylistId}`);

    let pageToken = resumeFromToken;
    let allVideoIds: string[] = [];
    let totalFetched = 0;

    // Get playlist pages
    while (true) {
      if (isQuotaLow()) {
        logger.warn('Quota running low, saving progress...');
        await updateProgressVideos(channelId, videosProcessed, null, pageToken);
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

      if (!page.nextPageToken) break;
      pageToken = page.nextPageToken;

      await delay(config.scraper.apiDelayMs);
    }

    // Apply max videos limit if set
    if (settings.maxVideosPerChannel && allVideoIds.length > settings.maxVideosPerChannel) {
      allVideoIds = allVideoIds.slice(0, settings.maxVideosPerChannel);
    }

    logger.success(`Total video IDs from playlist: ${allVideoIds.length}`);

    // If resuming without a page token, we re-fetched all IDs from scratch.
    // Skip IDs already processed to avoid duplicate work and inflated counts.
    if (resumeFromVideoCount > 0 && resumeFromToken === null && existingProgress?.lastProcessedVideoId) {
      const lastProcessedId = existingProgress.lastProcessedVideoId;
      const lastIdx = allVideoIds.indexOf(lastProcessedId);
      if (lastIdx >= 0) {
        const alreadyChecked = lastIdx + 1;
        allVideoIds = allVideoIds.slice(alreadyChecked);
        logger.info(`Resuming: skipping ${alreadyChecked} already-checked IDs, ${allVideoIds.length} remaining`);
      } else {
        // lastProcessedVideoId not found in list — reset counter to avoid inflation
        logger.warn(`Resume marker video not found in playlist, reprocessing all IDs`);
        videosProcessed = 0;
      }
    }

    const totalExpected = videosProcessed + allVideoIds.length;

    // Step 7: Fetch video details in batches
    await updateProgressPhase(channelId, 'scraping');
    const videoChunks = chunk(allVideoIds, config.scraper.batchSize);
    const allVideos: Video[] = [];

    // Track how many video IDs we've attempted to fetch (for progress tracking)
    let videoIdsAttempted = 0;

    for (let i = 0; i < videoChunks.length; i++) {
      if (isQuotaLow()) {
        logger.warn('Quota running low, saving progress...');
        // Use the last video ID from completed batches
        const lastProcessedId = videoIdsAttempted > 0 ? allVideoIds[videoIdsAttempted - 1] : null;
        await updateProgressVideos(channelId, videosProcessed, lastProcessedId, null);
        return {
          success: false,
          channelId,
          videosProcessed,
          thumbnailsDownloaded,
          error: 'Quota exhausted',
        };
      }

      const batchIds = videoChunks[i];
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
          thumbnailStoragePath: '', // Will be updated later
        });
      }

      allVideos.push(...videos);
      videosProcessed += videos.length;

      // Save batch to Firestore
      await saveVideosBatch(channelId, videos);

      logger.info(`Processed ${videosProcessed}/~${totalExpected} videos (${videoIdsAttempted} IDs checked)`);
      const lastBatchVideoId = batchIds.length > 0 ? batchIds[batchIds.length - 1] : null;
      await updateProgressVideos(channelId, videosProcessed, lastBatchVideoId, null);

      await delay(config.scraper.apiDelayMs);
    }

    // Step 8: Download thumbnails
    await updateProgressPhase(channelId, 'thumbnails');
    logger.info('Downloading thumbnails...');

    const videosForThumbnails = settings.skipShortThumbnails
      ? allVideos.filter((v) => !v.isShort)
      : allVideos;

    if (videosForThumbnails.length < allVideos.length) {
      logger.info(`Skipping thumbnails for ${allVideos.length - videosForThumbnails.length} short(s)`);
    }

    const thumbnailResults = await processThumbnailBatch(
      videosForThumbnails.map((v) => v.videoId),
      channelId,
      (processed, total) => {
        if (processed % 50 === 0 || processed === total) {
          logger.info(`Thumbnails: ${processed}/${total}`);
        }
      }
    );

    thumbnailsDownloaded = thumbnailResults.filter((r) => r.success).length;
    await updateProgressThumbnails(channelId, thumbnailsDownloaded);

    // Update videos with thumbnail paths
    const thumbnailPathMap = new Map(
      thumbnailResults.filter((r) => r.success).map((r) => [r.videoId, r.storagePath!])
    );

    for (const video of videosForThumbnails) {
      const path = thumbnailPathMap.get(video.videoId);
      if (path) {
        video.thumbnailStoragePath = path;
      }
    }

    // Save updated videos with thumbnail paths
    await saveVideosBatch(channelId, videosForThumbnails);

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

/**
 * Incrementally update a completed channel by fetching only new videos.
 * Exploits the fact that YouTube uploads playlists return newest videos first.
 * Stops fetching playlist pages once an entire page consists of already-known videos.
 */
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

  try {
    // Step 1: Resolve channel URL to ID
    logger.info(`Resolving URL: ${input.url}`);
    const resolved = await resolveChannelUrl(input.url);
    channelId = resolved.channelId;
    logger.success(`Resolved to channel ID: ${channelId} (${resolved.quotaCost} quota)`);

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

    const channel: Channel = {
      ...channelInfo,
      thumbnailStoragePath: '', // Preserved by merge: true in saveChannel
    };
    await saveChannel(channel);

    // Step 4: Fetch playlist pages, checking each page against Firestore
    const uploadsPlaylistId = getUploadsPlaylistId(channelId);
    logger.info(`Checking for new videos in playlist: ${uploadsPlaylistId}`);

    let pageToken: string | null = null;
    const newVideoIds: string[] = [];

    while (true) {
      if (isQuotaLow()) {
        logger.warn('Quota running low, stopping update...');
        break;
      }

      const page = await getPlaylistVideos(uploadsPlaylistId, pageToken || undefined);
      const items = page.items || [];
      const pageVideoIds = items.map((item) => item.videoId).filter((id): id is string => !!id);

      if (pageVideoIds.length === 0) break;

      // Check which videos in this page already exist
      const existingIds = await getExistingVideoIds(channelId, pageVideoIds);
      const newInPage = pageVideoIds.filter((id) => !existingIds.has(id));

      newVideoIds.push(...newInPage);

      // Stop condition: entire page is all-known videos
      if (newInPage.length === 0) {
        logger.info(`All ${pageVideoIds.length} videos on page already known — stopping`);
        break;
      }

      logger.info(`Found ${newInPage.length} new video(s) on this page (${newVideoIds.length} total new)`);

      if (!page.nextPageToken) break;
      pageToken = page.nextPageToken;

      await delay(config.scraper.apiDelayMs);
    }

    // No new videos found
    if (newVideoIds.length === 0) {
      logger.info('No new videos found');
      await updateProgressForUpdate(channelId, 0, channel.videoCount);
      return { success: true, channelId, newVideos: 0, thumbnailsDownloaded: 0 };
    }

    logger.success(`Found ${newVideoIds.length} new video(s) to process`);

    // Step 5: Fetch video details for new IDs only
    const videoChunks = chunk(newVideoIds, config.scraper.batchSize);
    const allNewVideos: Video[] = [];

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
        const video = transformVideoData(data, channelId, channel.subscriberCount);

        if (!settings.includeShorts && video.isShort) {
          continue;
        }

        videos.push({
          ...video,
          thumbnailStoragePath: '',
        });
      }

      allNewVideos.push(...videos);
      await saveVideosBatch(channelId, videos);

      await delay(config.scraper.apiDelayMs);
    }

    // Step 6: Download thumbnails for new videos only
    let thumbnailsDownloaded = 0;
    if (allNewVideos.length > 0) {
      const newVideosForThumbnails = settings.skipShortThumbnails
        ? allNewVideos.filter((v) => !v.isShort)
        : allNewVideos;

      if (newVideosForThumbnails.length < allNewVideos.length) {
        logger.info(`Skipping thumbnails for ${allNewVideos.length - newVideosForThumbnails.length} short(s)`);
      }

      if (newVideosForThumbnails.length > 0) {
        logger.info(`Downloading thumbnails for ${newVideosForThumbnails.length} new video(s)...`);

        const thumbnailResults = await processThumbnailBatch(
          newVideosForThumbnails.map((v) => v.videoId),
          channelId,
          (processed, total) => {
            if (processed % 50 === 0 || processed === total) {
              logger.info(`Thumbnails: ${processed}/${total}`);
            }
          }
        );

        thumbnailsDownloaded = thumbnailResults.filter((r) => r.success).length;

        // Update videos with thumbnail paths
        const thumbnailPathMap = new Map(
          thumbnailResults.filter((r) => r.success).map((r) => [r.videoId, r.storagePath!])
        );

        for (const video of newVideosForThumbnails) {
          const path = thumbnailPathMap.get(video.videoId);
          if (path) {
            video.thumbnailStoragePath = path;
          }
        }

        await saveVideosBatch(channelId, newVideosForThumbnails);
      }
    }

    // Step 7: Update progress
    await updateProgressForUpdate(channelId, allNewVideos.length, channel.videoCount);

    logger.success(`Update complete: ${channelInfo.channelTitle}`);
    logger.stats({
      'New Videos': allNewVideos.length,
      'Thumbnails': thumbnailsDownloaded,
      'Quota Used': `${getQuotaUsed()} / ${config.quota.dailyLimit}`,
    });

    return {
      success: true,
      channelId,
      newVideos: allNewVideos.length,
      thumbnailsDownloaded,
    };
  } catch (error) {
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
 * Run the main scraper
 */
export async function runScraper(options: { updateMode?: boolean; ignoreQuota?: boolean } = {}): Promise<void> {
  const { updateMode = false, ignoreQuota = false } = options;
  const startTime = Date.now();

  logger.header('YouTube Intelligence System v1.0');
  logger.info(updateMode ? 'Phase 1: Incremental Update' : 'Phase 1: Data Collection');
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
  let channelsProcessed = 0;
  let channelsFailed = 0;

  for (let i = 0; i < channelsConfig.channels.length; i++) {
    const channelInput = channelsConfig.channels[i];

    // Check quota before processing
    if (isQuotaLow()) {
      logger.warn('API quota nearly exhausted. Stopping.');
      break;
    }

    const verb = updateMode ? 'Updating' : 'Processing';
    logger.subheader(`${verb} [${i + 1}/${channelsConfig.channels.length}]: ${channelInput.url}`);

    if (updateMode) {
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
    } else {
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
  const videoLabel = updateMode ? 'New Videos Found' : 'Videos Scraped';

  logger.header('Session Summary');
  logger.stats({
    'Duration': formatDuration(Math.floor(duration / 1000)),
    'Channels Processed': `${channelsProcessed}/${channelsConfig.channels.length}`,
    'Channels Failed': channelsFailed,
    [videoLabel]: formatNumber(totalVideos),
    'Thumbnails Downloaded': formatNumber(totalThumbnails),
    'API Quota Used': `${formatNumber(getQuotaUsed())} / ${formatNumber(config.quota.dailyLimit)}`,
    'API Quota Remaining': formatNumber(getQuotaRemaining()),
  });

  logger.divider();

  if (getQuotaRemaining() < config.scraper.quotaWarningThreshold) {
    logger.warn('Quota nearly exhausted. Run again after midnight Pacific Time.');
  } else if (channelsProcessed < channelsConfig.channels.length) {
    logger.info(`More channels to process. Run again: npm start${updateMode ? ' -- --update' : ''}`);
  } else if (updateMode) {
    logger.success('All channels updated!');
  } else {
    logger.success('All channels processed! Proceed to Phase 2: cd analyzer && python -m src.main');
  }
}
