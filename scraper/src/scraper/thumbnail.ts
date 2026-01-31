import { downloadAndUploadThumbnail, downloadAndUploadChannelThumbnail } from '../firebase/storage.js';
import { config } from '../config.js';
import { delay } from '../utils/helpers.js';
import { logger } from '../utils/logger.js';

interface ThumbnailResult {
  videoId: string;
  success: boolean;
  storagePath?: string;
  error?: string;
}

/**
 * Process thumbnails for a batch of videos
 */
export async function processThumbnailBatch(
  videoIds: string[],
  channelId: string,
  onProgress?: (processed: number, total: number) => void
): Promise<ThumbnailResult[]> {
  const CONCURRENCY = 20;
  const results: ThumbnailResult[] = [];
  let nextIndex = 0;
  let processed = 0;

  async function worker(): Promise<void> {
    while (nextIndex < videoIds.length) {
      const idx = nextIndex++;
      const videoId = videoIds[idx];

      try {
        const storagePath = await downloadAndUploadThumbnail(videoId, channelId);
        results.push({
          videoId,
          success: true,
          storagePath,
        });
      } catch (error) {
        results.push({
          videoId,
          success: false,
          error: (error as Error).message,
        });
        logger.warn(`Failed to download thumbnail for ${videoId}: ${(error as Error).message}`);
      }

      processed++;
      if (onProgress) {
        onProgress(processed, videoIds.length);
      }
    }
  }

  const workers = Array.from(
    { length: Math.min(CONCURRENCY, videoIds.length) },
    () => worker()
  );
  await Promise.all(workers);

  return results;
}

/**
 * Process channel thumbnail
 */
export async function processChannelThumbnail(
  channelId: string,
  thumbnailUrl: string
): Promise<string | null> {
  if (!thumbnailUrl) {
    return null;
  }

  try {
    return await downloadAndUploadChannelThumbnail(channelId, thumbnailUrl);
  } catch (error) {
    logger.warn(`Failed to download channel thumbnail: ${(error as Error).message}`);
    return null;
  }
}

/**
 * Get statistics from thumbnail processing results
 */
export function getThumbnailStats(results: ThumbnailResult[]): {
  total: number;
  successful: number;
  failed: number;
  failedIds: string[];
} {
  const successful = results.filter((r) => r.success);
  const failed = results.filter((r) => !r.success);

  return {
    total: results.length,
    successful: successful.length,
    failed: failed.length,
    failedIds: failed.map((r) => r.videoId),
  };
}
