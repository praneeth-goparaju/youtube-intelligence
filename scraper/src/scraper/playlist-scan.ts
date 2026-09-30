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
