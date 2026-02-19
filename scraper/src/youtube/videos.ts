import { getYoutubeClient, addQuotaUsage } from './client.js';
import { Timestamp } from 'firebase-admin/firestore';
import { Video, PlaylistItem, CalculatedMetrics, VideoThumbnails } from '../types/index.js';
import { parseDuration, isShortVideoDetailed } from '../utils/duration.js';
import {
  daysBetween,
  getDayOfWeek,
  getHourIST,
  VIDEO_CATEGORIES,
  retry,
} from '../utils/helpers.js';
import { config } from '../config.js';

// Retry configuration from centralized config
const API_MAX_RETRIES = config.scraper.maxRetries;
const API_BASE_DELAY_MS = config.scraper.retryDelayMs;

interface PlaylistPageResult {
  items: PlaylistItem[];
  nextPageToken: string | null;
  totalResults: number;
}

/**
 * Get videos from uploads playlist with pagination
 * Includes retry logic for transient errors
 */
export async function getPlaylistVideos(
  playlistId: string,
  pageToken?: string
): Promise<PlaylistPageResult> {
  const youtube = getYoutubeClient();

  return retry(
    async () => {
      const response = await youtube.playlistItems.list({
        part: ['snippet'],
        playlistId,
        maxResults: 50,
        pageToken,
      });
      addQuotaUsage(1);

      const items: PlaylistItem[] = (response.data.items || []).map((item) => ({
        videoId: item.snippet?.resourceId?.videoId || '',
        publishedAt: item.snippet?.publishedAt || '',
        title: item.snippet?.title || '',
        description: item.snippet?.description || '',
      }));

      return {
        items,
        nextPageToken: response.data.nextPageToken || null,
        totalResults: response.data.pageInfo?.totalResults || 0,
      };
    },
    API_MAX_RETRIES,
    API_BASE_DELAY_MS
  ).catch((error) => {
    throw new Error(`Failed to fetch playlist ${playlistId} after ${API_MAX_RETRIES} retries: ${(error as Error).message}`);
  });
}

interface YouTubeVideoData {
  id: string;
  snippet: {
    title: string;
    description: string;
    publishedAt: string;
    thumbnails: {
      default?: { url: string };
      medium?: { url: string };
      high?: { url: string };
      standard?: { url: string };
      maxres?: { url: string };
    };
    tags?: string[];
    categoryId: string;
    defaultLanguage?: string;
    defaultAudioLanguage?: string;
  };
  contentDetails: {
    duration: string;
    definition: string;
    caption: string;
    licensedContent: boolean;
  };
  statistics: {
    viewCount: string;
    likeCount: string;
    commentCount: string;
  };
  topicDetails?: {
    topicCategories?: string[];
  };
  status?: {
    madeForKids: boolean;
  };
}

/**
 * Get detailed video information for a batch of video IDs
 * Includes retry logic for transient errors
 */
export async function getVideoDetails(videoIds: string[]): Promise<YouTubeVideoData[]> {
  if (videoIds.length === 0) return [];
  if (videoIds.length > 50) {
    throw new Error(`Batch size exceeds 50: ${videoIds.length}`);
  }

  const youtube = getYoutubeClient();

  return retry(
    async () => {
      const response = await youtube.videos.list({
        part: ['snippet', 'contentDetails', 'statistics', 'topicDetails', 'status'],
        id: videoIds,
      });
      addQuotaUsage(1);

      return (response.data.items || []) as unknown as YouTubeVideoData[];
    },
    API_MAX_RETRIES,
    API_BASE_DELAY_MS
  ).catch((error) => {
    throw new Error(`Failed to fetch video details after ${API_MAX_RETRIES} retries: ${(error as Error).message}`);
  });
}

/**
 * Calculate derived metrics for a video
 * @param subscriberCount - Channel subscriber count, or null if hidden
 */
