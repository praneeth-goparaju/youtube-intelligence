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
2. **Analyze** thumbnails, titles, descriptions, and tags using AI
3. **Discover** patterns that correlate with high performance
4. **Generate** data-driven recommendations for new video creation

### Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Scraper | TypeScript + Node.js | YouTube API integration |
| Database | Firebase Firestore | Structured data storage |
| File Storage | Firebase Storage | Thumbnail images |
| AI Analysis | Google Gemini 2.0 Flash | Vision + text analysis |
| Analytics | Python + Pandas/NumPy/SciPy | Statistical analysis |
| Recommendations | Python + Gemini | AI-powered suggestions |

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
│  (TypeScript)│    │   (Python)   │    │   (Python)   │    │   (Python)   │
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
│   │   │   ├── title.py      # Title analysis
│   │   │   ├── description.py
│   │   │   ├── tags.py
│   │   │   └── content_structure.py  # Inferred video structure
│   │   ├── processors/       # Batch processing
│   │   │   ├── __init__.py
│   │   │   ├── batch.py
│   │   │   └── progress.py
│   │   └── prompts/          # AI prompts
│   │       ├── __init__.py
│   │       ├── thumbnail_prompt.py
│   │       ├── title_prompt.py
│   │       ├── description_prompt.py
│   │       ├── tags_prompt.py
│   │       └── content_structure_prompt.py  # Structure inference prompt
│   ├── scripts/              # Individual analysis runners
│   └── tests/
│
├── insights/                 # PHASE 3: Pattern Discovery
│   ├── requirements.txt
│   ├── src/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── firebase_client.py
│   │   ├── correlations.py   # Statistical analysis
│   │   ├── patterns.py       # Pattern extraction
│   │   ├── gaps.py           # Content gap analysis
│   │   └── reports.py        # Report generation
│   └── outputs/              # Generated reports
│
└── recommender/              # PHASE 4: Recommendation Engine
    ├── requirements.txt
    ├── src/
    │   ├── __init__.py
    │   ├── main.py
    │   ├── config.py
    │   ├── firebase_client.py
    │   ├── engine.py         # Recommendation logic
    │   └── templates.py      # Title/thumbnail templates
    └── examples/
        └── sample_queries.json
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

The analyzer processes scraped data using Google Gemini 2.0 Flash:

- **Thumbnail Analysis**: Vision-based analysis of image composition, colors, text, faces
- **Title Analysis**: Text analysis of structure, language, hooks, keywords
- **Description Analysis**: Content parsing for timestamps, links, CTAs
- **Tag Analysis**: Keyword categorization and strategy evaluation
- **Content Structure Analysis**: Infers video structure from metadata (ToS-compliant transcript alternative)
  - Video segments and pacing from timestamps
  - Talking points and content outline inference
  - Recipe structure detection (steps, techniques, equipment)
  - Engagement points and retention strategies
  - Content classification and SEO insights

### Gemini Client

```python
# src/gemini_client.py

import google.generativeai as genai

genai.configure(api_key=config.GOOGLE_API_KEY)

_model = genai.GenerativeModel(
    model_name='gemini-2.0-flash',
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
├── thumbnail          # Thumbnail analysis results
├── title              # Title analysis results
├── description        # Description analysis results
├── tags               # Tag analysis results
└── content_structure  # Inferred video structure (transcript alternative)
```

---

## Phase 3: Pattern Discovery

### Overview

The insights phase performs statistical analysis to find:

1. **Correlations**: Features that correlate with view counts
2. **Patterns**: Elements common in top-performing videos
3. **Timing**: Optimal posting days and hours
4. **Content Gaps**: Underserved topics with high potential

### Correlation Analysis

```python
# src/correlations.py

class CorrelationAnalyzer:
    def find_top_correlations(self, target='view_count'):
        """Find features with strongest correlation to views."""
        correlations = []

        for column in self.df.columns:
            if not is_numeric(column):
                continue

            corr, p_value = stats.pearsonr(
                self.df[column].values,
                self.df[target].values
            )

            if abs(corr) > 0.1 and p_value < 0.05:
                correlations.append({
                    'feature': column,
                    'correlation': corr,
                    'p_value': p_value,
                    'direction': 'positive' if corr > 0 else 'negative'
                })

        return sorted(correlations, key=lambda x: abs(x['correlation']), reverse=True)
```

### Pattern Extraction

Videos are categorized by performance tier:

