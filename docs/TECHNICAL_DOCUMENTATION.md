# YouTube Intelligence System - Technical Documentation

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Phase 1: YouTube Scraper](#phase-1-youtube-scraper)
4. [Phase 2: AI Analyzer](#phase-2-ai-analyzer)
5. [Phase 3: Pattern Discovery](#phase-3-pattern-discovery)
6. [Phase 4: Recommendation Engine](#phase-4-recommendation-engine)
7. [Data Schemas](#data-schemas)
8. [API Integration Details](#api-integration-details)
9. [Error Handling & Resilience](#error-handling--resilience)
10. [Performance Considerations](#performance-considerations)

---

## System Overview

The YouTube Intelligence System is a four-phase analytics platform designed to:

1. **Collect** video data from 100+ Telugu YouTube channels
2. **Analyze** thumbnails and title+description using Gemini AI (2 calls per video)
3. **Profile** content types and compare top 10% performers to discover what works
4. **Generate** data-driven recommendations for new video creation

### Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Scraper | TypeScript + Node.js | YouTube API integration |
| Database | Firebase Firestore | Structured data storage |
| File Storage | Firebase Storage | Thumbnail images |
| AI Analysis | Google Gemini 2.5 Flash | Vision + text analysis (2 calls/video) |
| Analytics | Python + Pandas | Per-content-type profiling |
| Recommendations | TypeScript + Gemini | AI-powered suggestions (CLI + API) |

### Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATA FLOW                                       │
└─────────────────────────────────────────────────────────────────────────────┘

  channels.json
       │
       ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   PHASE 1    │    │   PHASE 2    │    │   PHASE 3    │    │   PHASE 4    │
│   Scraper    │───▶│   Analyzer   │───▶│   Insights   │───▶│ Recommender  │
│  (TypeScript)│    │   (Python)   │    │   (Python)   │    │ (TypeScript) │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
       │                   │                   │                   │
       ▼                   ▼                   ▼                   ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         FIREBASE FIRESTORE                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │  channels/  │  │  /analysis/ │  │  insights/  │  │ (read-only) │     │
│  │  /videos/   │  │  subcollect │  │  collection │  │             │     │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘     │
└──────────────────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────┐
│ FIREBASE STORAGE │
│   thumbnails/    │
└──────────────────┘
```

---

## Architecture

### Directory Structure

```
youtube_channel_analysis/
│
├── .env.example              # Environment variables template
├── .env                      # Actual credentials (git-ignored)
├── .gitignore
├── CLAUDE.md                 # Project context for AI assistants
│
├── config/
│   └── channels.json         # Input: YouTube channel URLs
│
├── scraper/                  # PHASE 1: TypeScript Scraper
│   ├── package.json
│   ├── tsconfig.json
│   ├── vitest.config.ts
│   ├── src/
│   │   ├── index.ts          # Entry point
│   │   ├── config.ts         # Environment configuration
│   │   ├── types/            # TypeScript interfaces
│   │   │   ├── index.ts
│   │   │   ├── channel.ts
│   │   │   ├── video.ts
│   │   │   └── progress.ts
│   │   ├── youtube/          # YouTube API integration
│   │   │   ├── client.ts     # API client & quota tracking
│   │   │   ├── resolver.ts   # URL → Channel ID resolution
│   │   │   ├── channels.ts   # Channel data fetching
│   │   │   └── videos.ts     # Video data fetching
│   │   ├── firebase/         # Firebase integration
│   │   │   ├── client.ts     # Firebase Admin SDK setup
│   │   │   ├── firestore.ts  # Database operations
│   │   │   └── storage.ts    # Thumbnail storage
│   │   ├── scraper/          # Core scraping logic
│   │   │   ├── index.ts      # Main scraping orchestration
│   │   │   ├── progress.ts   # Resume capability
│   │   │   └── thumbnail.ts  # Image processing
│   │   └── utils/            # Utilities
│   │       ├── duration.ts   # ISO 8601 parser
│   │       ├── helpers.ts    # Common utilities
│   │       └── logger.ts     # Console logging
│   ├── scripts/
│   │   ├── validate.ts       # Connection testing
│   │   └── reset-progress.ts # Clear progress data
│   └── tests/                # Vitest tests
│
├── analyzer/                 # PHASE 2: Python AI Analyzer
│   ├── requirements.txt
│   ├── src/
│   │   ├── __init__.py
│   │   ├── main.py           # Entry point
│   │   ├── config.py         # Configuration
│   │   ├── firebase_client.py
│   │   ├── gemini_client.py  # Gemini API wrapper
│   │   ├── analyzers/        # Analysis modules
│   │   │   ├── __init__.py
│   │   │   ├── thumbnail.py  # Vision analysis
│   │   │   └── title_description.py  # Combined title+description text analysis
│   │   ├── processors/       # Batch processing
│   │   │   ├── __init__.py
│   │   │   ├── batch.py
│   │   │   └── progress.py
│   │   └── prompts/          # AI prompts
│   │       ├── __init__.py
│   │       ├── thumbnail_prompt.py
│   │       └── title_description_prompt.py
│   └── tests/
│
├── insights/                 # PHASE 3: Per-Content-Type Profiling
│   ├── requirements.txt
│   └── src/
│       ├── __init__.py
│       ├── main.py           # Entry point (--type profiles|gaps|all)
│       ├── config.py
│       ├── firebase_client.py
│       ├── profiler.py       # Feature profiling (all vs top 10%)
│       └── gaps.py           # Content gap analysis
│
└── functions/                # PHASE 4: Recommendation Engine (TypeScript)
    ├── package.json
    ├── tsconfig.json
    ├── src/
    │   ├── index.ts          # Firebase Functions entry point
    │   ├── cli.ts            # CLI interface
    │   ├── engine.ts         # Recommendation logic
    │   ├── firebase.ts       # Firebase client
    │   ├── gemini.ts         # Gemini API client
    │   ├── templates.ts      # Title/thumbnail templates
    │   └── types.ts          # TypeScript interfaces
    └── README.md
```

---

## Phase 1: YouTube Scraper

### Overview

The scraper collects video data from YouTube channels using the YouTube Data API v3. It handles:

- Channel URL resolution (multiple formats)
- Paginated video listing
- Batch video details fetching
- Thumbnail downloading and storage
- Calculated metrics generation
- Progress tracking for resume capability

### URL Resolution

The system supports multiple YouTube URL formats:

| Format | Example | Quota Cost | Resolution Method |
|--------|---------|------------|-------------------|
| Handle | `@VismaiFood` | 1 unit | `channels.list` with `forHandle` |
| Channel ID | `/channel/UCxxx` | 0 units | Direct use |
| Username | `/user/name` | 1 unit | `channels.list` with `forUsername` |
| Custom URL | `/c/name` | 1-101 units | Try handle first, fallback to search |

```typescript
// src/youtube/resolver.ts

const URL_PATTERNS: UrlPattern[] = [
  { regex: /@([^\/\?]+)/, type: 'handle' },
  { regex: /\/channel\/(UC[a-zA-Z0-9_-]{22})/, type: 'channelId' },
  { regex: /\/c\/([^\/\?]+)/, type: 'customUrl' },
  { regex: /\/user\/([^\/\?]+)/, type: 'user' },
];

export async function resolveChannelUrl(url: string): Promise<ResolvedChannel> {
  const parsed = parseChannelUrl(url);
  // ... resolution logic based on URL type
}
```

### Video Fetching Strategy

1. **Get Uploads Playlist ID**: Convert channel ID (UC prefix → UU)
2. **Paginate Through Playlist**: Fetch video IDs in batches of 50
3. **Batch Video Details**: Request full video details (snippet, statistics, contentDetails)
4. **Calculate Metrics**: Derive performance metrics from raw data

```typescript
// Convert channel ID to uploads playlist ID
export function getUploadsPlaylistId(channelId: string): string {
  return 'UU' + channelId.substring(2);  // UCxxx → UUxxx
}
```

### Quota Management

YouTube API has a daily quota of 10,000 units:

| Operation | Cost | Notes |
|-----------|------|-------|
| `channels.list` | 1 | Channel details |
| `playlistItems.list` | 1 | 50 videos per page |
| `videos.list` | 1 | 50 videos per batch |
| `search.list` | 100 | Avoid if possible |

The scraper:
- Tracks quota usage in memory
- Saves progress when quota reaches warning threshold (500 remaining)
- Displays remaining quota after each channel

```typescript
// src/youtube/client.ts

let quotaUsed = 0;

export function addQuotaUsage(units: number): void {
  quotaUsed += units;
}

export function isQuotaLow(): boolean {
  return getQuotaRemaining() <= config.scraper.quotaWarningThreshold;
}
```

### Progress Tracking

Progress is stored in Firestore `scrape_progress/{channelId}`:

```typescript
interface ScrapeProgress {
  channelId: string;
  channelTitle: string;
  sourceUrl: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  phase: 'scraping' | 'thumbnails' | 'calculations';
  totalVideos: number;
  videosProcessed: number;
  thumbnailsDownloaded: number;
  lastProcessedVideoId: string | null;
  lastPlaylistPageToken: string | null;
  startedAt: Timestamp;
  lastProcessedAt: Timestamp;
  completedAt: Timestamp | null;
  errorMessage: string | null;
  retryCount: number;
}
```

### Calculated Metrics

For each video, the scraper calculates:

```typescript
interface CalculatedMetrics {
  engagementRate: number;      // (likes + comments) / views * 100
  likeRatio: number;           // likes / views * 100
  commentRatio: number;        // comments / views * 100
  viewsPerSubscriber: number;  // views / channel subscribers
  daysSincePublish: number;    // days since video published
  viewsPerDay: number;         // views / days since publish
  publishDayOfWeek: string;    // "Monday", "Tuesday", etc.
  publishHourIST: number;      // Hour in IST timezone (0-23)
  titleLength: number;
  descriptionLength: number;
  tagCount: number;
  hasNumberInTitle: boolean;
  hasEmojiInTitle: boolean;
  hasTeluguInTitle: boolean;   // Telugu script detection
  hasEnglishInTitle: boolean;
}
```

### Thumbnail Processing

Thumbnails are downloaded and uploaded to Firebase Storage:

```typescript
// src/scraper/thumbnail.ts

export async function downloadAndUploadThumbnail(
  videoId: string,
  channelId: string
): Promise<string> {
  const thumbnailUrl = `https://img.youtube.com/vi/${videoId}/mqdefault.jpg`;
  const storagePath = `thumbnails/${channelId}/${videoId}.jpg`;

  const buffer = await downloadImage(thumbnailUrl);
  await uploadBuffer(buffer, storagePath);

  return storagePath;
}
```

Storage structure:
```
{bucket}/
├── channel_thumbnails/
│   └── {channelId}.jpg
└── thumbnails/
    └── {channelId}/
        ├── {videoId1}.jpg
        ├── {videoId2}.jpg
        └── ...
```

---

## Phase 2: AI Analyzer

### Overview

The analyzer processes scraped data using Google Gemini 2.5 Flash with **2 API calls per video**:

- **Thumbnail Analysis** (vision call): Composition, colors, human presence, text, food, graphics, psychology (~109 fields)
- **Title + Description Analysis** (combined text call): Single call analyzing both together
  - Title: Structure, language mix, hooks, keywords, content signals, Telugu-specific patterns (~120 fields)
  - Description (lean): Structure, timestamps, recipe content, hashtags, CTAs, SEO (~20 fields)
  - Description context improves niche detection (e.g., ingredient list confirms isRecipe)

### Gemini Client

```python
# src/gemini_client.py

import google.generativeai as genai

genai.configure(api_key=config.GOOGLE_API_KEY)

_model = genai.GenerativeModel(
    model_name='gemini-2.5-flash',
    generation_config={
        'temperature': 0.1,      # Low for consistent structured output
        'top_p': 0.95,
        'max_output_tokens': 8192,
    }
)

def analyze_image(prompt: str, image_data: bytes) -> Dict[str, Any]:
    """Analyze image with Gemini Vision."""
    image = Image.open(io.BytesIO(image_data))
    response = _model.generate_content([prompt, image])
    return json.loads(response.text)

def analyze_text(prompt: str, text: str) -> Dict[str, Any]:
    """Analyze text with Gemini."""
    response = _model.generate_content(f"{prompt}\n\nText:\n{text}")
    return json.loads(response.text)
```

### Thumbnail Analysis Schema

The thumbnail analyzer extracts 50+ attributes:

```python
{
    "composition": {
        "layoutType": "split-screen|single-focus|collage|text-heavy|minimal",
        "gridStructure": "rule-of-thirds|centered|asymmetric",
        "visualBalance": "balanced|left-heavy|right-heavy",
        "complexity": "simple|medium|complex|cluttered",
        "focalPoint": "description",
        "depthOfField": "shallow|deep|flat"
    },
    "humanPresence": {
        "facePresent": True/False,
        "faceCount": int,
        "facePosition": "right-third|center|left-third",
        "expression": "surprised|happy|curious|neutral",
        "expressionIntensity": "subtle|moderate|high|extreme",
        "eyeContact": True/False,
        "handGesture": "pointing|thumbs-up|holding-item|none"
    },
    "textElements": {
        "hasText": True/False,
        "languages": ["english", "telugu"],
        "hasTeluguScript": True/False,
        "primaryText": {
            "content": "text",
            "position": "top-left|center|bottom",
            "color": "#HEX",
            "hasOutline": True/False
        },
        "hasNumbers": True/False,
        "numberType": "view-count|price|quantity"
    },
    "colors": {
        "dominantColors": [
            {"hex": "#FF6B35", "name": "orange", "percentage": 35}
        ],
        "palette": "warm|cool|neutral",
        "contrast": "low|medium|high",
        "saturation": "desaturated|medium|vivid"
    },
    "food": {  # For cooking channels
        "foodPresent": True/False,
        "mainDish": "dish name",
        "presentation": "close-up|plated|cooking-process",
        "steam": True/False,
        "appetiteAppeal": 1-10
    },
    "psychology": {
        "curiosityGap": True/False,
        "socialProof": True/False,
        "urgency": True/False,
        "primaryEmotion": "curiosity|excitement|appetite"
    },
    "scores": {
        "clickability": 1-10,
        "clarity": 1-10,
        "professionalism": 1-10,
        "predictedCTR": "below-average|average|above-average"
    }
}
```

### Title Analysis Schema

```python
{
    "structure": {
        "pattern": "dish-name | translation | modifier",
        "segments": [
            {"text": "Biryani Recipe", "type": "dish-name", "language": "english"},
            {"text": "బిర్యానీ", "type": "translation", "language": "telugu"}
        ],
        "characterCount": 67,
        "teluguCharacterCount": 12
    },
    "language": {
        "languages": ["english", "telugu"],
        "primaryLanguage": "english",
        "hasTeluguScript": True,
        "teluguRatio": 0.18,
        "codeSwitch": True,
        "codeSwitchStyle": "translation|mixed|parallel"
    },
    "hooks": {
        "hasPowerWord": True,
        "powerWords": ["SECRET", "Restaurant Style"],
        "triggers": {
            "curiosityGap": True/False,
            "socialProof": True/False,
            "urgency": True/False
        },
        "hookStrength": "weak|moderate|strong|viral"
    },
    "keywords": {
        "primaryKeyword": "Biryani Recipe",
        "searchIntent": "how-to|review|comparison",
        "keywordCompetition": "low|medium|high|extreme",
        "seoOptimized": True/False
    },
    "scores": {
        "seoScore": 1-10,
        "clickabilityScore": 1-10,
        "overallScore": 1-10
    }
}
```

### Batch Processing

The analyzer processes videos in batches with progress tracking:

```python
# src/processors/batch.py

class BatchProcessor:
    def process_channel(self, channel_id: str, limit: int = None):
        videos = get_unanalyzed_videos(channel_id, self.analysis_type, limit)

        for video in tqdm(videos):
            try:
                result = self._analyze_video(channel_id, video)
                if result:
                    self.progress.record_success()
                else:
                    self.progress.record_skip()
            except Exception as e:
                self.progress.record_failure()

            time.sleep(config.REQUEST_DELAY)  # Rate limiting
```

### Analysis Storage

Analysis results are stored as subcollections:

```
channels/{channelId}/videos/{videoId}/analysis/
├── thumbnail            # Thumbnail vision analysis results
└── title_description    # Combined title+description text analysis results
```

Note: Legacy analysis types (`title`, `description`, `tags`, `content_structure`) may exist in Firestore from previous runs but are no longer generated. The insights phase falls back to legacy `title` analysis when `title_description` is not available.

---

## Phase 3: Per-Content-Type Profiling

### Overview

The insights phase is a pure data summarizer — no interpretation, no ML. It provides:

1. **Per-Content-Type Profiles**: Group videos by `contentSignals.contentType`, compare all vs top 10% by `viewsPerSubscriber`
2. **Content Gap Analysis**: Identify underserved topics and keyword opportunities

### Success Metric

`viewsPerSubscriber` is the primary success metric (best proxy for CTR):
- Normalizes across channels of different sizes
- Top 10% threshold is calculated per content type

### Feature Profiling

```python
# src/profiler.py

class ContentTypeProfiler:
    def profile_content_type(self, content_type, videos):
        """Compare all videos vs top 10% for a content type."""
        vps_values = [v['calculated']['viewsPerSubscriber'] for v in videos]
        threshold = sorted(vps_values, reverse=True)[len(vps_values) // 10]

        top_videos = [v for v in videos if v['calculated']['viewsPerSubscriber'] >= threshold]

        # Profile each feature from thumbnail + title analysis
        features = {}
        for feature_name in self._get_all_features(videos):
            feature_type = self._detect_type(feature_name, videos)  # boolean|numeric|categorical|list

            all_profile = self._profile_feature(feature_name, feature_type, videos)
            top_profile = self._profile_feature(feature_name, feature_type, top_videos)

            features[feature_name] = {
                'type': feature_type,
                'all': all_profile,
                'top10': top_profile,
            }

        return features
```

Feature types are auto-detected:
- **boolean**: `{true_pct, false_pct}` (e.g., `humanPresence.facePresent`)
- **numeric**: `{mean, median, p25, p75}` (e.g., `scores.clickability`)
- **categorical**: `{value_distribution}` (e.g., `composition.layoutType`)
- **list**: `{top_items_by_frequency}` (e.g., `psychology.clickMotivation`)

### Content Gap Analysis

```python
# src/gaps.py

class GapAnalyzer:
    def analyze(self):
        """Find underserved topics with high potential."""
        content_type_stats = {}
        keyword_stats = defaultdict(list)

        for video in self.videos:
            content_type = video.get('contentType', 'unknown')
            vps = video['calculated']['viewsPerSubscriber']

            # Track content type performance
            # Track keyword performance and frequency

        return {
            'contentTypeBreakdown': content_type_stats,
            'keywordOpportunities': self._find_keyword_opportunities(keyword_stats),
        }
```

### Insights Output Schema

```python
# Stored in Firestore: insights/{contentType} (e.g., insights/recipe)
{
    "contentType": "recipe",
    "videoCount": 12500,
    "topPercentileThreshold": 3.2,  # viewsPerSubscriber threshold for top 10%
    "generatedAt": "2024-01-25T10:30:00Z",

    "thumbnail": {
        "composition.layoutType": {
            "type": "categorical",
            "all": {"split-screen": 35, "single-focus": 40, "text-heavy": 15, "other": 10},
            "top10": {"split-screen": 55, "single-focus": 30, "text-heavy": 5, "other": 10}
        },
        "humanPresence.facePresent": {
            "type": "boolean",
            "all": {"true_pct": 65, "false_pct": 35},
            "top10": {"true_pct": 85, "false_pct": 15}
        },
        "scores.clickability": {
            "type": "numeric",
            "all": {"mean": 6.2, "median": 6.0, "p25": 5.0, "p75": 7.5},
            "top10": {"mean": 8.1, "median": 8.0, "p25": 7.5, "p75": 9.0}
        }
    },

    "title": {
        "hooks.hookStrength": {
            "type": "categorical",
            "all": {"weak": 30, "moderate": 45, "strong": 20, "viral": 5},
            "top10": {"weak": 5, "moderate": 25, "strong": 50, "viral": 20}
        }
    }
}

# Stored in Firestore: insights/contentGaps
{
    "generatedAt": "2024-01-25T10:30:00Z",
    "contentTypeBreakdown": {
        "recipe": {"count": 12500, "avgVPS": 1.8, "topVPS": 5.2},
        "vlog": {"count": 8000, "avgVPS": 1.2, "topVPS": 3.8}
    },
    "keywordOpportunities": [
        {"keyword": "air fryer", "count": 15, "avgVPS": 4.5, "opportunity": "high"}
    ]
}

# Stored in Firestore: insights/summary
{
    "generatedAt": "2024-01-25T10:30:00Z",
    "totalVideos": 50000,
    "contentTypes": ["recipe", "vlog", "tutorial", "review"],
    "contentTypeCounts": {"recipe": 12500, "vlog": 8000, "tutorial": 5000, "review": 3000}
}
```

---

## Phase 4: Recommendation Engine

### Overview

The recommender is a TypeScript module (CLI + Firebase Functions API) that generates actionable suggestions by:

1. Loading per-content-type profiles from Firestore (`insights/{contentType}`)
2. Building context from profiling data
3. Using Gemini to generate creative recommendations
4. Falling back to templates if AI fails

### Usage

```bash
# CLI usage
cd functions
npm run recommend -- --topic "Biryani" --type recipe

# API usage (Firebase Functions)
npm run serve  # Start local emulator
curl -X POST http://localhost:5001/PROJECT/us-central1/recommend \
  -H "Content-Type: application/json" \
  -d '{"topic": "Biryani", "type": "recipe"}'
```

### Architecture

```typescript
// src/engine.ts

async function generateRecommendation(
  topic: string,
  contentType: string,
  angle?: string,
  audience?: string
): Promise<Recommendation> {
  // 1. Load insights from Firestore
  const insights = await loadInsights(contentType);

  // 2. Build context from per-content-type profiles
  const context = buildInsightsContext(insights);

  // 3. Generate with Gemini
  try {
    const prompt = buildPrompt(topic, contentType, angle, audience, context);
    const response = await model.generateContent(prompt);
    return parseRecommendation(response);
  } catch {
    // 4. Fallback to templates
    return generateFromTemplates(topic, contentType);
  }
}
```

### Template Fallback

When AI generation fails, templates provide basic recommendations:

```typescript
// src/templates.ts

const TITLE_TEMPLATES: Record<string, string[]> = {
  recipe: [
    "{dish} Recipe | {dish_telugu} | {modifier}",
    "SECRET {dish} Recipe | {dish_telugu} రహస్యం",
  ],
  vlog: [
    "My {topic} Experience | {topic_telugu}",
  ],
};
```

### Recommendation Output

```python
{
    "titles": {
        "primary": {
            "english": "Restaurant Style Hyderabadi Biryani | BEST Recipe",
            "telugu": "హోటల్ స్టైల్ హైదరాబాదీ బిర్యానీ",
            "combined": "Hyderabadi Biryani | హైదరాబాదీ బిర్యానీ | Restaurant Style"
        },
        "alternatives": [
            {"title": "SECRET Biryani Recipe | బిర్యానీ రహస్యం", "reasoning": "Uses power word"}
        ]
    },
    "thumbnail": {
        "layout": "split-composition",
        "elements": {
            "face": {"position": "right-third", "expression": "surprised", "required": True},
            "mainVisual": {"type": "biryani-close-up", "position": "left-center"},
            "text": {
                "primary": {"content": "SECRET", "position": "top-left", "color": "#FFFF00"},
                "secondary": {"content": "బిర్యానీ రహస్యం", "language": "telugu"}
            }
        },
        "colors": {"background": "#FF6B35", "accent": "#FFFF00"}
    },
    "tags": {
        "primary": ["biryani recipe", "hyderabadi biryani"],
        "telugu": ["బిర్యానీ", "హైదరాబాదీ బిర్యానీ"],
        "longtail": ["how to make biryani at home"]
    },
    "posting": {
        "bestDay": "Saturday",
        "bestTime": "18:00 IST",
        "alternativeTimes": ["Sunday 12:00 IST"]
    },
    "prediction": {
        "expectedViewRange": {"low": 15000, "medium": 45000, "high": 120000},
        "positiveFactors": ["Popular keyword", "Optimal thumbnail elements"],
        "riskFactors": ["High competition"]
    }
}
```

---

## Data Schemas

### Firestore Collections

#### `channels/{channelId}`

```javascript
{
  channelId: "UCBSwcE0p0PMwhvE6FVjgITw",
  channelTitle: "Vismai Food",
  channelDescription: "Telugu cooking channel...",
  customUrl: "@VismaiFood",

  subscriberCount: 4930000,
  videoCount: 2200,
  viewCount: 1250000000,

  thumbnailUrl: "https://yt3.ggpht.com/...",
  thumbnailStoragePath: "channel_thumbnails/UCBSwcE0p0PMwhvE6FVjgITw.jpg",
  bannerUrl: "https://...",

  country: "IN",
  publishedAt: Timestamp,

  category: "cooking",      // From channels.json
  priority: 1,              // From channels.json

  sourceUrl: "https://www.youtube.com/@VismaiFood",
  scrapedAt: Timestamp,
  lastUpdatedAt: Timestamp
}
```

#### `channels/{channelId}/videos/{videoId}`

```javascript
{
  videoId: "dQw4w9WgXcQ",
  channelId: "UCBSwcE0p0PMwhvE6FVjgITw",

  title: "Veg Manchurian Recipe | వెజ్ మంచూరియా",
  description: "Full recipe...",
  publishedAt: Timestamp,

  thumbnails: {
    default: "https://img.youtube.com/vi/xxx/default.jpg",
    medium: "https://img.youtube.com/vi/xxx/mqdefault.jpg",
    high: "https://img.youtube.com/vi/xxx/hqdefault.jpg"
  },
  thumbnailStoragePath: "thumbnails/UCBSwcE0p0PMwhvE6FVjgITw/dQw4w9WgXcQ.jpg",

  duration: "PT15M33S",
  durationSeconds: 933,

  viewCount: 16000000,
  likeCount: 450000,
  commentCount: 12000,

  tags: ["veg manchurian", "telugu cooking", ...],

  categoryId: "26",
  categoryName: "Howto & Style",
  defaultLanguage: "te",
  madeForKids: false,

  isShort: false,
  videoUrl: "https://www.youtube.com/watch?v=dQw4w9WgXcQ",

  scrapedAt: Timestamp,

  calculated: {
    engagementRate: 2.89,
    likeRatio: 2.81,
    commentRatio: 0.075,
    viewsPerSubscriber: 3.25,
    daysSincePublish: 365,
    viewsPerDay: 43836,
    publishDayOfWeek: "Saturday",
    publishHourIST: 18,
    titleLength: 52,
    descriptionLength: 2450,
    tagCount: 28,
    hasNumberInTitle: false,
    hasEmojiInTitle: false,
    hasTeluguInTitle: true,
    hasEnglishInTitle: true
  }
}
```

#### `channels/{channelId}/videos/{videoId}/analysis/{type}`

```javascript
// type = "thumbnail" (vision analysis)
{
  analyzedAt: "2024-01-25T10:30:00Z",
  modelUsed: "gemini-2.5-flash",
  analysisVersion: "1.0",

  composition: { ... },
  humanPresence: { ... },
  textElements: { ... },
  colors: { ... },
  food: { ... },
  graphics: { ... },
  branding: { ... },
  psychology: { ... },
  technicalQuality: { ... },
  scores: { ... }
}

// type = "title_description" (combined text analysis)
{
  analyzedAt: "2024-01-25T10:30:00Z",
  modelUsed: "gemini-2.5-flash",
  analysisVersion: "1.0",
  rawTitle: "Original title text",

  // Title analysis
  structure: { ... },
  language: { ... },
  hooks: { ... },
  keywords: { ... },
  formatting: { ... },
  contentSignals: { ... },      // includes contentType
  teluguAnalysis: { ... },
  competitive: { ... },
  scores: { ... },

  // Description analysis (lean)
  descriptionAnalysis: {
    structure: { ... },
    timestamps: { ... },
    recipeContent: { ... },
    hashtags: { ... },
    callToActions: { ... },
    seo: { ... }
  }
}
```

#### `scrape_progress/{channelId}`

```javascript
{
  channelId: "UCBSwcE0p0PMwhvE6FVjgITw",
  channelTitle: "Vismai Food",
  sourceUrl: "https://www.youtube.com/@VismaiFood",

  status: "in_progress",  // pending | in_progress | completed | failed
  phase: "scraping",      // scraping | thumbnails | calculations

  totalVideos: 2200,
  videosProcessed: 1547,
  thumbnailsDownloaded: 1547,

  lastProcessedVideoId: "abc123xyz",
  lastPlaylistPageToken: "CGQQAA",

  startedAt: Timestamp,
  lastProcessedAt: Timestamp,
  completedAt: null,

  errorMessage: null,
  retryCount: 0
}
```

#### `insights/{contentType}` (e.g., `insights/recipe`)

```javascript
{
  contentType: "recipe",
  videoCount: 12500,
  topPercentileThreshold: 3.2,  // viewsPerSubscriber for top 10%
  generatedAt: "2024-01-25T10:30:00Z",

  thumbnail: {
    // Per-feature profiles comparing all vs top 10%
    "composition.layoutType": { type: "categorical", all: {...}, top10: {...} },
    "humanPresence.facePresent": { type: "boolean", all: {...}, top10: {...} },
    "scores.clickability": { type: "numeric", all: {...}, top10: {...} }
  },
  title: {
    "hooks.hookStrength": { type: "categorical", all: {...}, top10: {...} },
    // ... more features
  }
}
```

#### `insights/contentGaps`

```javascript
{
  generatedAt: "2024-01-25T10:30:00Z",
  contentTypeBreakdown: { recipe: {...}, vlog: {...} },
  keywordOpportunities: [...]
}
```

#### `insights/summary`

```javascript
{
  generatedAt: "2024-01-25T10:30:00Z",
  totalVideos: 50000,
  contentTypes: ["recipe", "vlog", "tutorial"],
  contentTypeCounts: { recipe: 12500, vlog: 8000, tutorial: 5000 }
}
```

---

## API Integration Details

### YouTube Data API v3

**Base URL**: `https://www.googleapis.com/youtube/v3`

**Authentication**: API Key (passed as query parameter)

**Endpoints Used**:

| Endpoint | Purpose | Quota |
|----------|---------|-------|
| `channels.list` | Channel details | 1 |
| `playlistItems.list` | Video IDs from playlist | 1 |
| `videos.list` | Video details | 1 |
| `search.list` | Channel search (avoid) | 100 |

**Rate Limits**: 10,000 units/day

**Example Request**:
```typescript
const response = await youtube.videos.list({
  part: ['snippet', 'contentDetails', 'statistics', 'topicDetails'],
  id: ['video1', 'video2', ...],  // Up to 50
});
```

### Google Gemini API

**Model**: `gemini-2.5-flash`

**Authentication**: API Key via `google-generativeai` SDK

**Configuration**:
```python
generation_config = {
    'temperature': 0.1,      # Low for consistent JSON output
    'top_p': 0.95,
    'top_k': 40,
    'max_output_tokens': 8192
}
```

**Vision Input**: PIL Image objects or raw bytes

**Rate Limits**: Varies by tier (free tier: 60 requests/minute)

### Firebase Admin SDK

**Firestore Operations**:
```python
# Read
doc = db.collection('channels').document(channel_id).get()

# Write
db.collection('channels').document(channel_id).set(data, merge=True)

# Batch write (for efficiency)
batch = db.batch()
for video in videos:
    ref = db.collection('channels').document(cid).collection('videos').document(vid)
    batch.set(ref, video)
batch.commit()
```

**Storage Operations**:
```python
# Upload
blob = bucket.blob(storage_path)
blob.upload_from_string(image_bytes, content_type='image/jpeg')

# Download
image_bytes = blob.download_as_bytes()

# Signed URL
url = blob.generate_signed_url(expiration=3600)
```

---

## Error Handling & Resilience

### Scraper Error Handling

```typescript
// Retry with exponential backoff
export async function retry<T>(
  fn: () => Promise<T>,
  maxRetries: number,
  baseDelayMs: number
): Promise<T> {
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      if (attempt < maxRetries - 1) {
        await delay(baseDelayMs * Math.pow(2, attempt));
      } else {
        throw error;
      }
    }
  }
}
```

### Progress Recovery

If the scraper is interrupted:

1. Progress is automatically saved to Firestore
2. On restart, `lastPlaylistPageToken` resumes pagination
3. Videos already scraped are skipped
4. Thumbnails already downloaded are skipped

```typescript
// Check for existing progress
const existingProgress = await getProgress(channelId);
if (existingProgress && existingProgress.status !== 'completed') {
  resumeFromToken = existingProgress.lastPlaylistPageToken;
  resumeFromVideoCount = existingProgress.videosProcessed;
}
```

### Analyzer Error Handling

```python
def analyze_image(prompt, image_data, retries=3):
    last_error = None

    for attempt in range(retries):
        try:
            response = model.generate_content([prompt, image])
            return json.loads(response.text)
        except json.JSONDecodeError:
            # Gemini returned invalid JSON
            last_error = e
        except Exception as e:
            # API error
            last_error = e

        time.sleep(config.RETRY_DELAY * (attempt + 1))

    raise last_error
```

### Graceful Degradation

The recommender falls back to templates when AI fails:

```python
try:
    recommendation = self.model.generate_content(prompt)
    return json.loads(recommendation.text)
except:
    # Use template-based generation
    return self._generate_from_templates(topic, content_type)
```

---

## Performance Considerations

### Scraper Optimization

1. **Batch Processing**: Video details requested in batches of 50
2. **Parallel Thumbnails**: Could be parallelized (current: sequential)
3. **Progress Checkpoints**: Save after each video batch
4. **Memory Efficient**: Stream data to Firestore, don't accumulate

### Analyzer Optimization

1. **Skip Analyzed**: Check if analysis exists before processing
2. **Rate Limiting**: Configurable delay between requests
3. **Batch Progress**: Track at channel level, not video level

### Firestore Optimization

1. **Batch Writes**: Use `batch.commit()` for multiple documents
2. **Subcollections**: Videos as subcollection reduces document size
3. **Indexes**: Create indexes for common query patterns

### Estimated Processing Times

| Phase | Volume | Estimated Time |
|-------|--------|----------------|
| Scraper | 100 channels, 500 videos each | 3-5 days (quota limited) |
| Analyzer | 50,000 videos, 2 analysis types | 2-3 days |
| Insights | Aggregation of all data | 10-30 minutes |
| Recommender | Single query | 5-10 seconds |

### Cost Estimates

| Service | Usage | Cost |
|---------|-------|------|
| YouTube API | Free tier | $0 |
| Firebase Firestore | ~200K documents | ~$5-10 |
| Firebase Storage | ~3GB thumbnails | ~$1-2 |
| Gemini API | 50K images + 50K text (2 calls/video) | ~$200-300 |

---

## Appendix: Running the System

### Prerequisites

1. Node.js 18+ and npm
2. Python 3.11+
3. YouTube Data API v3 key
4. Firebase project with Firestore and Storage
5. Google AI Studio API key (Gemini)

### Setup

```bash
# Clone and setup
cd youtube_channel_analysis
cp .env.example .env
# Edit .env with your credentials

# Phase 1: Scraper
cd scraper
npm install
npm test  # Verify installation
npx tsx scripts/validate.ts  # Test connections
npm start  # Run scraper

# Phase 2: Analyzer (after scraping completes)
cd ../analyzer
pip install -r requirements.txt
python -m src.main --validate
python -m src.main

# Phase 3: Insights (after analysis completes)
cd ../insights
pip install -r requirements.txt
python -m src.main

# Phase 4: Recommender
cd ../functions
npm install
npm run recommend -- --topic "Biryani" --type recipe
```

### Monitoring Progress

```bash
# Scraper: Check console output for real-time progress
# Also check Firestore: scrape_progress/{channelId}

# Analyzer: Check console with tqdm progress bars
# Also check Firestore: analysis_progress/{type}

# Insights: Check console output and Firestore
# Also check Firestore: insights/{contentType}, insights/contentGaps, insights/summary
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Quota exhausted | Wait until midnight Pacific, then resume |
| Firebase permission denied | Check service account credentials |
| Gemini rate limit | Increase REQUEST_DELAY in config |
| Invalid JSON from Gemini | Retry logic handles this |
| Channel not found | Check URL format, try different format |

---

*Documentation generated for YouTube Intelligence System v1.0*
