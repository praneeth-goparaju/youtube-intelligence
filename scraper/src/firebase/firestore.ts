import { getDb } from './client.js';
import { Channel, Video, ScrapeProgress } from '../types/index.js';
import { Timestamp } from 'firebase-admin/firestore';

// Collection names
const CHANNELS_COLLECTION = 'channels';
const VIDEOS_SUBCOLLECTION = 'videos';
const PROGRESS_COLLECTION = 'scrape_progress';

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

/**
 * Save multiple videos in a batch
 */
export async function saveVideosBatch(channelId: string, videos: Video[]): Promise<void> {
  const db = getDb();
  const batch = db.batch();

  for (const video of videos) {
    const ref = db
      .collection(CHANNELS_COLLECTION)
      .doc(channelId)
      .collection(VIDEOS_SUBCOLLECTION)
      .doc(video.videoId);
    batch.set(ref, video, { merge: true });
  }

  await batch.commit();
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
  const batch = db.batch();
  snapshot.docs.forEach((doc) => batch.delete(doc.ref));
  await batch.commit();
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