export function calculateVideoMetrics(
  video: {
    publishedAt: Date;
    viewCount: number;
    likeCount: number;
    commentCount: number;
    tags: string[];
  },
  subscriberCount: number | null
): CalculatedMetrics {
  const now = new Date();
  const daysSince = Math.max(1, daysBetween(video.publishedAt, now));

  return {
    engagementRate: video.viewCount > 0
      ? ((video.likeCount + video.commentCount) / video.viewCount) * 100
      : 0,
    likeRatio: video.viewCount > 0
      ? (video.likeCount / video.viewCount) * 100
      : 0,
    commentRatio: video.viewCount > 0
      ? (video.commentCount / video.viewCount) * 100
      : 0,
    // viewsPerSubscriber is 0 if subscriber count is hidden (null) or zero
    viewsPerSubscriber: (subscriberCount !== null && subscriberCount > 0)
      ? video.viewCount / subscriberCount
      : 0,
    viewsPerDay: video.viewCount / daysSince,
    publishDayOfWeek: getDayOfWeek(video.publishedAt),
    publishHourIST: getHourIST(video.publishedAt),
    tagCount: video.tags.length,
  };
}

/**
 * Transform YouTube API video data to our Video schema
 * @param subscriberCount - Channel subscriber count, or null if hidden
 */
export function transformVideoData(
  data: YouTubeVideoData,
  channelId: string,
  subscriberCount: number | null
): Omit<Video, 'thumbnailStoragePath'> {
  const publishedAt = new Date(data.snippet.publishedAt);
  const durationSeconds = parseDuration(data.contentDetails.duration);

  const thumbnails: VideoThumbnails = {
    default: data.snippet.thumbnails.default?.url || '',
    medium: data.snippet.thumbnails.medium?.url || '',
    high: data.snippet.thumbnails.high?.url || '',
    standard: data.snippet.thumbnails.standard?.url || null,
    maxres: data.snippet.thumbnails.maxres?.url || null,
  };

  const viewCount = parseInt(data.statistics.viewCount, 10) || 0;
  const likeCount = parseInt(data.statistics.likeCount, 10) || 0;
  const commentCount = parseInt(data.statistics.commentCount, 10) || 0;
  const tags = data.snippet.tags || [];

  const calculated = calculateVideoMetrics(
    {
      publishedAt,
      viewCount,
      likeCount,
      commentCount,
      tags,
    },
    subscriberCount
  );

  return {
    // Identifiers
    videoId: data.id,
    channelId,

    // Basic Info
    title: data.snippet.title,
    description: data.snippet.description,
    publishedAt: Timestamp.fromDate(publishedAt),

    // Thumbnails
    thumbnails,

    // Duration
    duration: data.contentDetails.duration,
    durationSeconds,

    // Statistics
    viewCount,
    likeCount,
    commentCount,

    // Tags
    tags,

    // Metadata
    categoryId: data.snippet.categoryId,
    categoryName: VIDEO_CATEGORIES[data.snippet.categoryId] || 'Unknown',
    defaultLanguage: data.snippet.defaultLanguage || null,
    defaultAudioLanguage: data.snippet.defaultAudioLanguage || null,
    madeForKids: data.status?.madeForKids || false,

    // Content Details
    definition: data.contentDetails.definition,
    caption: data.contentDetails.caption === 'true',
    licensedContent: data.contentDetails.licensedContent,

    // Topic Details
    topicCategories: data.topicDetails?.topicCategories || [],

    // Derived Fields
    isShort: isShortVideoDetailed(durationSeconds, data.snippet.title, data.snippet.description).isShort,
    videoUrl: `https://www.youtube.com/watch?v=${data.id}`,

    // Scraping Info
    scrapedAt: Timestamp.now(),

    // Calculated Metrics
    calculated,
  };
}

/**
 * Get thumbnail URL for specified quality
 */
export function getThumbnailUrl(videoId: string, quality: string = 'mqdefault'): string {
  return `https://img.youtube.com/vi/${videoId}/${quality}.jpg`;
}
