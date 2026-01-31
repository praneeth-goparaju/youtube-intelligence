import { Timestamp } from 'firebase-admin/firestore';

export interface ChannelInput {
  url: string;
  category: string;
  priority: number;
}

export interface ChannelsConfig {
  channels: ChannelInput[];
  settings: {
    maxVideosPerChannel: number | null;
    includeShorts: boolean;
    includePrivate: boolean;
    skipShortThumbnails: boolean;
  };
}

export interface Channel {
  // Identifiers
  channelId: string;

  // Basic Info
  channelTitle: string;
  channelDescription: string;
  customUrl: string;

  // Statistics
  subscriberCount: number | null;  // null if channel hides subscriber count
  videoCount: number;
  viewCount: number;

  // Images
  thumbnailUrl: string;
  thumbnailStoragePath: string;
  bannerUrl: string | null;

  // Metadata
  country: string | null;
  publishedAt: Timestamp;

  // Categorization
  category: string;
  priority: number;

  // Scraping Info
  sourceUrl: string;
  scrapedAt: Timestamp;
  lastUpdatedAt: Timestamp;

  // Calculated (populated in Phase 3)
  avgViewsPerVideo?: number;
  avgEngagementRate?: number;
  uploadFrequency?: string;
}

export interface ResolvedChannel {
  channelId: string;
  resolvedFrom: 'handle' | 'channelId' | 'customUrl' | 'user';
  quotaCost: number;
}
