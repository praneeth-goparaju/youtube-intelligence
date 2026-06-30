import { describe, it, expect, vi } from 'vitest';

// Mock config so importing the transform chain (videos.js -> client.js -> config.js)
// doesn't require real environment variables at module load.
vi.mock('../../src/config.js', () => ({
  config: {
    scraper: { maxRetries: 3, retryDelayMs: 1000, apiTimeoutMs: 30000, quotaWarningThreshold: 500 },
    quota: { dailyLimit: 10000 },
    youtube: { apiKey: 'test-key' },
  },
}));

import { transformAndFilterVideos, applyThumbnailPaths } from '../../src/scraper/video-processing.js';
import type { YouTubeVideoData } from '../../src/youtube/videos.js';
import type { Video } from '../../src/types/index.js';

function makeVideoData(opts: { id: string; duration: string; title?: string; description?: string }): YouTubeVideoData {
  return {
    id: opts.id,
    snippet: {
      title: opts.title ?? 'Test Video',
      description: opts.description ?? '',
      publishedAt: '2024-01-15T10:00:00Z',
      thumbnails: { medium: { url: 'http://example.com/m.jpg' } },
      tags: ['tag1', 'tag2'],
      categoryId: '22',
    },
    contentDetails: { duration: opts.duration, definition: 'hd', caption: 'false', licensedContent: false },
    statistics: { viewCount: '1000', likeCount: '100', commentCount: '10' },
    status: { madeForKids: false },
  };
}

describe('transformAndFilterVideos', () => {
  it('transforms long videos and leaves thumbnailStoragePath empty', () => {
    const result = transformAndFilterVideos([makeVideoData({ id: 'aaaaaaaaaaa', duration: 'PT10M0S' })], 'UC123', 1000, false);
    expect(result).toHaveLength(1);
    expect(result[0].videoId).toBe('aaaaaaaaaaa');
    expect(result[0].isShort).toBe(false);
    expect(result[0].thumbnailStoragePath).toBe('');
    expect(result[0].calculated.tagCount).toBe(2);
  });

  it('drops Shorts when includeShorts is false', () => {
    const data = [
      makeVideoData({ id: 'longvideo01', duration: 'PT10M0S' }),
      makeVideoData({ id: 'shortvid001', duration: 'PT10S' }), // <=15s => Short
    ];
    const result = transformAndFilterVideos(data, 'UC123', 1000, false);
    expect(result.map((v) => v.videoId)).toEqual(['longvideo01']);
  });

  it('keeps Shorts when includeShorts is true', () => {
    const data = [
      makeVideoData({ id: 'longvideo01', duration: 'PT10M0S' }),
      makeVideoData({ id: 'shortvid001', duration: 'PT10S' }),
    ];
    const result = transformAndFilterVideos(data, 'UC123', 1000, true);
    expect(result).toHaveLength(2);
  });
});

describe('applyThumbnailPaths', () => {
  it('assigns storage paths to matching videos and leaves failures untouched', () => {
    const videos = [
      { videoId: 'v1', thumbnailStoragePath: '' },
      { videoId: 'v2', thumbnailStoragePath: '' },
    ] as unknown as Video[];

    applyThumbnailPaths(videos, [
      { videoId: 'v1', success: true, storagePath: 'thumbnails/UC123/v1.jpg' },
      { videoId: 'v2', success: false, error: 'download failed' },
    ]);

    expect(videos[0].thumbnailStoragePath).toBe('thumbnails/UC123/v1.jpg');
    expect(videos[1].thumbnailStoragePath).toBe('');
  });

  it('ignores results for video ids not in the list', () => {
    const videos = [{ videoId: 'v1', thumbnailStoragePath: 'old/path.jpg' }] as unknown as Video[];

    applyThumbnailPaths(videos, [{ videoId: 'other', success: true, storagePath: 'thumbnails/x.jpg' }]);

    expect(videos[0].thumbnailStoragePath).toBe('old/path.jpg');
  });
});
