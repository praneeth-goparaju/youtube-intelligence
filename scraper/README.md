# Phase 1: YouTube Scraper

A TypeScript-based YouTube data collection system that extracts channel and video metadata using the YouTube Data API v3, with automatic progress tracking and resume capability.

## Overview

The scraper is responsible for:
- Resolving various YouTube URL formats to channel IDs
- Fetching channel metadata (subscribers, video count, etc.)
- Collecting video data (titles, descriptions, statistics, tags)
- Downloading and storing thumbnails
- Calculating performance metrics
- Managing API quota efficiently

## Quick Start

```bash
# Install dependencies
npm install

# Configure environment (copy .env.example to .env in project root)
# Required: YOUTUBE_API_KEY, Firebase credentials

# Validate API connections
npx tsx scripts/validate.ts

# Run the scraper
npm start

# Run tests
npm test
```

## Architecture

```
scraper/
├── package.json
├── tsconfig.json
├── vitest.config.ts
│
├── src/
│   ├── index.ts              # Entry point
│   ├── config.ts             # Environment configuration
│   │
│   ├── types/                # TypeScript interfaces
│   │   ├── index.ts          # Type exports
│   │   ├── channel.ts        # Channel interface
│   │   ├── video.ts          # Video & CalculatedMetrics
│   │   └── progress.ts       # ScrapeProgress & SessionStats
│   │
│   ├── youtube/              # YouTube API integration
│   │   ├── client.ts         # API client & quota tracking
│   │   ├── resolver.ts       # URL → Channel ID resolution
│   │   ├── channels.ts       # Channel data fetching
│   │   └── videos.ts         # Video data fetching
│   │
│   ├── firebase/             # Firebase integration
│   │   ├── client.ts         # Firebase Admin SDK setup
│   │   ├── firestore.ts      # Database operations
│   │   └── storage.ts        # Thumbnail storage
│   │
│   ├── scraper/              # Core scraping logic
│   │   ├── index.ts          # Main orchestration
│   │   ├── progress.ts       # Resume capability
│   │   └── thumbnail.ts      # Image processing
│   │
│   └── utils/                # Utilities
│       ├── duration.ts       # ISO 8601 parser
│       ├── helpers.ts        # Common utilities
│       └── logger.ts         # Console logging
│
├── scripts/
│   ├── validate.ts                  # Test API connections
│   ├── reset-progress.ts            # Clear progress data
│   ├── check-status.ts              # Show scrape progress summary
│   ├── delete-short-thumbnails.ts   # Remove thumbnails for Shorts from Storage
│   └── migrate-unresolved.ts        # Retry unresolved channel URLs
│
└── tests/
    ├── utils/
    │   └── duration.test.ts  # Duration parsing tests
    ├── youtube/
    │   └── resolver.test.ts  # URL resolution tests
    └── scraper/
        └── progress.test.ts  # Progress tracking tests
```

## Core Features

### 1. URL Resolution

The scraper supports multiple YouTube URL formats:

| Format | Example | API Cost | Method |
|--------|---------|----------|--------|
| Handle | `@VismaiFood` | 1 unit | `channels.list` with `forHandle` |
| Channel ID | `/channel/UCxxx` | 0 units | Direct use |
| Username | `/user/name` | 1 unit | `channels.list` with `forUsername` |
| Custom URL | `/c/name` | 1-101 units | Try handle, fallback to search |

```typescript
// src/youtube/resolver.ts
import { resolveChannelUrl } from './youtube/resolver';

const result = await resolveChannelUrl('https://www.youtube.com/@VismaiFood');
// { channelId: 'UCxxx...', quotaCost: 1, resolvedFrom: 'handle' }
```

### 2. Video Fetching Strategy

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Channel ID     │────▶│  Uploads Playlist │────▶│  Video IDs      │
│  UCxxx...       │     │  UUxxx... (UC→UU) │     │  (50 per page)  │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                          │
                                                          ▼
                                                 ┌─────────────────┐
                                                 │  videos.list    │
                                                 │  (50 per batch) │
                                                 └─────────────────┘
```

### 3. Quota Management

YouTube API has a **10,000 units/day** quota limit:

```typescript
// src/youtube/client.ts
import { addQuotaUsage, getQuotaRemaining, isQuotaLow } from './youtube/client';

// Track usage
addQuotaUsage(1);

// Check remaining
const remaining = getQuotaRemaining(); // e.g., 8500

