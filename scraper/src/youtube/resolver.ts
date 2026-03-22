import { getYoutubeClient, addQuotaUsage } from './client.js';
import { ResolvedChannel } from '../types/index.js';
import { logger } from '../utils/logger.js';
import { parseChannelUrl } from './url-parser.js';

export { parseChannelUrl } from './url-parser.js';

// Type for YouTube API params with forHandle support (not in type definitions)
interface ChannelListParams {
  part: string[];
  id?: string[];
  forHandle?: string;
  forUsername?: string;
}

interface SearchListParams {
  part: string[];
  q: string;
  type: string[];
  maxResults: number;
}

/**
 * Resolve a YouTube channel URL to a channel ID
 */
export async function resolveChannelUrl(url: string): Promise<ResolvedChannel> {
  const parsed = parseChannelUrl(url);

  if (!parsed) {
    throw new Error(`Unable to parse channel URL: ${url}`);
  }

  const youtube = getYoutubeClient();
  const { identifier, type } = parsed;

  // Direct channel ID - no API call needed
  if (type === 'channelId') {
    return {
      channelId: identifier,
      resolvedFrom: 'channelId',
      quotaCost: 0,
    };
  }

  // Handle - use forHandle parameter (1 quota unit)
  if (type === 'handle') {
    try {
      const params: ChannelListParams = {
        part: ['id'],
        forHandle: identifier,
      };
      const response = await youtube.channels.list(params as any);
      addQuotaUsage(1);

      const channelId = response.data.items?.[0]?.id;
      if (!channelId) {
        throw new Error(`Channel not found for handle: @${identifier}`);
      }

      return {
        channelId,
        resolvedFrom: 'handle',
        quotaCost: 1,
      };
    } catch (error) {
      throw new Error(`Failed to resolve handle @${identifier}: ${(error as Error).message}`);
    }
  }

  // User - use forUsername parameter (1 quota unit)
  if (type === 'user') {
    try {
      const params: ChannelListParams = {
        part: ['id'],
        forUsername: identifier,
      };
      const response = await youtube.channels.list(params as any);
      addQuotaUsage(1);

      const channelId = response.data.items?.[0]?.id;
      if (!channelId) {
        throw new Error(`Channel not found for username: ${identifier}`);
      }

      return {
        channelId,
        resolvedFrom: 'user',
        quotaCost: 1,
      };
    } catch (error) {
      throw new Error(`Failed to resolve username ${identifier}: ${(error as Error).message}`);
    }
  }

  // Custom URL - try handle first, then search (expensive!)
  if (type === 'customUrl') {
    logger.warn(`Custom URL /c/${identifier} - trying as handle first...`);

    // First try as a handle (most custom URLs work this way now)
    try {
      const params: ChannelListParams = {
        part: ['id'],
        forHandle: identifier,
      };
      const response = await youtube.channels.list(params as any);
      addQuotaUsage(1);

      const channelId = response.data.items?.[0]?.id;
      if (channelId) {
        return {
          channelId,
          resolvedFrom: 'customUrl',
          quotaCost: 1,
        };
      }
    } catch {
      // Continue to search
    }

    // Fall back to search (100 quota units - avoid if possible!)
    logger.warn(`Handle lookup failed, using search API (100 units)...`);
    try {
      const searchParams: SearchListParams = {
        part: ['snippet'],
        q: identifier,
        type: ['channel'],
        maxResults: 1,
      };
      const searchResponse = await youtube.search.list(searchParams as any);
      addQuotaUsage(100);

      const channelId = searchResponse.data.items?.[0]?.snippet?.channelId;
      if (!channelId) {
        throw new Error(`Channel not found for custom URL: /c/${identifier}`);
      }

      return {
        channelId,
        resolvedFrom: 'customUrl',
        quotaCost: 101, // 1 for handle attempt + 100 for search
      };
    } catch (error) {
      throw new Error(`Failed to resolve custom URL /c/${identifier}: ${(error as Error).message}`);
    }
  }

  throw new Error(`Unsupported URL type: ${type}`);
}
