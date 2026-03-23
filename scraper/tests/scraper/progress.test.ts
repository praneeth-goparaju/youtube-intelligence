import { describe, it, expect, vi } from 'vitest';

// Mock firebase-admin/firestore before any imports that use it
vi.mock('firebase-admin/firestore', () => ({
  Timestamp: {
    now: () => ({ seconds: 1234567890, nanoseconds: 0 }),
  },
  FieldValue: {
    serverTimestamp: () => ({ seconds: 0, nanoseconds: 0 }),
  },
}));

vi.mock('firebase-admin', () => ({
  default: {
    initializeApp: vi.fn(),
    credential: { cert: vi.fn() },
    firestore: vi.fn(() => ({})),
  },
  initializeApp: vi.fn(),
  credential: { cert: vi.fn() },
}));

import { createInitialProgress } from '../../src/firebase/firestore.js';

describe('createInitialProgress', () => {
  it('should create progress with correct fields from arguments', () => {
    const progress = createInitialProgress(
      'UCxxxxxxxxxxxxxxxxxxxxxxx',
      'Test Channel',
      'https://youtube.com/@test',
      100
    );

    expect(progress.channelId).toBe('UCxxxxxxxxxxxxxxxxxxxxxxx');
    expect(progress.channelTitle).toBe('Test Channel');
    expect(progress.sourceUrl).toBe('https://youtube.com/@test');
    expect(progress.totalVideos).toBe(100);
  });

  it('should initialize counters to zero', () => {
    const progress = createInitialProgress('UC123456789012345678901', 'Ch', 'url', 50);

    expect(progress.videosProcessed).toBe(0);
    expect(progress.thumbnailsDownloaded).toBe(0);
    expect(progress.retryCount).toBe(0);
  });

  it('should set status to pending and phase to scraping', () => {
    const progress = createInitialProgress('UC123456789012345678901', 'Ch', 'url', 50);

    expect(progress.status).toBe('pending');
    expect(progress.phase).toBe('scraping');
  });

  it('should set nullable fields to null', () => {
    const progress = createInitialProgress('UC123456789012345678901', 'Ch', 'url', 50);

    expect(progress.lastProcessedVideoId).toBeNull();
    expect(progress.lastPlaylistPageToken).toBeNull();
    expect(progress.completedAt).toBeNull();
    expect(progress.errorMessage).toBeNull();
    expect(progress.errorStack).toBeNull();
  });

  it('should set timestamps', () => {
    const progress = createInitialProgress('UC123456789012345678901', 'Ch', 'url', 50);

    expect(progress.startedAt).toBeDefined();
    expect(progress.lastProcessedAt).toBeDefined();
  });
});
