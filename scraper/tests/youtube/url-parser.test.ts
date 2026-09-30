import { describe, it, expect } from 'vitest';
import { parseChannelUrl } from '../../src/youtube/url-parser.js';

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
