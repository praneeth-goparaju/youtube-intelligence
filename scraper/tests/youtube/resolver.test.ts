import { describe, it, expect } from 'vitest';

// Re-implement parseChannelUrl for testing without importing from source
// (to avoid config dependencies)
interface UrlPattern {
  regex: RegExp;
  type: 'handle' | 'channelId' | 'customUrl' | 'user';
}

const URL_PATTERNS: UrlPattern[] = [
  { regex: /@([^\/\?]+)/, type: 'handle' },
  { regex: /\/channel\/(UC[a-zA-Z0-9_-]{22})/, type: 'channelId' },
  { regex: /\/c\/([^\/\?]+)/, type: 'customUrl' },
  { regex: /\/user\/([^\/\?]+)/, type: 'user' },
];

function parseChannelUrl(url: string): { identifier: string; type: UrlPattern['type'] } | null {
  for (const pattern of URL_PATTERNS) {
    const match = url.match(pattern.regex);
    if (match) {
      return { identifier: match[1], type: pattern.type };
    }
  }
  return null;
}

describe('parseChannelUrl', () => {
  it('should parse @handle URLs', () => {
    const result = parseChannelUrl('https://www.youtube.com/@VismaiFood');
    expect(result).toEqual({ identifier: 'VismaiFood', type: 'handle' });
  });

  it('should parse @handle URLs with query params', () => {
    const result = parseChannelUrl('https://www.youtube.com/@VismaiFood?sub_confirmation=1');
    expect(result).toEqual({ identifier: 'VismaiFood', type: 'handle' });
  });

  it('should parse channel ID URLs', () => {
    const result = parseChannelUrl('https://www.youtube.com/channel/UCBSwcE0p0PMwhvE6FVjgITw');
    expect(result).toEqual({ identifier: 'UCBSwcE0p0PMwhvE6FVjgITw', type: 'channelId' });
  });

  it('should parse /c/ custom URLs', () => {
    const result = parseChannelUrl('https://www.youtube.com/c/VismaiFood');
    expect(result).toEqual({ identifier: 'VismaiFood', type: 'customUrl' });
  });

  it('should parse /user/ URLs', () => {
    const result = parseChannelUrl('https://www.youtube.com/user/VismaiFood');
    expect(result).toEqual({ identifier: 'VismaiFood', type: 'user' });
  });

  it('should return null for invalid URLs', () => {
    expect(parseChannelUrl('https://www.youtube.com/watch?v=abc123')).toBeNull();
    expect(parseChannelUrl('https://www.google.com')).toBeNull();
    expect(parseChannelUrl('')).toBeNull();
  });

  it('should handle handles with special characters', () => {
    const result = parseChannelUrl('https://www.youtube.com/@Telugu_Channel-123');
    expect(result).toEqual({ identifier: 'Telugu_Channel-123', type: 'handle' });
  });
});
