import { describe, it, expect } from 'vitest';
import { scanPageForNewIds } from '../../src/scraper/playlist-scan.js';

describe('scanPageForNewIds', () => {
  it('stops at the first stored video even when the page has never-stored (filtered) IDs', () => {
    // 'short1' was filtered out by an earlier run, so it is never stored
    const result = scanPageForNewIds(['new1', 'short1', 'old1', 'old2'], new Set(['old1', 'old2']), 0, null);
    expect(result).toEqual({ newIds: ['new1', 'short1'], scanned: 2, done: true });
  });

  it('continues to the next page when nothing on the page is stored', () => {
    const result = scanPageForNewIds(['a', 'b'], new Set(), 0, null);
    expect(result).toEqual({ newIds: ['a', 'b'], scanned: 2, done: false });
  });

  it('respects maxVideosPerChannel across pages', () => {
    const result = scanPageForNewIds(['c', 'd', 'e'], new Set(), 49, 50);
    expect(result).toEqual({ newIds: ['c'], scanned: 50, done: true });
  });
});
