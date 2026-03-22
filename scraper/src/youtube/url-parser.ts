export interface UrlPattern {
  regex: RegExp;
  type: 'handle' | 'channelId' | 'customUrl' | 'user';
}

export const URL_PATTERNS: UrlPattern[] = [
  { regex: /@([^\/\?]+)/, type: 'handle' },
  { regex: /\/channel\/(UC[a-zA-Z0-9_-]{22})/, type: 'channelId' },
  { regex: /\/c\/([^\/\?]+)/, type: 'customUrl' },
  { regex: /\/user\/([^\/\?]+)/, type: 'user' },
];

/**
 * Parse a YouTube channel URL and extract the identifier and type.
 * Pure function with no side effects — safe to import in tests.
 */
export function parseChannelUrl(url: string): { identifier: string; type: UrlPattern['type'] } | null {
  for (const pattern of URL_PATTERNS) {
    const match = url.match(pattern.regex);
    if (match) {
      return { identifier: match[1], type: pattern.type };
    }
  }
  return null;
}
