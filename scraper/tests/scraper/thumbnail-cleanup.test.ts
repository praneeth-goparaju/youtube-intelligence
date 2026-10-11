import { describe, expect, it } from 'vitest';
import { deleteThumbnailFiles } from '../../src/scraper/thumbnail-cleanup.js';

describe('thumbnail cleanup', () => {
  it('only clears references to successfully deleted or already absent files', async () => {
    const thumbnails = ['deleted', 'absent', 'failed'].map((videoId) => ({
      channelId: 'channel', videoId, thumbnailStoragePath: `thumbnails/${videoId}.jpg`,
    }));
    const result = await deleteThumbnailFiles(thumbnails, async (path) => {
      if (path.includes('absent')) throw Object.assign(new Error('not found'), { code: 404 });
      if (path.includes('failed')) throw Object.assign(new Error('temporary outage'), { code: 503 });
    });
    expect(result.deleted.map((thumbnail) => thumbnail.videoId).sort()).toEqual(['absent', 'deleted']);
    expect(result.failed.map(({ thumbnail }) => thumbnail.videoId)).toEqual(['failed']);

    const retry = await deleteThumbnailFiles(result.failed.map(({ thumbnail }) => thumbnail), async () => {});
    expect(retry.deleted).toEqual([thumbnails[2]]);
    expect(retry.failed).toEqual([]);
  });
});
