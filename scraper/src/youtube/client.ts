import { google, youtube_v3 } from 'googleapis';
import { config } from '../config.js';

let youtubeClient: youtube_v3.Youtube | null = null;
let quotaUsed = 0;
let quotaDate = getPacificDate();
let ignoreQuotaChecks = false;

/**
 * Get today's date in Pacific Time as YYYY-MM-DD (YouTube quota resets at midnight PT)
 */
export function getPacificDate(now: Date = new Date()): string {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/Los_Angeles',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(now);
}

/**
 * Reset the in-memory counter when a long run crosses midnight Pacific
 */
function rollOverQuotaIfNewDay(): void {
  const today = getPacificDate();
  if (today !== quotaDate) {
    quotaDate = today;
    quotaUsed = 0;
  }
}

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
  rollOverQuotaIfNewDay();
  quotaUsed += units;
}

/**
 * Get current quota usage
 */
export function getQuotaUsed(): number {
  rollOverQuotaIfNewDay();
  return quotaUsed;
}

/**
 * Get remaining quota
 */
export function getQuotaRemaining(): number {
  return config.quota.dailyLimit - getQuotaUsed();
}

/**
 * Check if quota is nearly exhausted
 */
export function isQuotaLow(): boolean {
  if (ignoreQuotaChecks) return false;
  return getQuotaRemaining() <= config.scraper.quotaWarningThreshold;
}

/**
 * Record that YouTube rejected a request with quotaExceeded: treat today's quota as used up
 */
export function markQuotaExhausted(): void {
  rollOverQuotaIfNewDay();
  quotaUsed = Math.max(quotaUsed, config.quota.dailyLimit);
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
  quotaDate = getPacificDate();
}

/**
 * Set quota usage (for resuming from progress)
 */
export function setQuotaUsed(units: number): void {
  quotaUsed = units;
  quotaDate = getPacificDate();
}
