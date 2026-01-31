# YouTube Intelligence System - Technical Documentation

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Phase 1: YouTube Scraper](#phase-1-youtube-scraper)
4. [Phase 2: AI Analyzer](#phase-2-ai-analyzer)
5. [Phase 3: Per-Content-Type Profiling](#phase-3-per-content-type-profiling)
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
│   ├── src/
│   │   ├── __init__.py
│   │   ├── main.py           # Entry point (sync + batch routing)
│   │   ├── config.py         # Configuration
│   │   ├── firebase_client.py  # Firebase operations + batch_jobs CRUD
│   │   ├── gemini_client.py  # Gemini API wrapper (response_schema support)
│   │   ├── analyzers/        # Per-video analysis modules (sync mode)
│   │   │   ├── __init__.py
│   │   │   ├── thumbnail.py  # Vision analysis
│   │   │   └── title_description.py  # Combined title+description text analysis
│   │   ├── batch_api/        # Gemini Batch API integration
│   │   │   ├── __init__.py
│   │   │   ├── schemas.py    # Pydantic models for response_schema
│   │   │   ├── client.py     # google-genai SDK wrapper
│   │   │   ├── prepare.py    # Build JSONL request files
│   │   │   ├── submit.py     # Submit jobs + track in Firestore
│   │   │   └── import_results.py  # Download results + save to Firestore
│   │   ├── processors/       # Sync mode orchestration
│   │   │   ├── __init__.py
│   │   │   ├── batch.py      # Channel/video iteration
│   │   │   └── progress.py   # Progress tracking
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

### Processing Modes

The analyzer supports two processing modes:

| Mode | SDK | Description | Cost |
|------|-----|-------------|------|
| **Sync** (default) | `google-generativeai` | Per-video API calls with `response_schema` | Standard |
| **Batch** | `google-genai` | Gemini Batch API, JSONL file upload | 50% savings |

Both modes use:
- **`response_schema`**: Pydantic models (`ThumbnailAnalysisSchema`, `TitleDescriptionAnalysisSchema`) guarantee valid JSON output
- **`system_instruction`**: Concise role/domain context set on the model
- **User prompts**: Shorter analysis instructions (no JSON template needed since schema enforces structure)

### Gemini Client

The Gemini client uses model caching per analysis type and structured output via `response_schema`:

```python
# src/gemini_client.py

import google.generativeai as genai

genai.configure(api_key=config.GOOGLE_API_KEY)

# Model instances cached by analysis_type
_models: Dict[str, genai.GenerativeModel] = {}

def get_model(analysis_type: Optional[str] = None) -> genai.GenerativeModel:
    """Get or create Gemini model with response_schema for structured output."""
    cache_key = analysis_type or 'default'
    if cache_key not in _models:
        gen_config = {
            'temperature': 0.1,
            'top_p': 0.95,
            'top_k': 40,
            'max_output_tokens': 8192,
        }
        model_kwargs = {'model_name': config.GEMINI_MODEL}

        if analysis_type:
            system_instruction, response_schema = _get_schema_config(analysis_type)
            if system_instruction:
                model_kwargs['system_instruction'] = system_instruction
            if response_schema:
                gen_config['response_mime_type'] = 'application/json'
                gen_config['response_schema'] = response_schema

        model_kwargs['generation_config'] = gen_config
        _models[cache_key] = genai.GenerativeModel(**model_kwargs)
    return _models[cache_key]

def analyze_image(prompt, image_data, analysis_type=None) -> Dict[str, Any]:
    """Analyze image with Gemini Vision (uses response_schema when analysis_type set)."""
    model = get_model(analysis_type)
    image = Image.open(io.BytesIO(image_data))
    response = model.generate_content([prompt, image])
    return parse_json_response(response.text)

def analyze_text(prompt, text, analysis_type=None) -> Dict[str, Any]:
    """Analyze text with Gemini (uses response_schema when analysis_type set)."""
    model = get_model(analysis_type)
    response = model.generate_content(f"{prompt}\n\nText to analyze:\n{text}")
    return parse_json_response(response.text)
```

Retry logic handles specific error types:
- `ResourceExhausted` (rate limit): exponential backoff with 2x multiplier
- `InvalidArgument`: no retry (request is malformed)
- `GoogleAPIError`: transient errors, linear backoff
- `JSONDecodeError`: no retry (response format issue)
- General `Exception`: logged with type info, linear backoff

### Thumbnail Analysis Schema (~109 fields)

Defined as a Pydantic model in `src/batch_api/schemas.py`:

```python
class ThumbnailAnalysisSchema(BaseModel):
    composition: ThumbnailComposition        # 7 fields: layoutType, gridStructure, visualBalance, etc.
    humanPresence: ThumbnailHumanPresence    # 16 fields: facePresent, faceCount, expression, etc.
    textElements: ThumbnailTextElements      # 14 fields + nested primaryText (11 fields)
    colors: ThumbnailColors                  # 10 fields + nested dominantColors list
    food: ThumbnailFood                      # 15 fields: foodPresent, mainDish, appetiteAppeal, etc.
    graphics: ThumbnailGraphics              # 18 fields: arrows, circles, borders, badges, etc.
    branding: ThumbnailBranding              # 5 fields: channelLogoVisible, professionalQuality, etc.
    psychology: ThumbnailPsychology          # 16 fields: curiosityGap, socialProof, urgency, etc.
    technicalQuality: ThumbnailTechnicalQuality  # 6 fields: resolution, sharpness, lighting, etc.
    scores: ThumbnailScores                  # 8 fields: clickability, clarity, predictedCTR, etc.
```

Key sections (examples of values):

```json
{
    "composition": {
        "layoutType": "split-screen|single-focus|collage|text-heavy|minimal",
        "gridStructure": "rule-of-thirds|centered|asymmetric|golden-ratio",
        "visualBalance": "balanced|left-heavy|right-heavy|top-heavy|bottom-heavy",
        "negativeSpace": "minimal|moderate|heavy",
        "complexity": "simple|medium|complex|cluttered",
        "focalPoint": "description of main focal point",
        "depthOfField": "shallow|deep|flat"
    },
    "humanPresence": {
        "facePresent": true,
        "faceCount": 1,
        "faceSize": "small|medium|large|dominant",
        "expression": "happy|surprised|shocked|curious|neutral|excited|disgusted|thinking",
        "expressionIntensity": "subtle|moderate|high|extreme",
        "mouthOpen": true,
        "eyeContact": true,
        "eyebrowsRaised": false,
        "bodyVisible": true,
        "bodyPortion": "face-only|upper|half|full",
        "handVisible": true,
        "handGesture": "none|thumbs-up|pointing|holding-item|peace|ok",
        "lookingDirection": "camera|left|right|down|at-food"
    },
    "food": {
        "foodPresent": true,
        "mainDish": "dish name",
        "dishCategory": "rice|curry|snack|dessert|bread|indo-chinese|breakfast",
        "presentation": "close-up|plated|cooking-process|ingredients|before-after",
        "platingStyle": "rustic|elegant|home-style|restaurant",
        "steam": true,
        "sizzle": false,
        "garnished": true,
        "freshness": "low|medium|high",
        "appetiteAppeal": 8,
        "portionSize": "small|medium|generous|huge",
        "cookingStage": "raw|in-progress|finished"
    },
    "psychology": {
        "curiosityGap": true,
        "socialProof": false,
        "urgency": false,
        "scarcity": false,
        "authority": false,
        "controversy": false,
        "transformation": true,
        "luxury": false,
        "nostalgia": false,
        "shock": false,
        "humor": false,
        "fear": false,
        "primaryEmotion": "curiosity|excitement|appetite|nostalgia|amusement",
        "emotionalIntensity": "low|moderate|high",
        "clickMotivation": ["reasons why someone would click"],
        "targetAudience": "description"
    },
    "scores": {
        "clickability": 7,
        "clarity": 8,
        "professionalism": 6,
        "uniqueness": 5,
        "appetiteAppeal": 9,
        "emotionalImpact": 6,
        "predictedCTR": "below-average|average|above-average|exceptional",
        "improvementAreas": ["list of suggestions"]
    }
}
```

### Title + Description Analysis Schema (~140 fields)

Defined as a Pydantic model in `src/batch_api/schemas.py`:

```python
class TitleDescriptionAnalysisSchema(BaseModel):
    # Title analysis (~120 fields)
    structure: TitleStructure          # 11 fields: pattern, segments, separators, counts
    language: TitleLanguage            # 14 fields: languages, scripts, ratios, transliteration
    hooks: TitleHooks                  # 16 fields + nested TitleTriggers (10 fields)
    keywords: TitleKeywords            # 14 fields: primaryKeyword, niche, SEO, competition
    formatting: TitleFormatting        # 16 fields: capitalization, emojis, brackets, hashtags
    contentSignals: TitleContentSignals  # 15 fields: contentType, isRecipe, series, brands
    teluguAnalysis: TitleTeluguAnalysis  # 12 fields: register, dialect, honorifics, food terms
    competitive: TitleCompetitive      # 6 fields: uniquenessScore, standoutFactor
    scores: TitleScores                # 11 fields: seo, clickability, clarity, overall (1-10)

    # Description analysis (~20 fields)
    descriptionAnalysis: DescriptionAnalysis  # structure, timestamps, recipeContent, hashtags, ctas, seo
```

Key sections (examples of values):

```json
{
    "structure": {
        "pattern": "dish-name | translation | modifier",
        "patternType": "single|segmented|question|list|statement",
        "segments": [
            {"text": "Biryani Recipe", "type": "dish-name", "language": "english"},
            {"text": "బిర్యానీ", "type": "translation", "language": "telugu"}
        ],
        "segmentCount": 2,
        "characterCount": 67,
        "wordCount": 8,
        "teluguCharacterCount": 12,
        "englishCharacterCount": 55
    },
    "language": {
        "languages": ["english", "telugu"],
        "primaryLanguage": "english",
        "hasTeluguScript": true,
        "hasLatinScript": true,
        "hasTransliteration": true,
        "transliteratedWords": ["biryani"],
        "codeSwitch": true,
        "codeSwitchStyle": "translation|mixed|parallel",
        "teluguRatio": 0.18,
        "englishRatio": 0.82
    },
    "hooks": {
        "isQuestion": false,
        "hasNumber": false,
        "hasPowerWord": true,
        "powerWords": ["SECRET", "Restaurant Style"],
        "triggers": {
            "curiosityGap": true,
            "socialProof": false,
            "urgency": false,
            "exclusivity": true,
            "controversy": false,
            "transformation": false,
            "challenge": false,
            "comparison": false,
            "personal": false,
            "storytelling": false
        },
        "hookStrength": "weak|moderate|strong|viral",
        "primaryHook": "description of main hook"
    },
    "keywords": {
        "primaryKeyword": "Biryani Recipe",
        "primaryKeywordPosition": "start|middle|end",
        "searchIntent": "how-to|review|comparison|information|entertainment",
        "niche": "cooking",
        "subNiche": "Indian rice dishes",
        "keywordCompetition": "low|medium|high|extreme",
        "seoOptimized": true,
        "keywordInFirst3Words": true
    },
    "contentSignals": {
        "contentType": "recipe|tutorial|review|vlog|challenge|reaction|comparison|list|storytime|unboxing|explainer|news",
        "isRecipe": true,
        "isTutorial": false,
        "isPartOfSeries": false,
        "hasCollaboration": false,
        "hasBrandMention": false
    },
    "teluguAnalysis": {
        "formalRegister": false,
        "respectLevel": "casual|neutral|respectful",
        "dialectHints": "andhra|telangana|rayalaseema|neutral",
        "hasHonorifics": false,
        "foodTermsAccurate": true,
        "targetAudienceAge": "young|middle|older|all",
        "urbanVsRural": "urban|rural|both"
    },
    "competitive": {
        "uniquenessScore": 6,
        "followsNichePattern": true,
        "standoutFactor": "description"
    },
    "scores": {
        "seoScore": 7,
        "clickabilityScore": 8,
        "clarityScore": 9,
        "emotionalScore": 5,
        "uniquenessScore": 6,
        "lengthScore": 7,
        "clickbaitLevel": 3,
        "overallScore": 7,
        "predictedPerformance": "below-average|average|above-average|exceptional"
    },
    "descriptionAnalysis": {
        "structure": {
            "length": 2450,
            "lineCount": 35,
            "wellOrganized": true,
            "firstLineHook": true
        },
        "timestamps": {
            "hasTimestamps": true,
            "timestampCount": 5
        },
        "recipeContent": {
            "hasIngredients": true,
            "ingredientCount": 12,
            "hasInstructions": true,
            "instructionSteps": 8,
            "hasCookingTime": true
        },
        "hashtags": {
            "count": 5,
            "position": "start|middle|end|throughout|none"
        },
        "ctas": {
            "hasSubscribeCTA": true,
            "hasLikeCTA": true,
            "hasCommentCTA": true,
            "commentQuestion": "What's your favorite biryani recipe?"
        },
        "seo": {
            "keywordInFirst100Chars": true,
            "keywordDensity": 0.02,
            "internalLinking": "none|minimal|good|excellent"
        }
    }
}
```

### Sync Mode Processing

The analyzer processes videos sequentially with progress tracking:

```python
# src/processors/batch.py

class BatchProcessor:
    def process_channel(self, channel_id: str, limit: int = None):
        # Paginated fetch to avoid loading all videos into memory
        videos = get_unanalyzed_videos_paginated(channel_id, self.analysis_type, limit)

        for video in tqdm(videos):
            try:
                result = self._analyze_video(channel_id, video)
                if result is None:
                    self.progress.record_skip()
                else:
                    self.progress.record_success()
            except GeminiRateLimitError:
                self.progress.record_failure()
                time.sleep(config.REQUEST_DELAY * 4)  # Extra delay
            except GeminiResponseError:
                self.progress.record_failure()
            except GeminiAPIError:
                self.progress.record_failure()
            except (ConnectionError, TimeoutError, OSError):
                self.progress.record_failure()
            except Exception:
                self.progress.record_failure()

            time.sleep(config.REQUEST_DELAY)  # 0.5s rate limiting
```

### Batch Mode (Gemini Batch API)

The batch mode submits all requests as a JSONL file to the Gemini Batch API for 50% cost savings. Uses the `google-genai` SDK (different from the `google-generativeai` SDK used in sync mode).

#### 4-Phase Workflow

```
PREPARE → SUBMIT → POLL → IMPORT
```

| Phase | Module | What it does |
|-------|--------|-------------|
| `prepare` | `batch_api/prepare.py` | Scans Firestore for unanalyzed videos, writes JSONL to `data/batch/` |
| `submit` | `batch_api/submit.py` | Uploads JSONL via Files API, creates batch job, tracks in Firestore `batch_jobs` |
| `poll` | `batch_api/submit.py` | Checks job status every 60s until terminal state |
| `import` | `batch_api/import_results.py` | Downloads result JSONL, parses results, saves to Firestore |

```bash
# Run all phases sequentially
python -m src.main --mode batch --type thumbnail

# Or run phases individually
python -m src.main --mode batch --phase prepare --type thumbnail
python -m src.main --mode batch --phase submit --type thumbnail
python -m src.main --mode batch --phase poll --type thumbnail
python -m src.main --mode batch --phase import --type thumbnail

# Check status of all jobs
python -m src.main --mode batch --phase status
```

#### Batch Request Key Format

Keys follow the pattern `{channelId}_{videoId}_{analysisType}`. On import, keys are parsed using fixed-length channel IDs (24 chars starting with UC) and 11-char video IDs.

#### Thumbnail Batch Requests

Thumbnails use GCS URIs directly (`gs://{bucket}/thumbnails/UCxxx/videoId.jpg`) since Firebase Storage is Google Cloud Storage.

### Analysis Storage

Analysis results are stored as Firestore subcollections:

```
channels/{channelId}/videos/{videoId}/analysis/
├── thumbnail            # Thumbnail vision analysis (analysisVersion: "1.0")
└── title_description    # Combined title+description text analysis (analysisVersion: "2.0")

batch_jobs/{jobId}       # Batch job tracking (state, request count, import status)
analysis_progress/{type} # Sync mode progress tracking (saves every 10 records)
```

Metadata fields added to each analysis document:
- `analyzedAt`: ISO timestamp
- `modelUsed`: `"gemini-2.5-flash"`
- `analysisVersion`: `"1.0"` (thumbnail) or `"2.0"` (title_description)
- `batchMode`: `true` (batch mode only)
- `rawTitle`: original title text (title_description only)
- `hasDescription`: whether description was present (title_description only)

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
  analysisVersion: "2.0",
  rawTitle: "Original title text",
  hasDescription: true,

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
    ctas: { ... },
    seo: { ... }
  }
}
```

#### `batch_jobs/{jobId}`

```javascript
{
  jobName: "batch_thumbnail_20260125_103000",
  analysisType: "thumbnail",        // thumbnail | title_description
  state: "JOB_STATE_SUCCEEDED",     // PENDING, RUNNING, SUCCEEDED, FAILED, CANCELLED
  requestCount: 500,
  requestFile: "data/batch/batch_thumbnail_20260125_103000.jsonl",
  resultFile: "data/batch/results_thumbnail_20260125_103000.jsonl",
  createdAt: "2026-01-25T10:30:00Z",
  completedAt: "2026-01-25T11:45:00Z",
  importedAt: "2026-01-25T11:50:00Z",
  importedCount: 498,
  failedCount: 2
}
```

#### `analysis_progress/{analysisType}`

```javascript
// analysisType = "thumbnail" or "title_description"
{
  analysisType: "thumbnail",
  totalProcessed: 1500,
  successCount: 1480,
  failureCount: 15,
  skipCount: 5,
  lastUpdatedAt: "2026-01-25T10:30:00Z"
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

**Model**: `gemini-2.5-flash` (configured in `shared/constants.py`)

**Two SDKs Used**:
- **Sync mode**: `google-generativeai` SDK — per-video calls with `response_schema` (Pydantic models)
- **Batch mode**: `google-genai` SDK — JSONL file upload, batch job management

**Authentication**: API Key via `GOOGLE_API_KEY` environment variable

**Configuration**:
```python
generation_config = {
    'temperature': 0.1,           # Low for consistent JSON output
    'top_p': 0.95,
    'top_k': 40,
    'max_output_tokens': 8192,
    'response_mime_type': 'application/json',  # When using response_schema
    'response_schema': PydanticModel           # Enforces structured output
}
```

**Vision Input**: PIL Image objects (sync) or GCS URIs `gs://bucket/path` (batch)

**Rate Limits**: Varies by tier (free tier: 60 requests/minute)

**Batch API Tier Limits**:
| Tier | Enqueued Token Limit | Max requests per job |
|------|---------------------|---------------------|
| Tier 1 | 3M tokens | ~680 |
| Tier 2 | 400M tokens | ~50K (API max) |
| Tier 3 | 1B tokens | ~50K, concurrent jobs |

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

The Gemini client uses `call_with_retry()` from `shared/gemini_utils.py` with 3 retries and linear backoff. The `BatchProcessor` handles specific exception types:

```python
# src/processors/batch.py - per-video error handling

except GeminiRateLimitError:
    # Rate limit (429) — extra delay (4x REQUEST_DELAY)
    self.progress.record_failure()
    time.sleep(config.REQUEST_DELAY * 4)
except GeminiResponseError:
    # Invalid/blocked response from Gemini
    self.progress.record_failure()
except GeminiAPIError:
    # General API-level errors
    self.progress.record_failure()
except (ConnectionError, TimeoutError, OSError):
    # Network errors
    self.progress.record_failure()
except Exception:
    # Unexpected errors — logged with type info
    self.progress.record_failure()
```

Custom exception classes in `gemini_client.py`:
- `GeminiAPIError`: Base class for all Gemini errors
- `GeminiRateLimitError(GeminiAPIError)`: 429 / ResourceExhausted
- `GeminiResponseError(GeminiAPIError)`: Invalid or blocked response

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
2. **Rate Limiting**: 0.5s delay between requests (hardcoded in config)
3. **Paginated Queries**: `get_unanalyzed_videos_paginated()` uses Firestore cursors (page size 100)
4. **Progress Batching**: Writes to Firestore every 10 records (not per-video)
5. **Batch Mode**: 50% cost savings via Gemini Batch API (submit JSONL, poll, import)
6. **Model Caching**: Gemini model instances cached per analysis type

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
pip install -r ../requirements.txt
python -m src.main --validate              # Test connections
python -m src.main                          # Sync mode (all types)
python -m src.main --mode batch --type all  # Batch mode (50% cheaper)

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
| Gemini rate limit | Wait and retry; consider upgrading Gemini API tier |
| Invalid JSON from Gemini | Retry logic handles this |
| Channel not found | Check URL format, try different format |

---

*Documentation generated for YouTube Intelligence System v1.0*
