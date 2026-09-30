import { describe, it, expect } from 'vitest';
import {
  getDayOfWeek,
  getHourIST,
  isQuotaExceededError,
  isRetryableError,
  retry,
  QuotaExhaustedError,
} from '../../src/utils/helpers.js';

// Shape of googleapis (Gaxios) errors
function apiError(status: number, reason?: string) {
  return Object.assign(new Error(`HTTP ${status}`), {
    response: { status },
    errors: reason ? [{ reason }] : undefined,
  });
}

describe('getDayOfWeek / getHourIST', () => {
  it('reports the IST day, not the host/UTC day', () => {
    // Sunday 20:30 UTC = Monday 02:00 IST
    const date = new Date('2024-01-07T20:30:00Z');
    expect(getDayOfWeek(date)).toBe('Monday');
    expect(getHourIST(date)).toBe(2);
  });
});

describe('API error classification', () => {
  it.each([
    ['quotaExceeded 403', apiError(403, 'quotaExceeded'), true, false],
    ['dailyLimitExceeded 403', apiError(403, 'dailyLimitExceeded'), true, false],
    ['rateLimitExceeded 403', apiError(403, 'rateLimitExceeded'), false, true],
    ['forbidden 403', apiError(403, 'forbidden'), false, false],
    ['404', apiError(404, 'playlistNotFound'), false, false],
    ['400', apiError(400, 'badRequest'), false, false],
    ['429', apiError(429), false, true],
    ['503', apiError(503), false, true],
    ['network error (no status)', new Error('ECONNRESET'), false, true],
  ])('%s', (_label, error, quota, retryable) => {
    expect(isQuotaExceededError(error)).toBe(quota);
    expect(isRetryableError(error)).toBe(retryable);
  });
});

describe('retry', () => {
  function failingWith(error: Error) {
    let calls = 0;
    const fn = async () => {
      calls++;
      throw error;
    };
    return { fn, calls: () => calls };
  }

  it('does not retry a 404', async () => {
    const f = failingWith(apiError(404));
    await expect(retry(f.fn, 3, 0)).rejects.toThrow('HTTP 404');
    expect(f.calls()).toBe(1);
  });

  it('turns quotaExceeded into QuotaExhaustedError without retrying', async () => {
    const f = failingWith(apiError(403, 'quotaExceeded'));
    await expect(retry(f.fn, 3, 0)).rejects.toBeInstanceOf(QuotaExhaustedError);
    expect(f.calls()).toBe(1);
  });

  it('retries transient errors up to maxRetries', async () => {
    const f = failingWith(apiError(503));
    await expect(retry(f.fn, 3, 0)).rejects.toThrow('HTTP 503');
    expect(f.calls()).toBe(3);
  });
});
