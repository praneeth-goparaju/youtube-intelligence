import { google, youtube_v3 } from 'googleapis';
import { config } from '../config.js';

let youtubeClient: youtube_v3.Youtube | null = null;
let quotaUsed = 0;
let ignoreQuotaChecks = false;

/**
 * Get or create YouTube API client
 * Includes timeout configuration to prevent indefinite hangs
 */
export function getYoutubeClient(): youtube_v3.Youtube {
  if (!youtubeClient) {
    youtubeClient = google.youtube({
      version: 'v3',
      auth: config.youtube.apiKey,
      timeout: config.scraper.apiTimeoutMs,
    });
  }
  return youtubeClient;
}

/**
 * Track quota usage
 */
export function addQuotaUsage(units: number): void {
  quotaUsed += units;
}

/**
 * Get current quota usage
 */
export function getQuotaUsed(): number {
  return quotaUsed;
}

/**
 * Get remaining quota
 */
export function getQuotaRemaining(): number {
  return config.quota.dailyLimit - quotaUsed;
}

/**
 * Check if quota is nearly exhausted
 */
export function isQuotaLow(): boolean {
  if (ignoreQuotaChecks) return false;
  return getQuotaRemaining() <= config.scraper.quotaWarningThreshold;
}

/**
 * Set whether to ignore quota checks (for --ignore-quota flag)
 */
export function setIgnoreQuota(ignore: boolean): void {
  ignoreQuotaChecks = ignore;
}

/**
 * Reset quota counter (for testing or new day)
 */
export function resetQuotaCounter(): void {
  quotaUsed = 0;
}

/**
 * Set quota usage (for resuming from progress)
 */
export function setQuotaUsed(units: number): void {
  quotaUsed = units;
}