// Stop when low
if (isQuotaLow()) {
  saveProgress();
  console.log('Quota low, run again tomorrow');
}
```

Configuration:
```typescript
// Default settings
API_DELAY_MS=100              // Delay between requests
QUOTA_WARNING_THRESHOLD=500    // Save and stop at this level
```

### 4. Progress Tracking

Progress is automatically saved to Firestore for resume capability:

```typescript
interface ScrapeProgress {
  channelId: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  phase: 'scraping' | 'thumbnails' | 'calculations';
  totalVideos: number;
  videosProcessed: number;
  lastProcessedVideoId: string | null;
  lastPlaylistPageToken: string | null;
  lastUpdateAt: Timestamp | null;       // Last incremental update timestamp
  lastUpdateNewVideos: number;           // Videos found in last update
  startedAt: Timestamp;
  lastProcessedAt: Timestamp;
}
```

On restart, the scraper:
1. Checks `scrape_progress/{channelId}` for existing progress
2. Resumes from `lastPlaylistPageToken` if interrupted
3. Skips already-processed videos

### 5. Calculated Metrics

For each video, these metrics are computed:

```typescript
interface CalculatedMetrics {
  engagementRate: number;      // (likes + comments) / views * 100
  likeRatio: number;           // likes / views * 100
  commentRatio: number;        // comments / views * 100
  viewsPerSubscriber: number;  // views / channel subscribers
  viewsPerDay: number;
  publishDayOfWeek: string;    // "Monday", "Tuesday", etc.
  publishHourIST: number;      // 0-23 in IST timezone
  tagCount: number;
}
```

### 6. Thumbnail Processing

Thumbnails are downloaded from YouTube and uploaded to Firebase Storage:

```typescript
// Storage structure
thumbnails/
├── {channelId}/
│   ├── {videoId1}.jpg
│   ├── {videoId2}.jpg
│   └── ...
└── channel_thumbnails/
    └── {channelId}.jpg
```

Quality setting: `mqdefault` (320x180) for storage efficiency.

## Data Output

### Channel Document (`channels/{channelId}`)

```typescript
{
  channelId: "UCBSwcE0p0PMwhvE6FVjgITw",
  channelTitle: "Vismai Food",
  channelDescription: "Telugu cooking channel...",
  customUrl: "@VismaiFood",
  subscriberCount: 4930000,
  videoCount: 2200,
  viewCount: 1250000000,
  thumbnailUrl: "https://yt3.ggpht.com/...",
  thumbnailStoragePath: "channel_thumbnails/UCxxx.jpg",
  category: "cooking",      // From channels.json
  priority: 1,              // From channels.json
  scrapedAt: Timestamp
}
```

### Video Document (`channels/{channelId}/videos/{videoId}`)

```typescript
{
  videoId: "dQw4w9WgXcQ",
  channelId: "UCBSwcE0p0PMwhvE6FVjgITw",
  title: "Veg Manchurian Recipe | వెజ్ మంచూరియా",
  description: "Full recipe...",
  publishedAt: Timestamp,
  duration: "PT15M33S",
  durationSeconds: 933,
  viewCount: 16000000,
  likeCount: 450000,
  commentCount: 12000,
  tags: ["veg manchurian", "telugu cooking", ...],
  thumbnailStoragePath: "thumbnails/UCxxx/videoId.jpg",
  isShort: false,
  calculated: {
    engagementRate: 2.89,
    viewsPerDay: 43836,
    publishDayOfWeek: "Saturday",
    publishHourIST: 18,
    // ... more metrics
  }
}
```

## Commands

### Run Scraper
```bash
npm start                          # Full initial scrape
npm start -- --update              # Incremental update (new videos only for completed channels)
npm start -- --refresh             # Refresh stats (views, likes, comments) for all existing videos
npm start -- --update --refresh    # Find new videos AND refresh all existing video stats
npm start -- --ignore-quota        # Ignore quota checks
```

### Validate Connections
```bash
npx tsx scripts/validate.ts
```

Tests:
- YouTube API key validity
- Firebase Firestore connection
- Firebase Storage access
- Channel URL resolution

### Check Scrape Status
```bash
npx tsx scripts/check-status.ts
```

Shows progress summary: completed, in-progress, failed, and pending channels.

### Reset Progress
```bash
npx tsx scripts/reset-progress.ts
```

Clears all progress documents to re-scrape from scratch.

### Delete Short Thumbnails
```bash
npx tsx scripts/delete-short-thumbnails.ts
```

Removes thumbnails for Shorts from Firebase Storage (saves storage space).

### Migrate Unresolved Channels
```bash
npx tsx scripts/migrate-unresolved.ts
```

Retries channel URLs that previously failed resolution.

### Run Tests
```bash
npm test
```

## Configuration

### Required Environment Variables

```bash
# YouTube API
YOUTUBE_API_KEY=your_api_key

