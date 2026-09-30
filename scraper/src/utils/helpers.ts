/**
 * Delay execution for specified milliseconds
 */
export function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Chunk an array into smaller arrays of specified size
 */
export function chunk<T>(array: T[], size: number): T[][] {
  const chunks: T[][] = [];
  for (let i = 0; i < array.length; i += size) {
    chunks.push(array.slice(i, i + size));
  }
  return chunks;
}

/**
 * Calculate days between two dates
 */
export function daysBetween(date1: Date, date2: Date): number {
  const MS_PER_DAY = 1000 * 60 * 60 * 24;
  const diff = Math.abs(date2.getTime() - date1.getTime());
  return Math.floor(diff / MS_PER_DAY);
}

const IST_OFFSET_MS = 5.5 * 60 * 60 * 1000; // IST is UTC+5:30 (no DST)

/**
 * Get day of week in IST (same timezone as getHourIST, independent of host timezone)
 */
export function getDayOfWeek(date: Date): string {
  const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
  return days[new Date(date.getTime() + IST_OFFSET_MS).getUTCDay()];
}

/**
 * Get hour in IST (UTC+5:30)
 */
export function getHourIST(date: Date): number {
  return new Date(date.getTime() + IST_OFFSET_MS).getUTCHours();
}

/**
 * Check if string contains Telugu script
 */
export function containsTelugu(text: string): boolean {
  // Telugu Unicode range: 0C00-0C7F
  return /[\u0C00-\u0C7F]/.test(text);
}

/**
 * Check if string contains English letters
 */
export function containsEnglish(text: string): boolean {
  return /[a-zA-Z]/.test(text);
}

/**
 * Check if string contains a number
 */
export function containsNumber(text: string): boolean {
  return /\d/.test(text);
}

/**
 * Check if string contains emoji
 */
export function containsEmoji(text: string): boolean {
  const emojiRegex = /[\u{1F600}-\u{1F64F}]|[\u{1F300}-\u{1F5FF}]|[\u{1F680}-\u{1F6FF}]|[\u{1F1E0}-\u{1F1FF}]|[\u{2600}-\u{26FF}]|[\u{2700}-\u{27BF}]/u;
  return emojiRegex.test(text);
}

/**
 * Thrown when the YouTube API reports the daily quota is used up.
 * Its message matches the 'Quota exhausted' signal runScraper stops on.
 */
export class QuotaExhaustedError extends Error {
  constructor() {
    super('Quota exhausted');
    this.name = 'QuotaExhaustedError';
  }
}

/**
 * Extract HTTP status and the first error reason from a googleapis (Gaxios) error.
 */
function getApiErrorInfo(error: unknown): { status?: number; reason?: string } {
  const err = error as {
    code?: number | string;
    status?: number;
    errors?: Array<{ reason?: string }>;
    response?: { status?: number; data?: { error?: { errors?: Array<{ reason?: string }> } } };
  };
  const status = err?.response?.status ?? err?.status ?? (typeof err?.code === 'number' ? err.code : undefined);
  const reason = err?.errors?.[0]?.reason ?? err?.response?.data?.error?.errors?.[0]?.reason;
  return { status, reason };
}

/**
 * True if the error is YouTube's daily quota exhaustion (403 quotaExceeded / dailyLimitExceeded).
 */
export function isQuotaExceededError(error: unknown): boolean {
  if (error instanceof QuotaExhaustedError) return true;
  const { status, reason } = getApiErrorInfo(error);
  return status === 403 && (reason === 'quotaExceeded' || reason === 'dailyLimitExceeded');
}

/**
 * True if retrying the request could succeed: network errors (no HTTP status),
 * 5xx, 429 and 403 rate-limit reasons. Other 4xx (400, 404, quotaExceeded) are permanent.
 */
export function isRetryableError(error: unknown): boolean {
  const { status, reason } = getApiErrorInfo(error);
  if (status === undefined) return true;
  if (status >= 500 || status === 429) return true;
  return status === 403 && (reason === 'rateLimitExceeded' || reason === 'userRateLimitExceeded');
}

/**
 * Retry a function with exponential backoff.
 * Non-retryable errors are thrown immediately; quota exhaustion becomes QuotaExhaustedError.
 */
export async function retry<T>(
  fn: () => Promise<T>,
  maxRetries: number,
  baseDelayMs: number
): Promise<T> {
  let lastError: Error | undefined;

  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      if (isQuotaExceededError(error)) throw new QuotaExhaustedError();
      lastError = error as Error;
      if (!isRetryableError(error)) break;
      if (attempt < maxRetries - 1) {
        const delayTime = baseDelayMs * Math.pow(2, attempt);
        await delay(delayTime);
      }
    }
  }

  throw lastError;
}

/**
 * Format number with commas
 */
export function formatNumber(num: number): string {
  return num.toLocaleString('en-US');
}

/**
 * Format bytes to human readable size
 */
export function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * YouTube video category mapping
 */
export const VIDEO_CATEGORIES: Record<string, string> = {
  '1': 'Film & Animation',
  '2': 'Autos & Vehicles',
  '10': 'Music',
  '15': 'Pets & Animals',
  '17': 'Sports',
  '18': 'Short Movies',
  '19': 'Travel & Events',
  '20': 'Gaming',
  '21': 'Videoblogging',
  '22': 'People & Blogs',
  '23': 'Comedy',
  '24': 'Entertainment',
  '25': 'News & Politics',
  '26': 'Howto & Style',
  '27': 'Education',
  '28': 'Science & Technology',
  '29': 'Nonprofits & Activism',
  '30': 'Movies',
  '31': 'Anime/Animation',
  '32': 'Action/Adventure',
  '33': 'Classics',
  '34': 'Comedy',
  '35': 'Documentary',
  '36': 'Drama',
  '37': 'Family',
  '38': 'Foreign',
  '39': 'Horror',
  '40': 'Sci-Fi/Fantasy',
  '41': 'Thriller',
  '42': 'Shorts',
  '43': 'Shows',
  '44': 'Trailers',
};
