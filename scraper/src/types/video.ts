import { Timestamp } from 'firebase-admin/firestore';

export interface VideoThumbnails {
  default: string;
  medium: string;
  high: string;
  standard: string | null;
  maxres: string | null;
}

export interface CalculatedMetrics {
  engagementRate: number;
  likeRatio: number;
  commentRatio: number;
  viewsPerSubscriber: number;
  viewsPerDay: number;
  performancePercentile?: number;
  publishDayOfWeek: string;
  publishHourIST: number;
  titleLength: number;
  descriptionLength: number;
  tagCount: number;
  hasNumberInTitle: boolean;
  hasEmojiInTitle: boolean;
  hasTeluguInTitle: boolean;
  hasEnglishInTitle: boolean;
}

export interface Video {
  // Identifiers
  videoId: string;
  channelId: string;

  // Basic Info
  title: string;
  description: string;
  publishedAt: Timestamp;

  // Thumbnails
  thumbnails: VideoThumbnails;
  thumbnailStoragePath: string;

  // Duration
  duration: string;
  durationSeconds: number;

  // Statistics
  viewCount: number;
  likeCount: number;
  commentCount: number;

  // Tags
  tags: string[];

  // Metadata
  categoryId: string;
  categoryName: string;
  defaultLanguage: string | null;
  defaultAudioLanguage: string | null;
  madeForKids: boolean;

  // Content Details
  definition: string;
  caption: boolean;
  licensedContent: boolean;

  // Topic Details
  topicCategories: string[];

  // Derived Fields
  isShort: boolean;
  videoUrl: string;

  // Scraping Info
  scrapedAt: Timestamp;

  // Calculated Metrics
  calculated: CalculatedMetrics;
}

export interface PlaylistItem {
  videoId: string;
  publishedAt: string;
  title: string;
  description: string;
}
