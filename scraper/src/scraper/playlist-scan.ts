/**
 * Scan one uploads-playlist page (newest first) for videos not yet stored.
 *
 * Stops at the first already-stored video: everything after it is older and was
 * seen by an earlier run. IDs that earlier runs dropped (filtered Shorts,
 * private/deleted videos) are never stored, so "whole page known" is not a
 * usable stop condition. Also stops once `maxVideos` playlist positions have
 * been scanned, matching the cap the initial scrape applies.
 */
export function scanPageForNewIds(
  pageIds: string[],
  storedIds: Set<string>,
  scannedSoFar: number,
  maxVideos: number | null
): { newIds: string[]; scanned: number; done: boolean } {
  const newIds: string[] = [];
  let scanned = scannedSoFar;

  for (const id of pageIds) {
    if (maxVideos && scanned >= maxVideos) return { newIds, scanned, done: true };
    if (storedIds.has(id)) return { newIds, scanned, done: true };
    newIds.push(id);
    scanned++;
  }

  return { newIds, scanned, done: false };
}

/**
 * Group new playlist IDs (collected newest first) into fetch/save batches
 * ordered OLDEST first.
 *
 * `scanPageForNewIds` stops at the newest stored video, so an interrupted update
 * must only ever leave a stored frontier that is contiguous from the old side:
 * every still-unsaved video is then newer than every video this run stored, and
 * the next run's scan reaches all of them before hitting a stored ID. Saving
 * newest first would store the top of the playlist and hide the older unsaved
 * videos forever. IDs that get filtered (Shorts, private/deleted) are never
 * stored, which is harmless here: a filtered ID in a saved batch is simply
 * rescanned (and filtered again) next run, and a batch that stored nothing
 * leaves the frontier where it was.
 */
export function planUpdateBatches(newIdsNewestFirst: string[], batchSize: number): string[][] {
  if (batchSize < 1) throw new Error(`batchSize must be >= 1 (got ${batchSize})`);
  const oldestFirst = [...newIdsNewestFirst].reverse();
  const batches: string[][] = [];
  for (let i = 0; i < oldestFirst.length; i += batchSize) {
    batches.push(oldestFirst.slice(i, i + batchSize));
  }
  return batches;
}
