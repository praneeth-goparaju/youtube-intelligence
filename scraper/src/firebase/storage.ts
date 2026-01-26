import { getBucket } from './client.js';
import axios from 'axios';
import { config } from '../config.js';
import { retry } from '../utils/helpers.js';

/**
 * Download an image from URL and return as buffer
 */
async function downloadImage(url: string): Promise<Buffer> {
  const response = await axios.get(url, {
    responseType: 'arraybuffer',
    timeout: 30000,
  });
  return Buffer.from(response.data);
}

/**
 * Upload image buffer to Firebase Storage
 */
async function uploadBuffer(buffer: Buffer, storagePath: string): Promise<string> {
  const bucket = getBucket();
  const file = bucket.file(storagePath);

  await file.save(buffer, {
    contentType: 'image/jpeg',
    metadata: {
      cacheControl: 'public, max-age=31536000',
    },
  });

  return storagePath;
}

/**
 * Download thumbnail from YouTube and upload to Firebase Storage
 */
export async function downloadAndUploadThumbnail(
  videoId: string,
  channelId: string
): Promise<string> {
  const thumbnailUrl = `https://img.youtube.com/vi/${videoId}/${config.scraper.thumbnailQuality}.jpg`;
  const storagePath = `thumbnails/${channelId}/${videoId}.jpg`;

  return retry(
    async () => {
      const buffer = await downloadImage(thumbnailUrl);
      await uploadBuffer(buffer, storagePath);
      return storagePath;
    },
    config.scraper.maxRetries,
    config.scraper.retryDelayMs
  );
}

/**
 * Download channel thumbnail and upload to Firebase Storage
 */
export async function downloadAndUploadChannelThumbnail(
  channelId: string,
  thumbnailUrl: string
): Promise<string> {
  const storagePath = `channel_thumbnails/${channelId}.jpg`;

  return retry(
    async () => {
      const buffer = await downloadImage(thumbnailUrl);
      await uploadBuffer(buffer, storagePath);
      return storagePath;
    },
    config.scraper.maxRetries,
    config.scraper.retryDelayMs
  );
}

/**
 * Check if a file exists in storage
 */
export async function fileExists(storagePath: string): Promise<boolean> {
  const bucket = getBucket();
  const file = bucket.file(storagePath);
  const [exists] = await file.exists();
  return exists;
}

/**
 * Get public URL for a file
 */
export function getPublicUrl(storagePath: string): string {
  return `https://storage.googleapis.com/${config.firebase.storageBucket}/${storagePath}`;
}

/**
 * Delete a file from storage
 */
export async function deleteFile(storagePath: string): Promise<void> {
  const bucket = getBucket();
  await bucket.file(storagePath).delete();
}

/**
 * Get signed URL for temporary access
 */
export async function getSignedUrl(storagePath: string, expiresInMs = 3600000): Promise<string> {
  const bucket = getBucket();
  const file = bucket.file(storagePath);
  const [url] = await file.getSignedUrl({
    action: 'read',
    expires: Date.now() + expiresInMs,
  });
  return url;
}
