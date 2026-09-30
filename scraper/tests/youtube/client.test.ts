import { describe, it, expect, vi, afterEach } from 'vitest';

// Avoid loading env vars via the real config module
vi.mock('../../src/config.js', () => ({
  config: {
    youtube: { apiKey: 'test' },
    quota: { dailyLimit: 10000 },
    scraper: { quotaWarningThreshold: 500, apiTimeoutMs: 1000 },
  },
}));

import { addQuotaUsage, getQuotaUsed, setQuotaUsed } from '../../src/youtube/client.js';

afterEach(() => {
  vi.useRealTimers();
});

describe('quota counter', () => {
  it('resets when a run crosses midnight Pacific', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2024-03-10T07:30:00Z')); // 23:30 PT, Mar 9
    setQuotaUsed(9000);
    addQuotaUsage(100);
    expect(getQuotaUsed()).toBe(9100);

    vi.setSystemTime(new Date('2024-03-10T08:30:00Z')); // 00:30 PT, Mar 10
    expect(getQuotaUsed()).toBe(0);
    addQuotaUsage(1);
    expect(getQuotaUsed()).toBe(1);
  });
});
