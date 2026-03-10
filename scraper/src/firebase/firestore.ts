import { getDb } from './client.js';
import { Channel, Video, CalculatedMetrics, ScrapeProgress, UnresolvedChannel } from '../types/index.js';
import { Timestamp } from 'firebase-admin/firestore';

// Collection names
const CHANNELS_COLLECTION = 'channels';
const VIDEOS_SUBCOLLECTION = 'videos';
const PROGRESS_COLLECTION = 'scrape_progress';
const UNRESOLVED_COLLECTION = 'unresolved_channels';

/**
 * Save or update channel data
 */
export async function saveChannel(channel: Channel): Promise<void> {
  const db = getDb();
  await db.collection(CHANNELS_COLLECTION).doc(channel.channelId).set(channel, { merge: true });
}

/**
 * Get channel by ID
 */
export async function getChannel(channelId: string): Promise<Channel | null> {
  const db = getDb();
  const doc = await db.collection(CHANNELS_COLLECTION).doc(channelId).get();
  return doc.exists ? (doc.data() as Channel) : null;
}

/**
 * Save video data
 */
export async function saveVideo(channelId: string, video: Video): Promise<void> {
  const db = getDb();
  await db
    .collection(CHANNELS_COLLECTION)
    .doc(channelId)
    .collection(VIDEOS_SUBCOLLECTION)
    .doc(video.videoId)
    .set(video, { merge: true });
}

// Firestore batch size limit
const MAX_BATCH_SIZE = 500;

/**
 * Save multiple videos in a batch
 * Automatically splits into multiple batches if exceeding Firestore's 500 operation limit
 */
export async function saveVideosBatch(channelId: string, videos: Video[]): Promise<void> {
  if (videos.length === 0) return;

  const db = getDb();

  // Split into chunks of MAX_BATCH_SIZE to respect Firestore limits
  for (let i = 0; i < videos.length; i += MAX_BATCH_SIZE) {
    const chunk = videos.slice(i, i + MAX_BATCH_SIZE);
    const batch = db.batch();

    for (const video of chunk) {
      const ref = db
        .collection(CHANNELS_COLLECTION)
        .doc(channelId)
        .collection(VIDEOS_SUBCOLLECTION)
        .doc(video.videoId);
      batch.set(ref, video, { merge: true });
    }

    try {
      await batch.commit();
    } catch (error) {
      throw new Error(`Failed to save video batch for channel ${channelId} (chunk ${Math.floor(i / MAX_BATCH_SIZE) + 1}): ${(error as Error).message}`);
    }
  }
}

/**
 * Get video by ID
 */
export async function getVideo(channelId: string, videoId: string): Promise<Video | null> {
  const db = getDb();
  const doc = await db
    .collection(CHANNELS_COLLECTION)
    .doc(channelId)
    .collection(VIDEOS_SUBCOLLECTION)
    .doc(videoId)
    .get();
  return doc.exists ? (doc.data() as Video) : null;
}

/**
 * Check if video exists
 */
export async function videoExists(channelId: string, videoId: string): Promise<boolean> {
  const db = getDb();
  const doc = await db
    .collection(CHANNELS_COLLECTION)
    .doc(channelId)
    .collection(VIDEOS_SUBCOLLECTION)
    .doc(videoId)
    .get();
  return doc.exists;
}

/**
 * Get all videos for a channel
 */
export async function getChannelVideos(channelId: string): Promise<Video[]> {
  const db = getDb();
  const snapshot = await db
    .collection(CHANNELS_COLLECTION)
    .doc(channelId)
    .collection(VIDEOS_SUBCOLLECTION)
    .get();
  return snapshot.docs.map((doc) => doc.data() as Video);
}

/**
 * Get video count for a channel
 */
export async function getVideoCount(channelId: string): Promise<number> {
  const db = getDb();
  const snapshot = await db
    .collection(CHANNELS_COLLECTION)
    .doc(channelId)
    .collection(VIDEOS_SUBCOLLECTION)
    .count()
    .get();
  return snapshot.data().count;
}

// ===== Progress Tracking =====

/**
 * Save or update scrape progress
 */
export async function saveProgress(progress: ScrapeProgress): Promise<void> {
  const db = getDb();
  await db.collection(PROGRESS_COLLECTION).doc(progress.channelId).set(progress, { merge: true });
}

/**
 * Get scrape progress for a channel
 */
export async function getProgress(channelId: string): Promise<ScrapeProgress | null> {
  const db = getDb();
  const doc = await db.collection(PROGRESS_COLLECTION).doc(channelId).get();
  return doc.exists ? (doc.data() as ScrapeProgress) : null;
}

/**
 * Get all progress records
 */
export async function getAllProgress(): Promise<ScrapeProgress[]> {
  const db = getDb();
  const snapshot = await db.collection(PROGRESS_COLLECTION).get();
  return snapshot.docs.map((doc) => doc.data() as ScrapeProgress);
}

/**
 * Delete progress for a channel
 */
export async function deleteProgress(channelId: string): Promise<void> {
  const db = getDb();
  await db.collection(PROGRESS_COLLECTION).doc(channelId).delete();
}

/**
 * Delete all progress records
 */
