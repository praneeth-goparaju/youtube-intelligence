import { describe, it, expect, vi } from 'vitest';

// Mock the Firebase client module to prevent config.ts from loading env vars
vi.mock('../../src/firebase/client.js', () => ({
  getDb: vi.fn(),
}));

// Mock Timestamp used by createInitialProgress
vi.mock('firebase-admin/firestore', () => ({
  Timestamp: {
    now: () => ({ seconds: 1234567890, nanoseconds: 0 }),
  },
}));

import { createInitialProgress } from '../../src/firebase/firestore.js';

describe('createInitialProgress', () => {
  it('creates a resumable pending record', () => {
    const progress = createInitialProgress(
      'UCxxxxxxxxxxxxxxxxxxxxxxx',
      'Test Channel',
      'https://youtube.com/@test',
      100
    );

    expect(progress).toMatchObject({
      channelId: 'UCxxxxxxxxxxxxxxxxxxxxxxx',
      channelTitle: 'Test Channel',
      sourceUrl: 'https://youtube.com/@test',
      totalVideos: 100,
      status: 'pending',
      phase: 'scraping',
      videosProcessed: 0,
      thumbnailsDownloaded: 0,
      retryCount: 0,
      lastProcessedVideoId: null,
      lastPlaylistPageToken: null,
      completedAt: null,
      errorMessage: null,
      errorStack: null,
    });
  });
});
