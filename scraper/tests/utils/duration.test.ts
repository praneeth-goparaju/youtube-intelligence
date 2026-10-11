import { describe, it, expect } from 'vitest';
import { parseDuration, formatDuration, isShortVideoDetailed } from '../../src/utils/duration.js';

describe('parseDuration', () => {
  it('should parse minutes and seconds', () => {
    expect(parseDuration('PT15M33S')).toBe(933);
  });

  it('should parse hours, minutes and seconds', () => {
    expect(parseDuration('PT1H30M45S')).toBe(5445);
  });

  it('should parse hours only', () => {
    expect(parseDuration('PT2H')).toBe(7200);
  });

  it('should parse minutes only', () => {
    expect(parseDuration('PT45M')).toBe(2700);
  });

  it('should parse seconds only', () => {
    expect(parseDuration('PT30S')).toBe(30);
  });

  it('should return 0 for empty string', () => {
    expect(parseDuration('')).toBe(0);
  });

  it('should return 0 for invalid format', () => {
    expect(parseDuration('invalid')).toBe(0);
  });

  it('should return 0 for null-like values', () => {
    expect(parseDuration('P')).toBe(0);
  });
});

describe('formatDuration', () => {
  it('should format seconds only', () => {
    expect(formatDuration(45)).toBe('45s');
  });

  it('should format minutes and seconds', () => {
    expect(formatDuration(125)).toBe('2m 5s');
  });

  it('should format hours, minutes and seconds', () => {
    expect(formatDuration(3665)).toBe('1h 1m 5s');
  });

  it('should handle zero', () => {
    expect(formatDuration(0)).toBe('0s');
  });
});

describe('isShortVideoDetailed', () => {
  const base = { durationSeconds: 120, title: 'Recipe #Shorts', description: '', publishedAt: new Date('2025-01-01T00:00:00Z'), videoId: 'abcdefghijk' };
  it.each([61, 120, 180])('recognizes explicit Shorts metadata for an eligible %i-second upload', (durationSeconds) => {
    expect(isShortVideoDetailed({ ...base, durationSeconds })).toMatchObject({ isShort: true, confidence: 'medium' });
  });
  it('does not classify a pre-expansion two-minute video as a Short', () => {
    expect(isShortVideoDetailed({ ...base, publishedAt: new Date('2024-01-01T00:00:00Z') }).isShort).toBe(false);
  });
  it('rejects a video longer than three minutes', () => {
    expect(isShortVideoDetailed({ ...base, durationSeconds: 181 }).isShort).toBe(false);
  });
  it.each([0, 10, 45, 120])('does not infer Shorts solely from a %i-second duration', (durationSeconds) => {
    expect(isShortVideoDetailed({ ...base, title: 'Recipe', durationSeconds })).toMatchObject({ isShort: false, confidence: 'low' });
  });
  it('accepts a link to the video itself but not a link to somebody else’s Short', () => {
    expect(isShortVideoDetailed({ ...base, title: 'Recipe', description: 'https://www.youtube.com/shorts/abcdefghijk' }).isShort).toBe(true);
    expect(isShortVideoDetailed({ ...base, title: 'Recipe', description: 'https://www.youtube.com/shorts/other-video' }).isShort).toBe(false);
  });
});
