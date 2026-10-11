import { beforeEach, describe, expect, it, vi } from 'vitest';
import { readFileSync } from 'node:fs';

const state = vi.hoisted(() => ({
  documents: new Map<string, Record<string, unknown>>(),
  lowChecks: [] as boolean[],
  pages: [] as string[][],
  thumbnailRequests: [] as string[],
  failDetails: false,
  thumbnailFailureIds: new Set<string>(),
}));

vi.mock('../../src/config.js', () => ({
  config: { scraper: { batchSize: 50, apiDelayMs: 0, maxRetries: 1, retryDelayMs: 0 }, quota: { dailyLimit: 10000 }, youtube: { apiKey: 'test' } },
}));
vi.mock('../../src/utils/logger.js', () => ({
  logger: new Proxy({}, { get: () => () => undefined }),
}));
vi.mock('../../src/firebase/client.js', () => {
  function doc(path: string) {
    return {
      id: path.split('/').at(-1), path,
      set: async (data: Record<string, unknown>, options?: { merge: boolean }) => state.documents.set(path, { ...(options?.merge ? state.documents.get(path) : {}), ...data }),
      get: async () => ({ id: path.split('/').at(-1), exists: state.documents.has(path), data: () => ({ ...state.documents.get(path) }) }),
      collection: (name: string) => collection(`${path}/${name}`),
    };
  }
  function collection(path: string, predicate: (data: Record<string, unknown>) => boolean = () => true) {
    const matching = () => [...state.documents.entries()].filter(([key, data]) => key.startsWith(path + '/') && key.slice(path.length + 1).indexOf('/') === -1 && predicate(data));
    return {
      doc: (id: string) => doc(`${path}/${id}`),
      get: async () => ({ docs: matching().map(([key, value]) => ({ id: key.split('/').at(-1), data: () => ({ ...value }) })) }),
      select: () => collection(path),
      where: (field: string, _operator: string, value: unknown) => collection(path, (data) => data[field] !== undefined && data[field] !== value),
      count: () => ({ get: async () => ({ data: () => ({ count: matching().length }) }) }),
    };
  }
  const db = {
    collection,
    getAll: (...refs: ReturnType<typeof doc>[]) => Promise.all(refs.map((ref) => ref.get())),
    batch: () => {
      const operations: Array<() => Promise<unknown>> = [];
      return {
        set: (ref: ReturnType<typeof doc>, data: Record<string, unknown>, options: { merge: boolean }) => operations.push(() => ref.set(data, options)),
        commit: async () => { for (const operation of operations) await operation(); },
      };
    },
  };
  return { initializeFirebase: () => ({}), getDb: () => db };
});
vi.mock('../../src/youtube/resolver.js', () => ({
  resolveChannelUrl: async () => ({ channelId: 'UCaaaaaaaaaaaaaaaaaaaaaa', quotaCost: 0, resolvedFrom: 'channelId' }),
}));
vi.mock('../../src/youtube/client.js', () => ({
  isQuotaLow: () => state.lowChecks.shift() ?? false,
  getQuotaUsed: () => 0, getQuotaRemaining: () => 10000, setQuotaUsed: () => {}, setIgnoreQuota: () => {},
}));
vi.mock('../../src/youtube/channels.js', async (original) => ({
  ...await original(),
  getChannelDetails: async () => ({ id: 'UCaaaaaaaaaaaaaaaaaaaaaa', snippet: { title: 'Test', description: '', thumbnails: {}, publishedAt: '2025-01-01T00:00:00Z' }, statistics: { subscriberCount: '1000', videoCount: '100', viewCount: '10000' } }),
}));
vi.mock('../../src/youtube/videos.js', async (original) => ({
  ...await original(),
  getPlaylistVideos: async (_playlist: string, token?: string) => {
    const i = token ? Number(token) : 0;
    return { items: state.pages[i].map((videoId) => ({ videoId })), nextPageToken: i + 1 < state.pages.length ? String(i + 1) : null, totalResults: state.pages.flat().length };
  },
  getVideoDetails: async (ids: string[]) => {
    if (state.failDetails) throw new Error('simulated transient API failure');
    return ids.map((id) => ({ id, snippet: { title: id, description: '', publishedAt: '2025-01-01T00:00:00Z', thumbnails: {}, categoryId: '22', tags: [] }, contentDetails: { duration: 'PT10M', definition: 'hd', caption: 'false', licensedContent: false }, statistics: { viewCount: '100', likeCount: '1', commentCount: '1' } }));
  },
}));
vi.mock('../../src/scraper/thumbnail.js', () => ({
  processChannelThumbnail: async () => 'channel_thumbnails/UCaaaaaaaaaaaaaaaaaaaaaa.jpg',
  processThumbnailBatch: async (ids: string[], channelId: string) => {
    state.thumbnailRequests.push(...ids);
    return ids.map((videoId) => state.thumbnailFailureIds.has(videoId) ? { videoId, success: false, error: 'temporary download failure' } : { videoId, success: true, storagePath: `thumbnails/${channelId}/${videoId}.jpg` });
  },
}));