export async function deleteAllProgress(): Promise<void> {
  const db = getDb();
  const snapshot = await db.collection(PROGRESS_COLLECTION).get();

  // Firestore batches limited to 500 operations
  const BATCH_LIMIT = 500;
  const docs = snapshot.docs;
  for (let i = 0; i < docs.length; i += BATCH_LIMIT) {
    const chunk = docs.slice(i, i + BATCH_LIMIT);
    const batch = db.batch();
    chunk.forEach((doc) => batch.delete(doc.ref));
    await batch.commit();
  }
}

/**
 * Initialize progress for a channel
 */
export function createInitialProgress(
  channelId: string,
  channelTitle: string,
  sourceUrl: string,
  totalVideos: number
): ScrapeProgress {
  const now = Timestamp.now();
  return {
    channelId,
    channelTitle,
    sourceUrl,
    status: 'pending',
    phase: 'scraping',
    totalVideos,
    videosProcessed: 0,
    thumbnailsDownloaded: 0,
    lastProcessedVideoId: null,
    lastPlaylistPageToken: null,
    startedAt: now,
    lastProcessedAt: now,
    completedAt: null,
    errorMessage: null,
    errorStack: null,
    retryCount: 0,
  };
}

/**
 * Check which video IDs already exist in Firestore for a channel.
 * Uses getAll() for efficient batch reads (single RPC for up to 100 refs).
 */
export async function getExistingVideoIds(channelId: string, videoIds: string[]): Promise<Set<string>> {
  if (videoIds.length === 0) return new Set();

  const db = getDb();
  const existing = new Set<string>();

  // getAll() supports up to 100 refs per call
  const BATCH_SIZE = 100;
  for (let i = 0; i < videoIds.length; i += BATCH_SIZE) {
    const batch = videoIds.slice(i, i + BATCH_SIZE);
    const refs = batch.map((id) =>
      db.collection(CHANNELS_COLLECTION).doc(channelId).collection(VIDEOS_SUBCOLLECTION).doc(id)
    );

    const docs = await db.getAll(...refs);
    for (const doc of docs) {
      if (doc.exists) {
        existing.add(doc.id);
      }
    }
  }

  return existing;
}

/**
 * Update channel stats after scraping
 */
export async function updateChannelStats(
  channelId: string,
  stats: {
    avgViewsPerVideo?: number;
    avgEngagementRate?: number;
    uploadFrequency?: string;
  }
): Promise<void> {
  const db = getDb();
  await db.collection(CHANNELS_COLLECTION).doc(channelId).update({
    ...stats,
    lastUpdatedAt: Timestamp.now(),
  });
}

/**
 * Get all video IDs for a channel (ID-only query, no field data transferred).
 */
export async function getAllVideoIdsForChannel(channelId: string): Promise<string[]> {
  const db = getDb();
  const snapshot = await db
    .collection(CHANNELS_COLLECTION)
    .doc(channelId)
    .collection(VIDEOS_SUBCOLLECTION)
    .select()
    .get();
  return snapshot.docs.map((doc) => doc.id);
}

/**
 * Batch-update video stats and calculated metrics only.
 * Uses merge:true to avoid overwriting immutable fields (title, description, thumbnails, etc.).
 */
export async function updateVideoStatsBatch(
  channelId: string,
  updates: Array<{
    videoId: string;
    viewCount: number;
    likeCount: number;
    commentCount: number;
    calculated: CalculatedMetrics;
    statsRefreshedAt: Timestamp;
  }>
): Promise<void> {
  if (updates.length === 0) return;

  const db = getDb();

  for (let i = 0; i < updates.length; i += MAX_BATCH_SIZE) {
    const chunk = updates.slice(i, i + MAX_BATCH_SIZE);
    const batch = db.batch();

    for (const update of chunk) {
      const ref = db
        .collection(CHANNELS_COLLECTION)
        .doc(channelId)
        .collection(VIDEOS_SUBCOLLECTION)
        .doc(update.videoId);
      batch.set(ref, {
        viewCount: update.viewCount,
        likeCount: update.likeCount,
        commentCount: update.commentCount,
        calculated: update.calculated,
        statsRefreshedAt: update.statsRefreshedAt,
      }, { merge: true });
    }

    try {
      await batch.commit();
    } catch (error) {
      throw new Error(`Failed to update video stats for channel ${channelId} (chunk ${Math.floor(i / MAX_BATCH_SIZE) + 1}): ${(error as Error).message}`);
    }
  }
}

// ===== Unresolved Channels =====

/**
 * Save or update an unresolved channel entry
 */
export async function saveUnresolvedChannel(entry: UnresolvedChannel): Promise<void> {
  const db = getDb();
  await db.collection(UNRESOLVED_COLLECTION).doc(entry.id).set(entry, { merge: true });
}

/**
 * Get a single unresolved channel by ID
 */
export async function getUnresolvedChannel(id: string): Promise<UnresolvedChannel | null> {
  const db = getDb();
  const doc = await db.collection(UNRESOLVED_COLLECTION).doc(id).get();
  return doc.exists ? (doc.data() as UnresolvedChannel) : null;
}

/**
 * Get all unresolved channel entries
 */
export async function getAllUnresolvedChannels(): Promise<UnresolvedChannel[]> {
  const db = getDb();
  const snapshot = await db.collection(UNRESOLVED_COLLECTION).get();
  return snapshot.docs.map((doc) => doc.data() as UnresolvedChannel);
}

/**
 * Delete an unresolved channel entry
 */
export async function deleteUnresolvedChannel(id: string): Promise<void> {
  const db = getDb();
  await db.collection(UNRESOLVED_COLLECTION).doc(id).delete();
}
