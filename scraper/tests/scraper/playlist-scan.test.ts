import { describe, it, expect } from 'vitest';
import { planUpdateBatches, scanPageForNewIds } from '../../src/scraper/playlist-scan.js';

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

describe('planUpdateBatches', () => {
  it('orders batches oldest first', () => {
    expect(planUpdateBatches(['n5', 'n4', 'n3', 'n2', 'n1'], 2)).toEqual([['n1', 'n2'], ['n3', 'n4'], ['n5']]);
  });

  it('does not mutate the input', () => {
    const ids = ['b', 'a'];
    planUpdateBatches(ids, 1);
    expect(ids).toEqual(['b', 'a']);
  });

  /**
   * Simulate an --update interrupted after `batchesSaved` batches, then a re-run.
   * The playlist is newest first; IDs starting with 'short' are filtered and never stored.
   */
  function simulate(playlist: string[], initiallyStored: string[], batchSize: number, batchesSaved: number) {
    const stored = new Set(initiallyStored);
    const isFiltered = (id: string) => id.startsWith('short');
    const scan = (): string[] => scanPageForNewIds(playlist, stored, 0, null).newIds;
    const saveBatches = (ids: string[], limit: number) => {
      for (const batch of planUpdateBatches(ids, batchSize).slice(0, limit)) {
        for (const id of batch) if (!isFiltered(id)) stored.add(id);
      }
    };

    saveBatches(scan(), batchesSaved); // interrupted run
    saveBatches(scan(), Infinity); // re-run to completion
    return stored;
  }

  it('an interrupted update followed by a re-run stores every new video', () => {
    const playlist = ['n6', 'n5', 'n4', 'n3', 'n2', 'n1', 'old2', 'old1'];
    const stored = simulate(playlist, ['old2', 'old1'], 2, 1);
    expect([...stored].sort()).toEqual(['n1', 'n2', 'n3', 'n4', 'n5', 'n6', 'old1', 'old2']);
  });

  it('handles filtered Shorts at the oldest end and inside saved batches', () => {
    // Oldest pending video is a Short; the first saved batch stores only 'n1'
    const playlist = ['n4', 'short2', 'n3', 'n2', 'n1', 'short1', 'old1'];
    for (const batchesSaved of [0, 1, 2, 3]) {
      const stored = simulate(playlist, ['old1'], 2, batchesSaved);
      expect([...stored].sort()).toEqual(['n1', 'n2', 'n3', 'n4', 'old1']);
    }
  });

  it('handles a first batch made only of filtered Shorts', () => {
    const playlist = ['n2', 'n1', 'short2', 'short1', 'old1'];
    const stored = simulate(playlist, ['old1'], 2, 1);
    expect([...stored].sort()).toEqual(['n1', 'n2', 'old1']);
  });
});