import { processChannel, updateChannel, refreshChannel, parseChannelsConfig } from '../../src/scraper/index.js';
import { createInitialProgress } from '../../src/firebase/firestore.js';

const channelId = 'UCaaaaaaaaaaaaaaaaaaaaaa';
const input = { url: `https://youtube.com/channel/${channelId}`, category: 'test', priority: 1 };
const settings = { maxVideosPerChannel: null, includeShorts: false, includePrivate: false, skipShortThumbnails: true };
const progressKey = `scrape_progress/${channelId}`;
const videoKey = (id: string) => `channels/${channelId}/videos/${id}`;
const page = (prefix: string) => Array.from({ length: 50 }, (_, i) => `${prefix}${String(i).padStart(10, '0')}`);
function completeExistingChannel() {
  state.documents.set(progressKey, { ...createInitialProgress(channelId, 'Test', input.url, 150), status: 'completed' });
  state.documents.set(`channels/${channelId}`, { channelId, thumbnailStoragePath: `channel_thumbnails/${channelId}.jpg` });
}
beforeEach(() => {
  state.documents.clear(); state.lowChecks = []; state.pages = []; state.thumbnailRequests = []; state.failDetails = false; state.thumbnailFailureIds.clear();
});
describe('scraper recovery', () => {
  it('replays playlist enumeration after a quota stop without losing collected IDs', async () => {
    const newer = page('a'); const older = page('b'); state.pages = [newer, older];
    state.lowChecks = [false, true];
    expect((await processChannel(input, settings)).success).toBe(false);
    expect(state.documents.get(progressKey)?.lastPlaylistPageToken).toBeNull();
    expect(state.documents.has(videoKey(newer[0]))).toBe(false);
    expect((await processChannel(input, settings)).success).toBe(true);
    expect(state.documents.get(progressKey)?.status).toBe('completed');
    expect(state.documents.get(progressKey)?.videosProcessed).toBe(100);
    for (const id of [...newer, ...older]) expect(state.documents.get(videoKey(id))?.thumbnailStoragePath).toBeTruthy();
  });

  it('finishes each metadata batch with thumbnails before stopping and resumes without duplicate counts', async () => {
    const first = page('a'); const second = page('b'); state.pages = [first, second];
    state.lowChecks = [false, false, false, true];
    expect((await processChannel(input, settings)).success).toBe(false);
    expect(state.documents.get(videoKey(first[0]))?.thumbnailStoragePath).toBeTruthy();
    expect((await processChannel(input, settings)).success).toBe(true);
    expect(state.documents.get(progressKey)?.videosProcessed).toBe(100);
    expect(state.documents.get(progressKey)?.thumbnailsDownloaded).toBe(100);
    expect(state.thumbnailRequests).toHaveLength(100);
    for (const id of [...first, ...second]) expect(state.documents.get(videoKey(id))?.thumbnailStoragePath).toBeTruthy();
  });

  it('repairs old completed checkpoints containing unsaved pages and unfinished thumbnails', async () => {
    completeExistingChannel(); const first = page('a'); const second = page('b'); state.pages = [first, second];
    state.documents.set(progressKey, { ...state.documents.get(progressKey), lastPlaylistPageToken: '1', videosProcessed: 50, lastProcessedVideoId: first.at(-1) });
    first.forEach((videoId) => state.documents.set(videoKey(videoId), { videoId, channelId, isShort: false, thumbnailStoragePath: '' }));
    expect((await processChannel(input, settings)).success).toBe(true);
    expect(state.documents.get(progressKey)?.videosProcessed).toBe(100);
    expect(state.documents.get(progressKey)?.thumbnailsDownloaded).toBe(100);
    expect(state.documents.get(progressKey)?.lastCompletedPlaylistVideoId).toBe(first[0]);
  });

  it('retains the last successful update marker until all new videos are durable', async () => {
    completeExistingChannel(); const first = page('a'); const second = page('b'); const old = page('c');
    state.documents.set(progressKey, { ...state.documents.get(progressKey), lastCompletedPlaylistVideoId: old[0] });
    state.pages = [first, second, old]; old.forEach((id) => state.documents.set(videoKey(id), { videoId: id, thumbnailStoragePath: `thumbnails/${id}.jpg` }));
    state.lowChecks = [false, false, false, false, true];
    expect(await updateChannel(input, settings)).toMatchObject({ success: false, newVideos: 50, error: 'Quota exhausted' });
    expect(state.documents.get(progressKey)?.lastCompletedPlaylistVideoId).toBe(old[0]);
    expect(await updateChannel(input, settings)).toMatchObject({ success: true, newVideos: 50 });
    expect(state.documents.has(videoKey(second[0]))).toBe(true);
    expect(state.documents.get(progressKey)?.lastCompletedPlaylistVideoId).toBe(first[0]);
    expect(state.documents.get(progressKey)?.videosProcessed).toBe(150);
    expect(state.thumbnailRequests).toHaveLength(100);
  });

  it('repairs missing older videos in a legacy update even when the newest page already exists', async () => {
    completeExistingChannel(); const first = page('a'); const second = page('b'); state.pages = [first, second];
    first.forEach((id) => state.documents.set(videoKey(id), { videoId: id, thumbnailStoragePath: `thumbnails/${id}.jpg` }));
    expect(await updateChannel(input, settings)).toMatchObject({ success: true, newVideos: 50 });
    expect(state.documents.get(progressKey)?.videosProcessed).toBe(100);
    expect(state.documents.has(videoKey(second[0]))).toBe(true);
  });

  it.each(['full', 'update'])('retries failed thumbnails after a %s scrape without declaring completion', async (mode) => {
    const ids = page('a'); state.pages = [ids]; state.thumbnailFailureIds.add(ids[0]);
    if (mode === 'update') completeExistingChannel();
    const run = () => mode === 'full' ? processChannel(input, settings) : updateChannel(input, settings);
    expect((await run()).success).toBe(false);
    expect(state.documents.get(progressKey)?.lastCompletedPlaylistVideoId).toBeUndefined();
    expect(state.documents.get(videoKey(ids[0]))?.thumbnailStoragePath).toBe('');
    state.thumbnailFailureIds.clear();
    expect((await run()).success).toBe(true);
    expect(state.documents.get(videoKey(ids[0]))?.thumbnailStoragePath).toBeTruthy();
    expect(state.documents.get(progressKey)?.thumbnailsDownloaded).toBe(50);
    expect(state.thumbnailRequests).toHaveLength(51);
  });

  it.each(['update', 'refresh'])('preserves stored channel thumbnails on %s', async (mode) => {
    completeExistingChannel(); state.pages = [[]];
    if (mode === 'update') await updateChannel(input, settings); else await refreshChannel(input, settings);
    expect(state.documents.get(`channels/${channelId}`)?.thumbnailStoragePath).toBe(`channel_thumbnails/${channelId}.jpg`);
  });

  it('reports failure without recording a completed refresh when every API batch failed', async () => {
    completeExistingChannel(); state.documents.set(videoKey('v0000000000'), { videoId: 'v0000000000', viewCount: 100 }); state.failDetails = true;
    expect(await refreshChannel(input, settings)).toMatchObject({ success: false, videosRefreshed: 0 });
    expect(state.documents.get(progressKey)?.lastRefreshAt).toBeUndefined();
    expect(state.documents.get(videoKey('v0000000000'))?.viewCount).toBe(100);
  });

  it('does not record a completed refresh after quota exhaustion', async () => {
    completeExistingChannel();
    for (const prefix of ['a', 'b', 'c', 'd', 'e', 'f']) for (const videoId of page(prefix)) state.documents.set(videoKey(videoId), { videoId });
    state.lowChecks = [false, true];
    expect(await refreshChannel(input, settings)).toMatchObject({ success: false, videosRefreshed: 250, error: 'Quota exhausted' });
    expect(state.documents.get(progressKey)?.lastRefreshAt).toBeUndefined();
  });
});

describe('channel configuration validation', () => {
  it('parses valid configuration', () => expect(parseChannelsConfig({ channels: [input], settings })).toEqual({ channels: [input], settings }));
  it('loads the checked-in example and defaults omitted settings', () => {
    const example = JSON.parse(readFileSync(new URL('../../../config/channels.json.example', import.meta.url), 'utf8'));
    expect(parseChannelsConfig(example).settings).toEqual(settings);
  });
  it.each([null, [], {}, { channels: 'bad', settings }, { channels: [null], settings }, { channels: [{ ...input, priority: '1' }], settings }, { channels: [input], settings: { ...settings, maxVideosPerChannel: -1 } }, { channels: [input], settings: { ...settings, includeShorts: 'false' } }])('rejects malformed configuration %#', (value) => expect(() => parseChannelsConfig(value)).toThrow());
});
