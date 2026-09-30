import { getDb } from './client.js';
import { Channel, Video, CalculatedMetrics, ScrapeProgress, UnresolvedChannel } from '../types/index.js';
import { Timestamp } from 'firebase-admin/firestore';

// Collection names
const CHANNELS_COLLECTION = 'channels';
const VIDEOS_SUBCOLLECTION = 'videos';
const PROGRESS_COLLECTION = 'scrape_progress';
const UNRESOLVED_COLLECTION = 'unresolved_channels';

/**
 * Save or update channel data.
 * Fields omitted from a partial update are preserved by merge.
 */
export async function saveChannel(channel: Partial<Channel> & Pick<Channel, 'channelId'>): Promise<void> {
  const db = getDb();
  await db.collection(CHANNELS_COLLECTION).doc(channel.channelId).set(channel, { merge: true });
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
 * Get videos whose thumbnail has not been stored yet (thumbnailStoragePath == '').
 */
export async function getVideosMissingThumbnails(
  channelId: string
): Promise<Array<{ videoId: string; isShort: boolean }>> {
  const db = getDb();
  const snapshot = await db
    .collection(CHANNELS_COLLECTION)
    .doc(channelId)
    .collection(VIDEOS_SUBCOLLECTION)
    .where('thumbnailStoragePath', '==', '')
    .select('isShort')
    .get();
  return snapshot.docs.map((doc) => ({ videoId: doc.id, isShort: doc.get('isShort') === true }));
}

/**
 * Batch-write thumbnail storage paths only (merge:true leaves other video fields intact).
 */
export async function updateVideoThumbnailPaths(
  channelId: string,
  updates: Array<{ videoId: string; thumbnailStoragePath: string }>
): Promise<void> {
  const db = getDb();

  for (let i = 0; i < updates.length; i += MAX_BATCH_SIZE) {
    const batch = db.batch();
    for (const update of updates.slice(i, i + MAX_BATCH_SIZE)) {
      const ref = db
        .collection(CHANNELS_COLLECTION)
        .doc(channelId)
        .collection(VIDEOS_SUBCOLLECTION)
        .doc(update.videoId);
      batch.set(ref, { thumbnailStoragePath: update.thumbnailStoragePath }, { merge: true });
    }
    await batch.commit();
  }
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
