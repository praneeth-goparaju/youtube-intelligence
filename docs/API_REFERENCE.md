# API Reference

Complete programmatic interface documentation for the YouTube Intelligence System.

## Table of Contents

1. [Scraper API (TypeScript)](#scraper-api-typescript)
2. [Analyzer API (Python)](#analyzer-api-python)
3. [Insights API (Python)](#insights-api-python)
4. [Recommender API (TypeScript)](#recommender-api-typescript)
5. [Firebase Data Structures](#firebase-data-structures)
6. [Shared Utilities](#shared-utilities)

---

## Scraper API (TypeScript)

### YouTube Client

#### `getYoutubeClient()`
Returns the initialized YouTube API client.

```typescript
import { getYoutubeClient } from './youtube/client';

const youtube = getYoutubeClient();
```

#### `addQuotaUsage(units: number)`
Track API quota usage.

```typescript
import { addQuotaUsage, getQuotaRemaining, isQuotaLow } from './youtube/client';

addQuotaUsage(1);
const remaining = getQuotaRemaining();  // Returns number
const low = isQuotaLow();  // Returns boolean
```

### URL Resolver

#### `resolveChannelUrl(url: string): Promise<ResolvedChannel>`
Resolves a YouTube URL to a channel ID.

**Parameters:**
- `url`: YouTube channel URL in any format

**Returns:**
```typescript
interface ResolvedChannel {
  channelId: string;
  quotaCost: number;
  resolvedFrom: 'handle' | 'channelId' | 'user' | 'customUrl';
}
```

**Example:**
```typescript
import { resolveChannelUrl } from './youtube/resolver';

const result = await resolveChannelUrl('https://www.youtube.com/@VismaiFood');
// { channelId: 'UCxxx...', quotaCost: 1, resolvedFrom: 'handle' }
```

**Supported URL Formats:**
| Format | Example | Cost |
|--------|---------|------|
| Handle | `@VismaiFood` | 1 |
| Channel ID | `/channel/UCxxx` | 0 |
| Username | `/user/name` | 1 |
| Custom URL | `/c/name` | 1-101 |

### Channel Operations

#### `getChannelDetails(channelId: string): Promise<Channel>`
Fetches channel metadata.

```typescript
import { getChannelDetails } from './youtube/channels';

const channel = await getChannelDetails('UCBSwcE0p0PMwhvE6FVjgITw');
```

**Returns:**
```typescript
interface Channel {
  channelId: string;
  channelTitle: string;
  channelDescription: string;
  customUrl: string;
  subscriberCount: number;
  videoCount: number;
  viewCount: number;
  thumbnailUrl: string;
  bannerUrl: string | null;
  country: string | null;
  publishedAt: Date;
}
```

### Video Operations

#### `getUploadsPlaylistId(channelId: string): string`
Converts channel ID to uploads playlist ID.

```typescript
import { getUploadsPlaylistId } from './youtube/videos';

const playlistId = getUploadsPlaylistId('UCBSwcE0p0PMwhvE6FVjgITw');
// Returns: 'UUBSwcE0p0PMwhvE6FVjgITw'
```

#### `getPlaylistVideos(playlistId: string, pageToken?: string): Promise<PlaylistResult>`
Fetches video IDs from a playlist.

```typescript
interface PlaylistResult {
  videoIds: string[];
  nextPageToken: string | null;
  totalResults: number;
}

const result = await getPlaylistVideos('UUxxx', null);
```

#### `getVideoDetailsBatch(videoIds: string[]): Promise<Video[]>`
Fetches detailed video information (max 50 per request).

```typescript
import { getVideoDetailsBatch } from './youtube/videos';

const videos = await getVideoDetailsBatch(['videoId1', 'videoId2', ...]);
```

### Firestore Operations

#### `saveChannel(channel: Channel): Promise<void>`
Saves channel data to Firestore.

```typescript
import { saveChannel } from './firebase/firestore';

await saveChannel(channelData);
```

#### `saveVideosBatch(channelId: string, videos: Video[]): Promise<void>`
Batch saves videos to Firestore.

```typescript
import { saveVideosBatch } from './firebase/firestore';

await saveVideosBatch('UCxxx', videosArray);
```

#### `getProgress(channelId: string): Promise<ScrapeProgress | null>`
Retrieves scraping progress for resume.

```typescript
import { getProgress, saveProgress } from './firebase/firestore';

const progress = await getProgress('UCxxx');
await saveProgress(progressData);
```

### Storage Operations

#### `downloadAndUploadThumbnail(videoId: string, channelId: string): Promise<string>`
Downloads thumbnail and uploads to Firebase Storage.

```typescript
import { downloadAndUploadThumbnail } from './scraper/thumbnail';

const storagePath = await downloadAndUploadThumbnail('videoId', 'channelId');
// Returns: 'thumbnails/channelId/videoId.jpg'
```

### Utilities

#### `parseDuration(isoDuration: string): number`
Parses ISO 8601 duration to seconds.

```typescript
import { parseDuration } from './utils/duration';

parseDuration('PT15M33S');  // Returns: 933
parseDuration('PT1H2M3S');  // Returns: 3723
```

#### `chunk<T>(array: T[], size: number): T[][]`
Splits array into chunks.

```typescript
import { chunk } from './utils/helpers';

chunk([1,2,3,4,5], 2);  // Returns: [[1,2], [3,4], [5]]
```

---

## Analyzer API (Python)

### Gemini Client

#### `analyze_image(prompt: str, image_data: bytes) -> Dict`
Analyzes an image using Gemini Vision.

```python
from src.gemini_client import analyze_image

with open('thumbnail.jpg', 'rb') as f:
    image_data = f.read()

result = analyze_image(THUMBNAIL_PROMPT, image_data)
```

#### `analyze_text(prompt: str, text: str) -> Dict`
Analyzes text using Gemini.

```python
from src.gemini_client import analyze_text

result = analyze_text(TITLE_PROMPT, "Video Title | వీడియో టైటిల్")
```

### Analyzers

#### `ThumbnailAnalyzer`

```python
from src.analyzers.thumbnail import ThumbnailAnalyzer

analyzer = ThumbnailAnalyzer()
result = analyzer.analyze(video_data)
```

**Parameters:**
- `video_data`: Dict with `thumbnailStoragePath`

**Returns:** Dict with ~109 attributes (composition, humanPresence, textElements, colors, food, graphics, branding, psychology, technicalQuality, scores)

#### `TitleDescriptionAnalyzer`

```python
from src.analyzers.title_description import TitleDescriptionAnalyzer

analyzer = TitleDescriptionAnalyzer()
result = analyzer.analyze(video_data)
```

**Parameters:**
- `video_data`: Dict with `title` and `description`

**Returns:** Dict with ~140 attributes covering title analysis (structure, language, hooks, keywords, contentSignals, teluguAnalysis) and lean description analysis (structure, timestamps, recipeContent, hashtags, callToActions, seo)

### Batch Processor

#### `BatchProcessor`

```python
from src.processors.batch import BatchProcessor

processor = BatchProcessor(analysis_type='thumbnail')

# Process single channel
processor.process_channel('UCxxx', limit=100)

# Process all channels
processor.process_all_channels(limit=50)
```

**Parameters:**
- `analysis_type`: `'thumbnail'` or `'title_description'`

### Firebase Client

#### `get_all_channels() -> List[Dict]`
Fetches all channels from Firestore.

```python
from src.firebase_client import get_all_channels

channels = get_all_channels()
```

#### `get_channel_videos(channel_id: str, limit: int = None) -> List[Dict]`
Fetches videos for a channel.

```python
from src.firebase_client import get_channel_videos

videos = get_channel_videos('UCxxx', limit=100)
```

#### `download_thumbnail(storage_path: str) -> bytes`
Downloads thumbnail from Firebase Storage.

```python
from src.firebase_client import download_thumbnail

image_data = download_thumbnail('thumbnails/UCxxx/videoId.jpg')
```

#### `save_analysis(channel_id, video_id, analysis_type, data) -> None`
Saves analysis results.

```python
from src.firebase_client import save_analysis

save_analysis('UCxxx', 'videoId', 'thumbnail', analysis_result)
```

#### `has_analysis(channel_id, video_id, analysis_type) -> bool`
Checks if analysis exists.

```python
from src.firebase_client import has_analysis

exists = has_analysis('UCxxx', 'videoId', 'thumbnail')
```

---

## Insights API (Python)

### Content Type Profiler

#### `ContentTypeProfiler`

```python
from src.profiler import ContentTypeProfiler

profiler = ContentTypeProfiler(videos_with_analyses)
profiles = profiler.generate_all_profiles()
```

Generates per-content-type profiles comparing all videos vs top 10% (by `viewsPerSubscriber`).

**Returns:** Dict of content type profiles, each containing:
```python
{
    "recipe": {
        "contentType": "recipe",
        "videoCount": 12500,
        "topPercentileThreshold": 3.2,
        "thumbnail": {
            "composition.layoutType": {
                "type": "categorical",
                "all": {"split-screen": 35, "single-focus": 40, ...},
                "top10": {"split-screen": 55, "single-focus": 30, ...}
            },
            "humanPresence.facePresent": {
                "type": "boolean",
                "all": {"true_pct": 65, "false_pct": 35},
                "top10": {"true_pct": 85, "false_pct": 15}
            },
            # ... more features
        },
        "title": {
            # ... title features
        }
    }
}
```

Feature types are auto-detected:
- **boolean**: `{true_pct, false_pct}`
- **numeric**: `{mean, median, p25, p75}`
- **categorical**: `{value: percentage, ...}`
- **list**: `{item: frequency, ...}`

### Gap Analyzer

#### `GapAnalyzer`

```python
from src.gaps import GapAnalyzer

analyzer = GapAnalyzer(videos_with_analyses)
gaps = analyzer.analyze()
```

**Returns:**
```python
{
    "contentTypeBreakdown": {
        "recipe": {"count": 12500, "avgVPS": 1.8, "topVPS": 5.2},
        "vlog": {"count": 8000, "avgVPS": 1.2, "topVPS": 3.8}
    },
    "keywordOpportunities": [
        {"keyword": "air fryer", "count": 15, "avgVPS": 4.5, "opportunity": "high"}
    ]
}
```

---

## Recommender API (TypeScript)

The recommendation engine is implemented in TypeScript and can be used via CLI or as a Firebase Function API.

### CLI Usage

```bash
cd functions

# Basic usage
npm run recommend -- --topic "Hyderabadi Biryani" --type recipe

# With all options
npm run recommend -- \
  --topic "Hyderabadi Biryani" \
  --type recipe \
  --angle "Restaurant secret recipe" \
  --audience "Telugu home cooks" \
  --output recommendation.json
```

### HTTP API

```bash
# POST request
curl -X POST https://us-central1-PROJECT.cloudfunctions.net/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Hyderabadi Biryani",
    "type": "recipe",
    "angle": "Restaurant secret recipe",
    "audience": "Telugu home cooks"
  }'
```

### Firebase SDK (Callable)

```typescript
import { getFunctions, httpsCallable } from 'firebase/functions';

const functions = getFunctions();
const getRecommendation = httpsCallable(functions, 'getRecommendation');

const result = await getRecommendation({
  topic: 'Hyderabadi Biryani',
  type: 'recipe',
  angle: 'Restaurant secret recipe',
  audience: 'Telugu home cooks'
});
```

### Request Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `topic` | string | Yes | - | Video topic |
| `type` | string | No | `'recipe'` | `'recipe'`, `'vlog'`, `'tutorial'`, `'review'`, `'challenge'` |
| `angle` | string | No | `undefined` | Unique positioning |
| `audience` | string | No | `'Telugu audience'` | Target audience |

### Response Structure

```typescript
{
  titles: {
    primary: {
      english: string,
      telugu: string,
      combined: string,
      predictedCTR: 'below-average' | 'average' | 'above-average' | 'high',
      reasoning: string
    },
    alternatives: [...]
  },
  thumbnail: {
    layout: {...},
    elements: {...},
    colors: {...}
  },
  tags: {
    primary: string[],
    secondary: string[],
    telugu: string[],
    longtail: string[],
    fullTagString: string,
    characterCount: number,
    utilizationPercent: number
  },
  posting: {
    bestDay: string,
    bestTime: string,
    alternativeTimes: string[],
    reasoning: string
  },
  prediction: {
    expectedViewRange: { low: number, medium: number, high: number },
    confidence: 'low' | 'medium' | 'high',
    positiveFactors: string[],
    riskFactors: string[]
  },
  metadata: {
    generatedAt: string,
    modelUsed: string,
    insightsVersion: string | null,
    fallbackUsed: boolean
  }
}
```

### RecommendationEngine Class

```typescript
import { RecommendationEngine } from './engine';

const engine = new RecommendationEngine();

const recommendation = await engine.generateRecommendation({
  topic: 'Biryani',
  type: 'recipe',
  angle: 'Secret recipe',
  audience: 'Telugu home cooks'
});
```

### Templates (Fallback)

When Gemini AI is unavailable or fails, the engine falls back to template-based generation:

```typescript
import { TITLE_TEMPLATES, THUMBNAIL_SPECS, POWER_WORDS } from './templates';

// Title templates by content type
const recipeTemplates = TITLE_TEMPLATES['recipe'];
// ['{dish} Recipe | {dish_telugu} | {modifier}', ...]

// Thumbnail specifications
const recipeSpec = THUMBNAIL_SPECS['recipe'];
// { layout: {...}, elements: {...}, colors: {...} }

// Power words for titles
const teluguWords = POWER_WORDS.telugu;
// ['రహస్యం', 'పర్ఫెక్ట్', 'అసలైన', ...]
```

---

## Firebase Data Structures

### Collections

#### `channels/{channelId}`

```typescript
{
  channelId: string,
  channelTitle: string,
  channelDescription: string,
  customUrl: string,
  subscriberCount: number,
  videoCount: number,
  viewCount: number,
  thumbnailUrl: string,
  thumbnailStoragePath: string,
  bannerUrl: string | null,
  country: string | null,
  publishedAt: Timestamp,
  category: string,
  priority: number,
  sourceUrl: string,
  scrapedAt: Timestamp,
  lastUpdatedAt: Timestamp
}
```

#### `channels/{channelId}/videos/{videoId}`

```typescript
{
  videoId: string,
  channelId: string,
  title: string,
  description: string,
  publishedAt: Timestamp,
  thumbnails: {
    default: string,
    medium: string,
    high: string,
    standard?: string,
    maxres?: string
  },
  thumbnailStoragePath: string,
  duration: string,           // ISO 8601
  durationSeconds: number,
  viewCount: number,
  likeCount: number,
  commentCount: number,
  tags: string[],
  categoryId: string,
  categoryName: string,
  isShort: boolean,
  videoUrl: string,
  scrapedAt: Timestamp,
  calculated: {
    engagementRate: number,
    likeRatio: number,
    commentRatio: number,
    viewsPerSubscriber: number,
    daysSincePublish: number,
    viewsPerDay: number,
    publishDayOfWeek: string,
    publishHourIST: number,
    titleLength: number,
    descriptionLength: number,
    tagCount: number,
    hasNumberInTitle: boolean,
    hasEmojiInTitle: boolean,
    hasTeluguInTitle: boolean,
    hasEnglishInTitle: boolean
  }
}
```

#### `channels/{channelId}/videos/{videoId}/analysis/{type}`

Types: `thumbnail`, `title_description`

Legacy types (`title`, `description`, `tags`, `content_structure`) may exist from previous runs but are no longer generated.

See [Technical Documentation](TECHNICAL_DOCUMENTATION.md) for full schemas.

#### `scrape_progress/{channelId}`

```typescript
{
  channelId: string,
  channelTitle: string,
  sourceUrl: string,
  status: 'pending' | 'in_progress' | 'completed' | 'failed',
  phase: 'scraping' | 'thumbnails' | 'calculations',
  totalVideos: number,
  videosProcessed: number,
  thumbnailsDownloaded: number,
  lastProcessedVideoId: string | null,
  lastPlaylistPageToken: string | null,
  startedAt: Timestamp,
  lastProcessedAt: Timestamp,
  completedAt: Timestamp | null,
  errorMessage: string | null,
  retryCount: number
}
```

#### `insights/{contentType}` (e.g., `insights/recipe`)

Per-content-type profiles with feature comparisons (all vs top 10%).

#### `insights/contentGaps`

Content gap and keyword opportunity analysis.

#### `insights/summary`

Overview of all content types and video counts.

See [Technical Documentation](TECHNICAL_DOCUMENTATION.md) for full schemas.

### Storage Structure

```
{bucket}/
├── channel_thumbnails/
│   └── {channelId}.jpg
└── thumbnails/
    └── {channelId}/
        └── {videoId}.jpg
```

---

## Shared Utilities

### Constants

```python
# shared/constants.py

COLLECTION_CHANNELS = 'channels'
COLLECTION_VIDEOS = 'videos'
COLLECTION_ANALYSIS = 'analysis'
COLLECTION_INSIGHTS = 'insights'
COLLECTION_SCRAPE_PROGRESS = 'scrape_progress'
COLLECTION_ANALYSIS_PROGRESS = 'analysis_progress'

ANALYSIS_TYPE_THUMBNAIL = 'thumbnail'
ANALYSIS_TYPE_TITLE_DESCRIPTION = 'title_description'
ANALYSIS_TYPES = [ANALYSIS_TYPE_THUMBNAIL, ANALYSIS_TYPE_TITLE_DESCRIPTION]

INSIGHT_TYPE_CONTENT_GAPS = 'contentGaps'
INSIGHT_TYPE_SUMMARY = 'summary'

GEMINI_MODEL = 'gemini-2.5-flash'
```

### Firebase Utilities

```python
# shared/firebase_utils.py

def initialize_firebase_app(config, options=None):
    """Initialize Firebase Admin SDK."""

def get_firestore_client():
    """Get Firestore client instance."""

def fetch_document(collection, doc_id):
    """Fetch a single document."""

def fetch_collection(collection, limit=None):
    """Fetch all documents in a collection."""

def save_document(collection, doc_id, data, merge=True):
    """Save/update a document."""
```

### Config Utilities

```python
# shared/config.py

def load_env_file(module_path):
    """Load .env from project root."""

def get_env(name, required=True, default=None):
    """Get environment variable."""

class BaseFirebaseConfig:
    """Base config with Firebase credentials."""

class BaseGeminiConfig(BaseFirebaseConfig):
    """Extended config with Gemini API key."""
```

---

## Error Codes

### Scraper Errors

| Code | Message | Solution |
|------|---------|----------|
| `QUOTA_EXCEEDED` | Daily API quota exhausted | Wait until midnight Pacific |
| `CHANNEL_NOT_FOUND` | Channel does not exist | Verify URL |
| `INVALID_API_KEY` | YouTube API key invalid | Check YOUTUBE_API_KEY |
| `FIREBASE_ERROR` | Firebase connection failed | Check credentials |

### Analyzer Errors

| Code | Message | Solution |
|------|---------|----------|
| `RATE_LIMIT` | Gemini rate limit exceeded | Increase REQUEST_DELAY |
| `INVALID_JSON` | Gemini returned invalid JSON | Automatic retry |
| `THUMBNAIL_NOT_FOUND` | Thumbnail missing in storage | Run scraper first |

### Common HTTP Status Codes

| Code | Meaning |
|------|---------|
| 403 | Permission denied / Invalid API key |
| 404 | Resource not found |
| 429 | Rate limit exceeded |
| 500 | Internal server error |

---

## Rate Limits

### YouTube Data API
- **Daily quota**: 10,000 units
- **Recommended delay**: 100ms between requests

### Gemini API
- **Free tier**: 60 requests/minute
- **Recommended delay**: 500ms-1000ms between requests

### Firebase
- **Firestore writes**: 10,000/second
- **Storage uploads**: No hard limit, but throttle for reliability

---

For implementation details, see [Technical Documentation](TECHNICAL_DOCUMENTATION.md).
