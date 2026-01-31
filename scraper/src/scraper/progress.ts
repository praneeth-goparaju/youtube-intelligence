import { Timestamp } from 'firebase-admin/firestore';
import {
  saveProgress,
  getProgress,
  getAllProgress,
  createInitialProgress,
} from '../firebase/firestore.js';
import { ScrapeProgress, ProgressStatus, ProgressPhase } from '../types/index.js';
import { getQuotaUsed, setQuotaUsed } from '../youtube/client.js';

/**
 * Get today's date in Pacific Time (YouTube quota resets at midnight PT)
 */
function getPacificDate(): string {
  const now = new Date();
  // Convert to Pacific Time
  const ptOptions: Intl.DateTimeFormatOptions = {
    timeZone: 'America/Los_Angeles',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  };
  const ptDate = new Intl.DateTimeFormat('en-CA', ptOptions).format(now);
  return ptDate; // Returns YYYY-MM-DD format
}

/**
 * Load saved quota usage if from the same day (quota resets daily at midnight Pacific)
 * Returns the highest quota value from today's progress records, or 0 if none found
 */
export async function loadSavedQuota(): Promise<number> {
  const allProgress = await getAllProgress();
  const today = getPacificDate();

  // Find the maximum quota usage from today across all progress records
  // This ensures we don't undercount if multiple channels were processed
  let maxQuota = 0;
  for (const progress of allProgress) {
    if (progress.quotaDate === today && typeof progress.quotaUsed === 'number') {
      maxQuota = Math.max(maxQuota, progress.quotaUsed);
    }
  }

  if (maxQuota > 0) {
    setQuotaUsed(maxQuota);
  }

  return maxQuota;
}

/**
 * Save current quota usage to a progress record
 */
export async function saveQuotaToProgress(channelId: string): Promise<void> {
  const progress = await getProgress(channelId);
  if (!progress) return;

  progress.quotaUsed = getQuotaUsed();
  progress.quotaDate = getPacificDate();
  progress.lastProcessedAt = Timestamp.now();

  await saveProgress(progress);
}

/**
 * Get or create progress for a channel
 */
export async function getOrCreateProgress(
  channelId: string,
  channelTitle: string,
  sourceUrl: string,
  totalVideos: number
): Promise<ScrapeProgress> {
  const existing = await getProgress(channelId);

  if (existing) {
    return existing;
  }

  const progress = createInitialProgress(channelId, channelTitle, sourceUrl, totalVideos);
  await saveProgress(progress);
  return progress;
}

/**
 * Update progress status
 */
export async function updateProgressStatus(
  channelId: string,
  status: ProgressStatus,
  errorMessage?: string
): Promise<void> {
  const progress = await getProgress(channelId);
  if (!progress) return;

  progress.status = status;
  progress.lastProcessedAt = Timestamp.now();

  if (status === 'completed') {
    progress.completedAt = Timestamp.now();
  }

  if (status === 'failed' && errorMessage) {
    progress.errorMessage = errorMessage;
    progress.retryCount += 1;
  }

  await saveProgress(progress);
}

/**
 * Update progress after processing videos
 */
export async function updateProgressVideos(
  channelId: string,
  videosProcessed: number,
  lastVideoId: string | null,
  nextPageToken: string | null
): Promise<void> {
  const progress = await getProgress(channelId);
  if (!progress) return;

  progress.videosProcessed = videosProcessed;
  progress.lastProcessedVideoId = lastVideoId;
  progress.lastPlaylistPageToken = nextPageToken;
  progress.lastProcessedAt = Timestamp.now();

  // Also save quota for resume capability
  progress.quotaUsed = getQuotaUsed();
  progress.quotaDate = getPacificDate();

  await saveProgress(progress);
}

/**
 * Update progress after downloading thumbnails
 */
export async function updateProgressThumbnails(
  channelId: string,
  thumbnailsDownloaded: number
): Promise<void> {
  const progress = await getProgress(channelId);
  if (!progress) return;

  progress.thumbnailsDownloaded = thumbnailsDownloaded;
  progress.lastProcessedAt = Timestamp.now();

  await saveProgress(progress);
}

/**
 * Update progress phase
 */
export async function updateProgressPhase(
  channelId: string,
  phase: ProgressPhase
): Promise<void> {
  const progress = await getProgress(channelId);
  if (!progress) return;

  progress.phase = phase;
  progress.lastProcessedAt = Timestamp.now();

  await saveProgress(progress);
}

/**
 * Get summary of all channel progress
 */
export async function getProgressSummary(): Promise<{
  completed: number;
  inProgress: number;
  pending: number;
  failed: number;
  totalVideos: number;
}> {
  const allProgress = await getAllProgress();

  return {
    completed: allProgress.filter((p) => p.status === 'completed').length,
    inProgress: allProgress.filter((p) => p.status === 'in_progress').length,
    pending: allProgress.filter((p) => p.status === 'pending').length,
    failed: allProgress.filter((p) => p.status === 'failed').length,
    totalVideos: allProgress.reduce((sum, p) => sum + p.videosProcessed, 0),
  };
}

/**
 * Get channels that need processing
 */
export async function getChannelsToProcess(
  channelIds: string[]
): Promise<{
  toResume: string[];
  toStart: string[];
  completed: string[];
}> {
  const allProgress = await getAllProgress();
  const progressMap = new Map(allProgress.map((p) => [p.channelId, p]));

  const toResume: string[] = [];
  const toStart: string[] = [];
  const completed: string[] = [];

  for (const channelId of channelIds) {
    const progress = progressMap.get(channelId);

    if (!progress) {
      toStart.push(channelId);
    } else if (progress.status === 'completed') {
      completed.push(channelId);
    } else if (progress.status === 'in_progress' || progress.status === 'pending') {
      toResume.push(channelId);
    } else if (progress.status === 'failed' && progress.retryCount < 3) {
      toResume.push(channelId);
    }
  }

  return { toResume, toStart, completed };
}

/**
 * Update progress after an incremental update of a completed channel.
 * Increments videosProcessed, sets lastUpdateAt, and saves quota info.
 * Keeps status as 'completed'.
 */
export async function updateProgressForUpdate(
  channelId: string,
  newVideosCount: number,
  newTotalVideos?: number
): Promise<void> {
  const progress = await getProgress(channelId);
  if (!progress) return;

  progress.videosProcessed += newVideosCount;
  progress.lastUpdateAt = Timestamp.now();
  progress.lastUpdateNewVideos = newVideosCount;
  progress.lastProcessedAt = Timestamp.now();
  progress.quotaUsed = getQuotaUsed();
  progress.quotaDate = getPacificDate();

  if (newTotalVideos !== undefined) {
    progress.totalVideos = newTotalVideos;
  }

  await saveProgress(progress);
}

/**
 * Check if a channel is already completed
 */
export async function isChannelCompleted(channelId: string): Promise<boolean> {
  const progress = await getProgress(channelId);
  return progress?.status === 'completed';
}