```python
# src/patterns.py

class PatternExtractor:
    def _categorize_by_performance(self):
        views = [v['video']['viewCount'] for v in self.videos]

        self.top_10_threshold = np.percentile(views, 90)
        self.top_25_threshold = np.percentile(views, 75)

        for video in self.videos:
            view_count = video['video']['viewCount']
            if view_count >= self.top_10_threshold:
                video['performance_tier'] = 'top_10'
            elif view_count >= self.top_25_threshold:
                video['performance_tier'] = 'top_25'
            else:
                video['performance_tier'] = 'normal'
```

Patterns are found by comparing top performers to average:

```python
def extract_thumbnail_patterns(self):
    top_videos = self._get_tier_videos('top_10')
    all_videos = self.videos

    # Find elements overrepresented in top videos
    for element in top_videos:
        top_rate = count_in_top / len(top_videos)
        all_rate = count_in_all / len(all_videos)

        if top_rate > all_rate * 1.2:  # 20% more common
            patterns.append({
                'element': element,
                'lift': top_rate / all_rate
            })
```

### Timing Analysis

```python
# src/patterns.py

def extract_timing_patterns(self):
    day_performance = defaultdict(list)
    hour_performance = defaultdict(list)

    for video in self.videos:
        day = video['video']['calculated']['publishDayOfWeek']
        hour = video['video']['calculated']['publishHourIST']
        views = video['video']['viewCount']

        day_performance[day].append(views)
        hour_performance[hour].append(views)

    # Calculate multipliers vs average
    total_avg = np.mean([v['video']['viewCount'] for v in self.videos])

    return {
        'byDayOfWeek': [
            {'day': day, 'multiplier': np.mean(views) / total_avg}
            for day, views in day_performance.items()
        ],
        'byHourIST': [
            {'hour': hour, 'multiplier': np.mean(views) / total_avg}
            for hour, views in hour_performance.items()
        ]
    }
```

### Content Gap Analysis

```python
# src/gaps.py

class GapAnalyzer:
    def find_content_gaps(self):
        """Find underserved topics with high potential."""
        topic_performance = defaultdict(list)

        for video in self.videos:
            niche = video['analysis']['keywords']['niche']
            views = video['video']['viewCount']
            topic_performance[niche].append(views)

        opportunities = []
        for topic, views in topic_performance.items():
            avg_views = np.mean(views)
            video_count = len(views)

            # High opportunity = high views, low competition
            opportunity_score = avg_views / (video_count + 1)

            opportunities.append({
                'topic': topic,
                'avgViews': avg_views,
                'videoCount': video_count,
                'opportunityScore': opportunity_score
            })

        return sorted(opportunities, key=lambda x: x['opportunityScore'], reverse=True)
```

### Insights Output Schema

```python
# Stored in Firestore: insights/thumbnails
{
    "generatedAt": "2024-01-25T10:30:00Z",
    "basedOnVideos": 50000,
    "topPerformingElements": [
        {
            "category": "humanPresence",
            "element": "expression:surprised",
            "lift": 2.6
        }
    ],
    "topCorrelations": [
        {
            "feature": "psychology_curiosityGap",
            "correlation": 0.42,
            "p_value": 0.001
        }
    ]
}

# Stored in Firestore: insights/timing
{
    "bestTimes": {
        "byDayOfWeek": [
            {"day": "Saturday", "avgViews": 125000, "multiplier": 1.4}
        ],
        "byHourIST": [
            {"hour": 18, "avgViews": 130000, "multiplier": 1.46}
        ],
        "optimal": {
            "day": "Saturday",
            "hourIST": 18,
            "multiplier": 1.6
        }
    }
}

# Stored in Firestore: insights/contentGaps
{
    "highOpportunity": [
        {
            "topic": "cooking/indo-chinese",
            "avgViews": 85000,
            "videoCount": 45,
            "opportunityScore": 1847
        }
    ],
    "saturatedTopics": [
        {"topic": "cooking/biryani", "competition": "extreme"}
    ]
}
```

---

## Phase 4: Recommendation Engine

### Overview

The recommender generates actionable suggestions for new videos by:

1. Loading insights from Firestore
2. Building context from patterns
3. Using Gemini to generate recommendations
4. Falling back to templates if AI fails

### Recommendation Flow

```python
# src/engine.py

class RecommendationEngine:
    def generate_recommendation(self, topic, content_type, unique_angle, target_audience):
        # 1. Load insights
        self.insights = get_all_insights()

        # 2. Build context from insights
        context = self._build_context()

        # 3. Generate with Gemini
        try:
            prompt = self._build_prompt(topic, content_type, unique_angle, target_audience, context)
            response = self.model.generate_content(prompt)
            recommendation = json.loads(response.text)
        except:
            # 4. Fallback to templates
            recommendation = self._generate_from_templates(topic, content_type)

        # 5. Add posting recommendation
        recommendation['posting'] = self._get_posting_recommendation()

        return recommendation
```

