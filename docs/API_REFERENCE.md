# API Reference

Complete programmatic interface documentation for the YouTube Intelligence System.

## Table of Contents

1. [Scraper API (TypeScript)](#scraper-api-typescript)
2. [Analyzer API (Python)](#analyzer-api-python)
3. [Insights API (Python)](#insights-api-python)
4. [Recommender API (Python)](#recommender-api-python)
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

**Returns:** Dict with 50+ attributes (see Technical Documentation)

#### `TitleAnalyzer`

```python
from src.analyzers.title import TitleAnalyzer

analyzer = TitleAnalyzer()
result = analyzer.analyze(video_data)
```

**Parameters:**
- `video_data`: Dict with `title`

#### `DescriptionAnalyzer`

```python
from src.analyzers.description import DescriptionAnalyzer

analyzer = DescriptionAnalyzer()
result = analyzer.analyze(video_data)
```

#### `TagsAnalyzer`

```python
from src.analyzers.tags import TagsAnalyzer

analyzer = TagsAnalyzer()
result = analyzer.analyze(video_data)
```

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
- `analysis_type`: `'thumbnail'`, `'title'`, `'description'`, or `'tags'`

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

### Correlation Analyzer

#### `CorrelationAnalyzer`

```python
from src.correlations import CorrelationAnalyzer

analyzer = CorrelationAnalyzer(videos_with_analysis)
correlations = analyzer.find_top_correlations(target='view_count')
```

**Returns:**
```python
[
    {
        'feature': 'psychology_curiosityGap',
        'correlation': 0.42,
        'p_value': 0.001,
        'direction': 'positive'
    },
    ...
]
```

### Pattern Extractor

#### `PatternExtractor`

```python
from src.patterns import PatternExtractor

extractor = PatternExtractor(videos_with_analysis)

# Extract thumbnail patterns
thumbnail_patterns = extractor.extract_thumbnail_patterns()

# Extract title patterns
title_patterns = extractor.extract_title_patterns()

# Extract timing patterns
timing_patterns = extractor.extract_timing_patterns()
```

**Thumbnail/Title Pattern Return:**
```python
[
    {
        'element': 'surprised-expression',
        'top_rate': 0.65,
        'all_rate': 0.25,
        'lift': 2.6
    },
    ...
]
```

**Timing Pattern Return:**
```python
{
    'byDayOfWeek': [
        {'day': 'Saturday', 'avgViews': 125000, 'multiplier': 1.4}
    ],
    'byHourIST': [
        {'hour': 18, 'avgViews': 130000, 'multiplier': 1.46}
    ],
    'optimal': {
        'day': 'Saturday',
        'hourIST': 18,
        'multiplier': 1.6
    }
}
```

### Gap Analyzer

#### `GapAnalyzer`

```python
from src.gaps import GapAnalyzer

analyzer = GapAnalyzer(videos_with_analysis)

# Find content gaps
gaps = analyzer.find_content_gaps()

# Analyze keyword gaps
keyword_gaps = analyzer.analyze_keyword_gaps()
```

**Returns:**
```python
[
    {
        'topic': 'cooking/indo-chinese',
        'avgViews': 85000,
        'videoCount': 45,
        'opportunityScore': 1847
    },
    ...
]
```

### Report Generator

#### `ReportGenerator`

```python
from src.reports import ReportGenerator

generator = ReportGenerator()

# Save to Firestore and local file
generator.save_thumbnail_insights(patterns, correlations)
generator.save_title_insights(patterns, power_words)
generator.save_timing_insights(timing_data)
generator.save_content_gaps(gaps)
```

---

## Recommender API (Python)

### Recommendation Engine

#### `RecommendationEngine`

```python
from src.engine import RecommendationEngine

engine = RecommendationEngine()

recommendation = engine.generate_recommendation(
    topic="Hyderabadi Biryani",
    content_type="recipe",
    unique_angle="Restaurant secret recipe",
    target_audience="Telugu home cooks"
)
```

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `topic` | str | Yes | - | Video topic |
| `content_type` | str | No | `'recipe'` | `'recipe'`, `'vlog'`, `'tutorial'`, `'review'`, `'challenge'` |
| `unique_angle` | str | No | `None` | Unique positioning |
| `target_audience` | str | No | `'telugu-audience'` | Target audience |

**Returns:**
```python
{
    'titles': {
        'primary': {
            'english': str,
            'telugu': str,
            'combined': str,
            'predictedCTR': str,
            'reasoning': str
        },
        'alternatives': [...]
    },
    'thumbnail': {
        'layout': {...},
        'elements': {...},
        'colors': {...}
    },
    'tags': {
        'primary': [...],
        'secondary': [...],
        'telugu': [...],
        'longtail': [...]
    },
    'posting': {
        'bestDay': str,
        'bestTime': str,
        'alternativeTimes': [...]
    },
    'prediction': {
        'expectedViewRange': {'low': int, 'medium': int, 'high': int},
        'positiveFactors': [...],
        'riskFactors': [...]
    }
}
```

#### `_generate_from_templates(topic, content_type) -> Dict`
Fallback method for template-based generation.

```python
# Called automatically when AI fails
result = engine._generate_from_templates("Biryani", "recipe")
```

### Templates

#### Title Templates

```python
from src.templates import TITLE_TEMPLATES

templates = TITLE_TEMPLATES['recipe']
# ['{dish} Recipe | {dish_telugu} | {modifier}', ...]
```

#### Thumbnail Specs

```python
from src.templates import THUMBNAIL_SPECS

spec = THUMBNAIL_SPECS['recipe']
# {'layout': 'split-composition', 'face': {...}, 'food': {...}}
```

#### Power Words

```python
from src.templates import POWER_WORDS

telugu_words = POWER_WORDS['telugu']
# ['రహస్యం', 'పర్ఫెక్ట్', 'అసలైన', ...]
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

Types: `thumbnail`, `title`, `description`, `tags`

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

#### `insights/{type}`

Types: `thumbnails`, `titles`, `timing`, `contentGaps`

See output schemas in respective module documentation.

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

ANALYSIS_TYPE_THUMBNAIL = 'thumbnail'
ANALYSIS_TYPE_TITLE = 'title'
ANALYSIS_TYPE_DESCRIPTION = 'description'
ANALYSIS_TYPE_TAGS = 'tags'

GEMINI_MODEL = 'gemini-2.0-flash'
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