# Firebase
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_CLIENT_EMAIL=firebase-adminsdk@your-project.iam.gserviceaccount.com
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
FIREBASE_STORAGE_BUCKET=your-project.appspot.com
```

### Optional Settings

```bash
API_DELAY_MS=100              # Delay between API calls (ms)
QUOTA_WARNING_THRESHOLD=500   # Save progress at this quota level
THUMBNAIL_QUALITY=mqdefault   # YouTube thumbnail quality
```

### Channel Configuration

Edit `config/channels.json`:

```json
{
  "channels": [
    {
      "url": "https://www.youtube.com/@VismaiFood",
      "category": "cooking",
      "priority": 1
    }
  ],
  "settings": {
    "maxVideosPerChannel": null,
    "includeShorts": true,
    "includePrivate": false,
    "skipShortThumbnails": true
  }
}
```

## Error Handling

### Retry Logic

```typescript
// Exponential backoff for transient errors
async function retry<T>(
  fn: () => Promise<T>,
  maxRetries: number = 3,
  baseDelayMs: number = 1000
): Promise<T>
```

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `quotaExceeded` | Daily limit reached | Wait until midnight Pacific |
| `channelNotFound` | Invalid URL/ID | Check URL format |
| `forbidden` | API key invalid | Verify YOUTUBE_API_KEY |
| `rateLimitExceeded` | Too many requests | Increase API_DELAY_MS |

### Progress Recovery

If the scraper crashes or is interrupted:
1. Progress is automatically saved to Firestore
2. Run `npm start` again to resume
3. Use `reset-progress.ts` to start fresh if needed

## Performance

### Estimated Processing Times

| Channels | Videos (avg 500 each) | Days (quota limited) |
|----------|----------------------|---------------------|
| 10 | 5,000 | 1 |
| 50 | 25,000 | 2-3 |
| 100 | 50,000 | 3-5 |

### Quota Usage per Channel

```
Per channel (500 videos):
  - URL resolution: 1 unit
  - Channel info: 1 unit
  - List videos: 10 pages × 1 = 10 units
  - Video details: 10 batches × 1 = 10 units
  - Total: ~22 units
```

## Testing

```bash
# Run all tests
npm test

# Run specific test file
npm test -- tests/utils/duration.test.ts

# Run with coverage
npm test -- --coverage
```

### Test Coverage

- `duration.test.ts`: ISO 8601 duration parsing (8 tests)
- `resolver.test.ts`: URL format resolution
- `progress.test.ts`: Progress tracking logic

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `googleapis` | ^131.0.0 | YouTube Data API client |
| `firebase-admin` | ^12.0.0 | Firebase Admin SDK |
| `axios` | ^1.6.7 | HTTP client for thumbnails |
| `dotenv` | ^16.4.1 | Environment configuration |
| `typescript` | ^5.3.3 | TypeScript compiler |
| `vitest` | ^1.2.2 | Test runner |
| `tsx` | ^4.7.0 | TypeScript execution |

## Troubleshooting

### "Quota exceeded" error
- **Cause**: Daily YouTube API quota (10,000 units) exhausted
- **Solution**: Wait until midnight Pacific Time, then run again

### "Channel not found" error
- **Cause**: Invalid URL format or deleted channel
- **Solution**: Verify the URL works in a browser

### Firebase connection errors
- **Cause**: Invalid credentials or network issues
- **Solution**:
  1. Verify `FIREBASE_PROJECT_ID` is correct
  2. Check `FIREBASE_PRIVATE_KEY` includes newlines
  3. Run `validate.ts` to test connection

### Progress not resuming
- **Cause**: Corrupted progress document
- **Solution**: Run `npx tsx scripts/reset-progress.ts` for that channel

## Next Steps

After scraping completes:
1. Verify data in Firebase Console
2. Check `scrape_progress` collection for any failures
3. Proceed to **Phase 2: Analyzer** for AI analysis

---

For more details, see the [Technical Documentation](../docs/TECHNICAL_DOCUMENTATION.md).
