import { Video } from '../types/index.js';
import { transformVideoData, YouTubeVideoData } from '../youtube/videos.js';
import { ThumbnailResult } from './thumbnail.js';

/**
 * Transform a batch of raw YouTube video details into Video records, dropping
 * Shorts unless includeShorts is set.
 *
 * thumbnailStoragePath starts empty because thumbnails are downloaded in a
 * later step (and filled in via applyThumbnailPaths). Shared by the full-scrape
 * and incremental-update paths so both filter and shape videos identically.
 */
export function transformAndFilterVideos(
  videoData: YouTubeVideoData[],
  channelId: string,
  subscriberCount: number | null,
  includeShorts: boolean
): Video[] {
  const videos: Video[] = [];
  for (const data of videoData) {
    const video = transformVideoData(data, channelId, subscriberCount);

    // Filter shorts if needed
    if (!includeShorts && video.isShort) {
      continue;
    }

    videos.push({
      ...video,
      thumbnailStoragePath: '', // Will be updated later
    });
  }
  return videos;
}

/**
 * Apply downloaded thumbnail storage paths back onto their Video records.
 *
 * Mutates the passed videos in place; only successful downloads are applied,
 * so videos whose thumbnail failed keep their existing path.
 */
export function applyThumbnailPaths(videos: Video[], thumbnailResults: ThumbnailResult[]): void {
  const pathMap = new Map(
    thumbnailResults.filter((r) => r.success).map((r) => [r.videoId, r.storagePath!])
  );

  for (const video of videos) {
    const path = pathMap.get(video.videoId);
    if (path) {
      video.thumbnailStoragePath = path;
    }
  }
}
