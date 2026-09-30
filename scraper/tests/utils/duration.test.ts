import { describe, it, expect } from 'vitest';
import { parseDuration, formatDuration, isShortVideoDetailed } from '../../src/utils/duration.js';

describe('parseDuration', () => {
  it.each([
    ['minutes and seconds', 'PT15M33S', 933],
    ['hours, minutes and seconds', 'PT1H30M45S', 5445],
    ['hours only', 'PT2H', 7200],
    ['minutes only', 'PT45M', 2700],
    ['seconds only', 'PT30S', 30],
    ['empty string', '', 0],
    ['invalid format', 'invalid', 0],
    ['bare period designator P', 'P', 0],
  ])('parses %s', (_label, input, expected) => {
    expect(parseDuration(input)).toBe(expected);
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
  it.each([
    ['90s with #shorts (3-minute Shorts limit)', 90, 'Quick recipe #shorts', '', true],
    ['180s with #Shorts in description', 180, 'Quick recipe', 'Try it #Shorts', true],
    ['181s with #shorts', 181, 'Quick recipe #shorts', '', false],
    ['45s without any indicator', 45, 'Teaser', '', false],
    ['10s without any indicator', 10, 'Clip', '', true],
    ['zero duration (live/upcoming)', 0, 'Live now', '', false],
    ['long video', 900, 'Full recipe', '#shorts', false],
  ])('%s', (_label, seconds, title, description, expected) => {
    expect(isShortVideoDetailed(seconds, title, description).isShort).toBe(expected);
  });
});
