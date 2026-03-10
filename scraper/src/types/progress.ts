import { Timestamp } from 'firebase-admin/firestore';

export type ProgressStatus = 'pending' | 'in_progress' | 'completed' | 'failed';
export type ProgressPhase = 'scraping' | 'thumbnails' | 'calculations';

export interface ScrapeProgress {
  // Identifiers
  channelId: string;
  channelTitle: string;
  sourceUrl: string;

  // Status
  status: ProgressStatus;

  // Progress
  phase: ProgressPhase;
  totalVideos: number;
  videosProcessed: number;
  thumbnailsDownloaded: number;

  // Resume Point
  lastProcessedVideoId: string | null;
  lastPlaylistPageToken: string | null;

  // Quota Tracking (for resuming within same day)
  quotaUsed?: number;
  quotaDate?: string;  // ISO date string (YYYY-MM-DD) in Pacific Time

  // Incremental Update Tracking
  lastUpdateAt?: Timestamp | null;
  lastUpdateNewVideos?: number;

  // Stats Refresh Tracking
  lastRefreshAt?: Timestamp | null;
  lastRefreshVideosUpdated?: number;

  // Timestamps
  startedAt: Timestamp;
  lastProcessedAt: Timestamp;
  completedAt: Timestamp | null;

  // Error Info
  errorMessage: string | null;
  errorStack: string | null;
  retryCount: number;
}

export interface UnresolvedChannel {
  id: string;              // URL-derived ID (from urlToProgressId)
  sourceUrl: string;
  errorMessage: string;
  retryCount: number;
  firstSeenAt: Timestamp;
  lastAttemptAt: Timestamp;
}

export interface SessionStats {
  startTime: Date;
  channelsCompleted: number;
  channelsTotal: number;
  videosScraped: number;
  thumbnailsDownloaded: number;
  thumbnailsFailed: number;
  quotaUsed: number;
  quotaTotal: number;
}
