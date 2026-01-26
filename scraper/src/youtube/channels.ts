import { getYoutubeClient, addQuotaUsage } from './client.js';
import { Timestamp } from 'firebase-admin/firestore';
import { Channel, ChannelInput } from '../types/index.js';

interface YouTubeChannelData {
  id: string;
  snippet: {
    title: string;
    description: string;
    customUrl?: string;
    thumbnails: {
      default?: { url: string };
      medium?: { url: string };
      high?: { url: string };
    };
    country?: string;
    publishedAt: string;
  };
  statistics: {
    subscriberCount: string;
    videoCount: string;
    viewCount: string;
  };
  brandingSettings?: {
    image?: {
      bannerExternalUrl?: string;
    };
  };
}

/**
 * Fetch channel details from YouTube API
 */
export async function getChannelDetails(channelId: string): Promise<YouTubeChannelData | null> {
  const youtube = getYoutubeClient();

  try {
    const response = await youtube.channels.list({
      part: ['snippet', 'statistics', 'brandingSettings'],
      id: [channelId],
    });
    addQuotaUsage(1);

    const channel = response.data.items?.[0];
    if (!channel) {
      return null;
    }

    return channel as unknown as YouTubeChannelData;
  } catch (error) {
    throw new Error(`Failed to fetch channel ${channelId}: ${(error as Error).message}`);
  }
}

/**
 * Transform YouTube API response to our Channel schema
 */
export function transformChannelData(
  data: YouTubeChannelData,
  input: ChannelInput
): Omit<Channel, 'thumbnailStoragePath'> {
  const now = Timestamp.now();

  return {
    // Identifiers
    channelId: data.id,

    // Basic Info
    channelTitle: data.snippet.title,
    channelDescription: data.snippet.description,
    customUrl: data.snippet.customUrl || '',

    // Statistics
    subscriberCount: parseInt(data.statistics.subscriberCount, 10) || 0,
    videoCount: parseInt(data.statistics.videoCount, 10) || 0,
    viewCount: parseInt(data.statistics.viewCount, 10) || 0,

    // Images
    thumbnailUrl: data.snippet.thumbnails.high?.url ||
                  data.snippet.thumbnails.medium?.url ||
                  data.snippet.thumbnails.default?.url || '',
    bannerUrl: data.brandingSettings?.image?.bannerExternalUrl || null,

    // Metadata
    country: data.snippet.country || null,
    publishedAt: Timestamp.fromDate(new Date(data.snippet.publishedAt)),

    // Categorization
    category: input.category,
    priority: input.priority,

    // Scraping Info
    sourceUrl: input.url,
    scrapedAt: now,
    lastUpdatedAt: now,
  };
}

/**
 * Get the uploads playlist ID for a channel
 * Channel IDs start with "UC", uploads playlist IDs start with "UU"
 */
export function getUploadsPlaylistId(channelId: string): string {
  if (!channelId.startsWith('UC')) {
    throw new Error(`Invalid channel ID format: ${channelId}`);
  }
  return 'UU' + channelId.substring(2);
}
