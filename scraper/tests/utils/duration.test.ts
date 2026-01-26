import { describe, it, expect } from 'vitest';
import { parseDuration, formatDuration, isShortVideo } from '../../src/utils/duration.js';

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

describe('isShortVideo', () => {
  it('should return true for videos <= 60 seconds', () => {
    expect(isShortVideo(60)).toBe(true);
    expect(isShortVideo(30)).toBe(true);
    expect(isShortVideo(1)).toBe(true);
  });

  it('should return false for videos > 60 seconds', () => {
    expect(isShortVideo(61)).toBe(false);
    expect(isShortVideo(120)).toBe(false);
    expect(isShortVideo(3600)).toBe(false);
  });
});