### Context Building

```python
def _build_context(self):
    context_parts = []

    # Add top thumbnail elements
    if 'thumbnails' in self.insights:
        top_elements = self.insights['thumbnails']['topPerformingElements'][:5]
        context_parts.append("Top performing thumbnail elements:")
        for elem in top_elements:
            context_parts.append(f"  - {elem['element']} ({elem['lift']}x performance)")

    # Add power words
    if 'titles' in self.insights:
        power_words = self.insights['titles']['topPowerWords'][:10]
        context_parts.append("\nTop power words:")
        for pw in power_words:
            context_parts.append(f"  - {pw['word']}")

    # Add optimal timing
    if 'timing' in self.insights:
        optimal = self.insights['timing']['bestTimes']['optimal']
        context_parts.append(f"\nOptimal posting: {optimal['day']} at {optimal['hourIST']}:00 IST")

    return '\n'.join(context_parts)
```

### Template Fallback

When AI generation fails, templates provide basic recommendations:

```python
# src/templates.py

TITLE_TEMPLATES = {
    'recipe': [
        "{dish} Recipe | {dish_telugu} | {modifier}",
        "{modifier} {dish} | {dish_telugu} | Restaurant Style",
        "SECRET {dish} Recipe | {dish_telugu} రహస్యం",
    ],
    'vlog': [
        "My {topic} Experience | {topic_telugu}",
        "A Day in {location} | {topic_telugu}",
    ],
}

THUMBNAIL_SPECS = {
    'recipe': {
        'layout': 'split-composition',
        'face': {'position': 'right-third', 'expression': 'surprised'},
        'food': {'position': 'left-center', 'style': 'close-up with steam'},
        'colors': {'background': '#FF6B35', 'accent': '#FFFF00'}
    }
}

POWER_WORDS = {
    'telugu': ['రహస్యం', 'పర్ఫెక్ట్', 'అసలైన', 'హోటల్ స్టైల్'],
    'english': ['SECRET', 'PERFECT', 'AUTHENTIC', 'Restaurant Style']
}
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
// type = "thumbnail"
{
  analyzedAt: "2024-01-25T10:30:00Z",
  modelUsed: "gemini-2.0-flash",
  analysisVersion: "1.0",

  composition: { ... },
  humanPresence: { ... },
  textElements: { ... },
  colors: { ... },
  food: { ... },
  graphics: { ... },
  psychology: { ... },
  scores: { ... }
}

// type = "title"
{
  analyzedAt: "2024-01-25T10:30:00Z",
  modelUsed: "gemini-2.0-flash",
  analysisVersion: "1.0",
  rawTitle: "Original title text",

  structure: { ... },
  language: { ... },
  hooks: { ... },
  keywords: { ... },
  scores: { ... }
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

#### `insights/{type}`

```javascript
// type = "thumbnails"
{
  generatedAt: "2024-01-25T10:30:00Z",
  basedOnVideos: 50000,
  topPerformingElements: [...],
  topCorrelations: [...]
}

// type = "timing"
{
  generatedAt: "2024-01-25T10:30:00Z",
  bestTimes: {
    byDayOfWeek: [...],
    byHourIST: [...],
    optimal: { day: "Saturday", hourIST: 18 }
  }
}

// type = "contentGaps"
{
  generatedAt: "2024-01-25T10:30:00Z",
  highOpportunity: [...],
  saturatedTopics: [...]
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

**Model**: `gemini-2.0-flash`

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
| Analyzer | 50,000 videos, 4 analysis types | 2-3 days |
| Insights | Aggregation of all data | 10-30 minutes |
| Recommender | Single query | 5-10 seconds |

### Cost Estimates

| Service | Usage | Cost |
|---------|-------|------|
| YouTube API | Free tier | $0 |
| Firebase Firestore | ~200K documents | ~$5-10 |
| Firebase Storage | ~3GB thumbnails | ~$1-2 |
| Gemini API | 50K images + 150K text | ~$300-400 |

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
cd ../recommender
pip install -r requirements.txt
python -m src.main --topic "Biryani" --type recipe
```

### Monitoring Progress

```bash
# Scraper: Check console output for real-time progress
# Also check Firestore: scrape_progress/{channelId}

# Analyzer: Check console with tqdm progress bars
# Also check Firestore: analysis_progress/{type}

# Insights: Output files in insights/outputs/
# Also check Firestore: insights/{type}
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
