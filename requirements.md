# YouTube Intelligence System - Complete Specification

## 🎯 Project Overview

Build a comprehensive YouTube analytics system that:
1. **Scrapes** video data from 100+ Telugu YouTube channels
2. **Analyzes** thumbnails, titles, descriptions, and tags using Claude AI
3. **Discovers** patterns that correlate with high performance
4. **Generates** data-driven recommendations for new video creation

**End Goal:** A system that tells you exactly what title, thumbnail, tags, and posting time to use for maximum views.

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PHASE 1: DATA COLLECTION                          │
│                              (Node.js + YouTube API)                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   channels.json ──► YouTube API ──► Firebase Firestore (raw data)          │
│                          │                                                  │
│                          └──► Firebase Storage (thumbnails)                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PHASE 2: AI ANALYSIS                              │
│                           (Python + Claude API)                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   │
│   │  Thumbnail  │   │    Title    │   │ Description │   │    Tags     │   │
│   │  Analysis   │   │  Analysis   │   │  Analysis   │   │  Analysis   │   │
│   │ (Vision AI) │   │  (Text AI)  │   │  (Text AI)  │   │  (Text AI)  │   │
│   └──────┬──────┘   └──────┬──────┘   └──────┬──────┘   └──────┬──────┘   │
│          │                 │                 │                 │           │
│          └─────────────────┴─────────────────┴─────────────────┘           │
│                                      │                                      │
│                                      ▼                                      │
│                        Firebase Firestore (analysis data)                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        PHASE 3: PATTERN DISCOVERY                           │
│                              (Python + Analytics)                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Cross-Reference Analysis:                                                 │
│   • Thumbnail elements vs View counts                                       │
│   • Title patterns vs Engagement rates                                      │
│   • Tag strategies vs Discovery metrics                                     │
│   • Posting times vs Performance                                            │
│                                                                             │
│                              ▼                                              │
│                    Pattern Database & Insights                              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      PHASE 4: RECOMMENDATION ENGINE                         │
│                              (Python + Claude API)                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Input: "I want to make a biryani video"                                   │
│                                                                             │
│   Output:                                                                   │
│   • Optimal title templates (ranked)                                        │
│   • Thumbnail specification (colors, layout, elements)                      │
│   • Tag list (prioritized)                                                  │
│   • Best posting time                                                       │
│   • Expected performance range                                              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Technical Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Scraper | Node.js 18+ | YouTube API integration |
| YouTube API | YouTube Data API v3 | Video/channel data |
| Database | Firebase Firestore | Structured data storage |
| File Storage | Firebase Storage | Thumbnail images |
| AI Analysis | Claude API (Opus 4.5) | Vision + text analysis |
| Analysis Scripts | Python 3.11+ | Data processing |
| Environment | dotenv | Configuration |

---

## 📁 Project Structure

```
youtube-intelligence/
│
├── package.json                    # Node.js dependencies
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment template
├── .env                            # Actual config (git-ignored)
├── .gitignore
├── README.md
│
├── config/
│   └── channels.json               # Input: YouTube channel URLs
│
├── scraper/                        # PHASE 1: Node.js Scraper
│   ├── package.json
│   ├── src/
│   │   ├── index.js                # Main entry point
│   │   ├── config.js               # Environment validation
│   │   ├── youtube/
│   │   │   ├── client.js           # YouTube API setup
│   │   │   ├── channels.js         # Channel operations
│   │   │   ├── videos.js           # Video operations
│   │   │   └── resolver.js         # URL → Channel ID
│   │   ├── firebase/
│   │   │   ├── client.js           # Firebase Admin setup
│   │   │   ├── firestore.js        # Database operations
│   │   │   └── storage.js          # Thumbnail storage
│   │   ├── scraper/
│   │   │   ├── index.js            # Main scraping logic
│   │   │   ├── progress.js         # Resume capability
│   │   │   └── thumbnail.js        # Image download/upload
│   │   └── utils/
│   │       ├── duration.js         # ISO 8601 parser
│   │       ├── logger.js           # Console output
│   │       └── helpers.js          # Utilities
│   └── scripts/
│       ├── validate.js             # Test connections
│       └── reset-progress.js       # Clear for re-run
│
├── analyzer/                       # PHASE 2: Python AI Analysis
│   ├── requirements.txt
│   ├── src/
│   │   ├── __init__.py
│   │   ├── main.py                 # Main entry point
│   │   ├── config.py               # Configuration
│   │   ├── firebase_client.py      # Firebase connection
│   │   ├── claude_client.py        # Claude API wrapper
│   │   ├── analyzers/
│   │   │   ├── __init__.py
│   │   │   ├── thumbnail.py        # Thumbnail analysis
│   │   │   ├── title.py            # Title analysis
│   │   │   ├── description.py      # Description analysis
│   │   │   └── tags.py             # Tag analysis
│   │   ├── processors/
│   │   │   ├── __init__.py
│   │   │   ├── batch.py            # Batch processing
│   │   │   └── progress.py         # Progress tracking
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── helpers.py
│   └── scripts/
│       ├── run_thumbnail_analysis.py
│       ├── run_title_analysis.py
│       ├── run_description_analysis.py
│       └── run_tag_analysis.py
│
├── insights/                       # PHASE 3: Pattern Discovery
│   ├── requirements.txt
│   ├── src/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── correlations.py         # Statistical analysis
│   │   ├── patterns.py             # Pattern extraction
│   │   ├── gaps.py                 # Content gap analysis
│   │   └── reports.py              # Generate reports
│   └── outputs/
│       └── (generated reports)
│
└── recommender/                    # PHASE 4: Recommendations
    ├── requirements.txt
    ├── src/
    │   ├── __init__.py
    │   ├── main.py
    │   ├── engine.py               # Recommendation logic
    │   ├── templates.py            # Title/thumbnail templates
    │   └── api.py                  # Optional: REST API
    └── examples/
        └── sample_queries.json
```

---

# PHASE 1: YOUTUBE SCRAPER

## Environment Variables

### .env.example
```bash
# ============================================
# YOUTUBE API
# ============================================
# Get from: https://console.cloud.google.com/apis/credentials
YOUTUBE_API_KEY=your_youtube_api_key_here

# ============================================
# FIREBASE
# ============================================
# Get from: Firebase Console > Project Settings > Service Accounts
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_CLIENT_EMAIL=firebase-adminsdk-xxxxx@your-project-id.iam.gserviceaccount.com
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nYourKeyHere\n-----END PRIVATE KEY-----\n"
FIREBASE_STORAGE_BUCKET=your-project-id.appspot.com

# ============================================
# CLAUDE API (for Phase 2)
# ============================================
# Get from: https://console.anthropic.com/
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxx

# ============================================
# SCRAPER SETTINGS
# ============================================
API_DELAY_MS=100
QUOTA_WARNING_THRESHOLD=500
THUMBNAIL_QUALITY=mqdefault
```

---

## Input Format

### config/channels.json
```json
{
  "channels": [
    {
      "url": "https://www.youtube.com/@VismaiFood",
      "category": "cooking",
      "priority": 1
    },
    {
      "url": "https://www.youtube.com/@MyVillageShow",
      "category": "entertainment",
      "priority": 1
    },
    {
      "url": "https://www.youtube.com/@UmaTeluguTraveller",
      "category": "travel",
      "priority": 1
    },
    {
      "url": "https://www.youtube.com/@VahchefVahrehvahTelugu",
      "category": "cooking",
      "priority": 2
    },
    {
      "url": "https://www.youtube.com/@AmericaloGunturAmmayi",
      "category": "nri-lifestyle",
      "priority": 1
    }
  ],
  "settings": {
    "maxVideosPerChannel": null,
    "includeShorts": true,
    "includePrivate": false
  }
}
```

### Supported URL Formats
```
https://www.youtube.com/@handle
https://www.youtube.com/channel/UCxxxxxxxxxxxxxxxxxxxxxx
https://www.youtube.com/c/customname
https://www.youtube.com/user/username
```

---

## Firebase Data Schema

### Collection: `channels/{channelId}`

```javascript
{
  // ===== IDENTIFIERS =====
  channelId: "UCBSwcE0p0PMwhvE6FVjgITw",
  
  // ===== BASIC INFO =====
  channelTitle: "Vismai Food",
  channelDescription: "Vismai Food Is a Telugu Language-Based Cookery Channel...",
  customUrl: "@VismaiFood",
  
  // ===== STATISTICS =====
  subscriberCount: 4930000,
  videoCount: 2200,
  viewCount: 1250000000,
  
  // ===== IMAGES =====
  thumbnailUrl: "https://yt3.ggpht.com/...",
  thumbnailStoragePath: "channel_thumbnails/UCBSwcE0p0PMwhvE6FVjgITw.jpg",
  bannerUrl: "https://yt3.googleusercontent.com/...",
  
  // ===== METADATA =====
  country: "IN",
  publishedAt: Timestamp,
  
  // ===== CATEGORIZATION =====
  category: "cooking",
  priority: 1,
  
  // ===== SCRAPING INFO =====
  sourceUrl: "https://www.youtube.com/@VismaiFood",
  scrapedAt: Timestamp,
  lastUpdatedAt: Timestamp,
  
  // ===== CALCULATED (Phase 3) =====
  avgViewsPerVideo: 568182,
  avgEngagementRate: 4.2,
  uploadFrequency: "3 per week"
}
```

### Collection: `channels/{channelId}/videos/{videoId}`

```javascript
{
  // ===== IDENTIFIERS =====
  videoId: "dQw4w9WgXcQ",
  channelId: "UCBSwcE0p0PMwhvE6FVjgITw",
  
  // ===== BASIC INFO (from YouTube API) =====
  title: "Veg Manchurian Recipe | వెజ్ మంచూరియా | Restaurant Style",
  description: "Full recipe description here...",
  publishedAt: Timestamp,
  
  // ===== THUMBNAILS =====
  thumbnails: {
    default: "https://img.youtube.com/vi/xxx/default.jpg",
    medium: "https://img.youtube.com/vi/xxx/mqdefault.jpg",
    high: "https://img.youtube.com/vi/xxx/hqdefault.jpg",
    standard: "https://img.youtube.com/vi/xxx/sddefault.jpg",
    maxres: "https://img.youtube.com/vi/xxx/maxresdefault.jpg"
  },
  thumbnailStoragePath: "thumbnails/UCBSwcE0p0PMwhvE6FVjgITw/dQw4w9WgXcQ.jpg",
  
  // ===== DURATION =====
  duration: "PT15M33S",
  durationSeconds: 933,
  
  // ===== STATISTICS =====
  viewCount: 16000000,
  likeCount: 450000,
  commentCount: 12000,
  
  // ===== TAGS =====
  tags: [
    "veg manchurian",
    "manchurian recipe", 
    "telugu cooking",
    "vismai food",
    "restaurant style manchurian",
    "వెజ్ మంచూరియా"
  ],
  
  // ===== METADATA =====
  categoryId: "26",
  categoryName: "Howto & Style",
  defaultLanguage: "te",
  defaultAudioLanguage: "te",
  madeForKids: false,
  
  // ===== CONTENT DETAILS =====
  definition: "hd",
  caption: true,
  licensedContent: false,
  
  // ===== TOPIC DETAILS =====
  topicCategories: [
    "https://en.wikipedia.org/wiki/Food",
    "https://en.wikipedia.org/wiki/Cooking"
  ],
  
  // ===== DERIVED FIELDS =====
  isShort: false,
  videoUrl: "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  
  // ===== SCRAPING INFO =====
  scrapedAt: Timestamp,
  
  // ===== CALCULATED METRICS (computed after scrape) =====
  calculated: {
    engagementRate: 2.89,           // (likes + comments) / views * 100
    likeRatio: 2.81,                // likes / views * 100
    commentRatio: 0.075,            // comments / views * 100
    viewsPerSubscriber: 3.25,       // views / channel_subs
    daysSincePublish: 365,
    viewsPerDay: 43836,
    performancePercentile: 95,      // rank within channel
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

### Collection: `scrape_progress/{channelId}`

```javascript
{
  // ===== IDENTIFIERS =====
  channelId: "UCBSwcE0p0PMwhvE6FVjgITw",
  channelTitle: "Vismai Food",
  sourceUrl: "https://www.youtube.com/@VismaiFood",
  
  // ===== STATUS =====
  status: "in_progress",  // "pending" | "in_progress" | "completed" | "failed"
  
  // ===== PROGRESS =====
  phase: "scraping",  // "scraping" | "thumbnails" | "calculations"
  totalVideos: 2200,
  videosProcessed: 1547,
  thumbnailsDownloaded: 1547,
  
  // ===== RESUME POINT =====
  lastProcessedVideoId: "abc123xyz",
  lastPlaylistPageToken: "CGQQAA",
  
  // ===== TIMESTAMPS =====
  startedAt: Timestamp,
  lastProcessedAt: Timestamp,
  completedAt: Timestamp,
  
  // ===== ERROR INFO =====
  errorMessage: null,
  errorStack: null,
  retryCount: 0
}
```

### Firebase Storage Structure

```
{bucket}/
├── channel_thumbnails/
│   ├── UCBSwcE0p0PMwhvE6FVjgITw.jpg
│   └── ...
│
└── thumbnails/
    ├── UCBSwcE0p0PMwhvE6FVjgITw/
    │   ├── video1.jpg
    │   ├── video2.jpg
    │   └── ...
    └── ...
```

---

## YouTube API Quota Management

### Quota Costs

| Operation | Units | Notes |
|-----------|-------|-------|
| `channels.list` | 1 | Get channel details |
| `search.list` | 100 | Resolve @handle (avoid!) |
| `playlistItems.list` | 1 | List videos (50/page) |
| `videos.list` | 1 | Video details (50/request) |

### Daily Quota: 10,000 units

### Estimation for 100 Channels (avg 500 videos each)

```
Per channel:
  - Resolve URL: 1-100 units (1 if direct, 100 if search)
  - Channel info: 1 unit
  - List videos: 10 pages × 1 = 10 units
  - Video details: 10 batches × 1 = 10 units
  - Total: ~22-120 units per channel

For 100 channels: ~2,200 - 12,000 units
Realistic estimate: ~5,000-7,000 units (multiple days needed)
```

### Quota Strategy

1. Track usage in memory
2. Save progress after each video batch
3. Stop at 500 units remaining
4. Display "Run again tomorrow" message
5. Resume from last position

---

## Scraper Core Logic

### 1. Channel URL Resolution

```javascript
// Handle all URL formats:
// @handle → channels.list with forHandle
// /channel/UCxxx → direct use
// /c/name → search.list (expensive) or try forHandle
// /user/name → channels.list with forUsername

async function resolveChannelUrl(url) {
  const patterns = {
    handle: /@([^\/\?]+)/,
    channelId: /\/channel\/(UC[a-zA-Z0-9_-]{22})/,
    customUrl: /\/c\/([^\/\?]+)/,
    user: /\/user\/([^\/\?]+)/
  };
  
  // Try each pattern and resolve
  // Return: { channelId, resolvedFrom, quotaCost }
}
```

### 2. Fetch All Videos

```javascript
async function getAllChannelVideos(channelId, resumeToken = null) {
  // Get uploads playlist (UC → UU)
  const uploadsPlaylistId = 'UU' + channelId.substring(2);
  
  // Paginate through all videos
  // Handle resumeToken for continuation
  // Return: { videoIds: [], nextPageToken, totalResults }
}
```

### 3. Batch Video Details

```javascript
async function getVideoDetailsBatch(videoIds) {
  // Batch into groups of 50
  // Request: snippet, contentDetails, statistics, topicDetails
  // Parse and transform data
  // Return: Video objects matching schema
}
```

### 4. Download & Upload Thumbnails

```javascript
async function processThumbnail(videoId, channelId) {
  const url = `https://img.youtube.com/vi/${videoId}/mqdefault.jpg`;
  
  // Download with axios (stream)
  // Upload to Firebase Storage
  // Return: storage path
  
  // Retry 3x with exponential backoff on failure
}
```

### 5. Calculate Derived Metrics

```javascript
function calculateMetrics(video, channel) {
  return {
    engagementRate: ((video.likeCount + video.commentCount) / video.viewCount) * 100,
    likeRatio: (video.likeCount / video.viewCount) * 100,
    commentRatio: (video.commentCount / video.viewCount) * 100,
    viewsPerSubscriber: video.viewCount / channel.subscriberCount,
    daysSincePublish: daysBetween(video.publishedAt, now()),
    viewsPerDay: video.viewCount / daysSincePublish,
    publishDayOfWeek: getDayOfWeek(video.publishedAt),
    publishHourIST: getHourIST(video.publishedAt),
    // ... more calculations
  };
}
```

---

## CLI Output Format

```
================================================================================
                     YOUTUBE INTELLIGENCE SYSTEM v1.0
                           Phase 1: Data Collection
================================================================================

[2024-01-25 10:30:15] 🚀 Starting scraper...
[2024-01-25 10:30:15] 📁 Loaded 100 channels from config/channels.json
[2024-01-25 10:30:16] 🔗 Connected to Firebase: youtube-intel-12345
[2024-01-25 10:30:16] 📊 API Quota: 10,000 units available

[2024-01-25 10:30:17] 📋 Progress Status:
                      ✅ Completed: 23 channels (11,247 videos)
                      🔄 In Progress: 1 channel
                      ⏳ Pending: 76 channels

================================================================================

[2024-01-25 10:30:18] 📺 Processing [24/100]: Vismai Food
                      URL: https://www.youtube.com/@VismaiFood
                      Resuming from video 1,547...
--------------------------------------------------------------------------------
[2024-01-25 10:30:20] 📹 Videos: 1,600/2,200 (72.7%) | 🖼️ Thumbnails: 1,600
[2024-01-25 10:30:22] 📹 Videos: 1,650/2,200 (75.0%) | 🖼️ Thumbnails: 1,650
[2024-01-25 10:30:24] 📹 Videos: 1,700/2,200 (77.3%) | 🖼️ Thumbnails: 1,700
...
[2024-01-25 10:32:45] ✅ Completed: Vismai Food
                      📹 2,200 videos | 🖼️ 2,200 thumbnails | ⏱️ 2m 27s
                      📊 Quota used: 47 units | Remaining: 8,453

================================================================================

[2024-01-25 14:30:00] ⚠️  API QUOTA WARNING
                      Used: 9,523 / 10,000 units (95.2%)
                      Saving progress...

[2024-01-25 14:30:01] 💾 Progress saved successfully

================================================================================
                              SESSION SUMMARY
================================================================================

Duration:           4h 0m 1s
Channels:           45/100 completed (45%)
Videos scraped:     28,450
Thumbnails:         28,391 (59 failed)
API quota used:     9,523 / 10,000

Storage used:       ~2.8 GB (thumbnails)
Firestore writes:   ~85,000 documents

Next steps:
  • Quota resets at midnight Pacific Time
  • Run again: npm start
  • After completion, run Phase 2: python analyzer/src/main.py

================================================================================
```

---

# PHASE 2: AI ANALYSIS

## Overview

After scraping completes, analyze all data using Claude API:

| Analysis Type | Input | AI Model | Output |
|---------------|-------|----------|--------|
| Thumbnail | Image file | Claude Vision (Opus 4.5) | 50+ attributes |
| Title | Text string | Claude Text | 40+ attributes |
| Description | Text string | Claude Text | 30+ attributes |
| Tags | Array of strings | Claude Text | 20+ attributes |

---

## Thumbnail Analysis Schema

### Collection: `channels/{channelId}/videos/{videoId}/analysis/thumbnail`

```javascript
{
  // ===== ANALYSIS METADATA =====
  analyzedAt: Timestamp,
  modelUsed: "claude-opus-4-5-20250514",
  analysisVersion: "1.0",
  
  // ===== COMPOSITION =====
  composition: {
    layoutType: "split-screen",  // "split-screen" | "single-focus" | "collage" | "text-heavy" | "minimal"
    gridStructure: "rule-of-thirds",  // "rule-of-thirds" | "centered" | "asymmetric" | "golden-ratio"
    visualBalance: "left-heavy",  // "balanced" | "left-heavy" | "right-heavy" | "top-heavy" | "bottom-heavy"
    negativeSpace: "minimal",  // "minimal" | "moderate" | "heavy"
    complexity: "medium",  // "simple" | "medium" | "complex" | "cluttered"
    focalPoint: "food-center",  // description of main focal point
    depthOfField: "shallow"  // "shallow" | "deep" | "flat"
  },
  
  // ===== HUMAN PRESENCE =====
  humanPresence: {
    facePresent: true,
    faceCount: 1,
    facePosition: "right-third",  // position in frame
    faceSize: "large",  // "small" | "medium" | "large" | "dominant"
    faceCoverage: 25,  // percentage of frame
    expression: "surprised",  // "happy" | "surprised" | "shocked" | "curious" | "neutral" | "excited" | "disgusted" | "thinking"
    expressionIntensity: "high",  // "subtle" | "moderate" | "high" | "extreme"
    mouthOpen: true,
    eyeContact: true,  // looking at camera
    eyebrowsRaised: true,
    
    // Body language
    bodyVisible: true,
    bodyPortion: "upper",  // "face-only" | "upper" | "half" | "full"
    handVisible: true,
    handGesture: "pointing",  // "none" | "thumbs-up" | "pointing" | "holding-item" | "peace" | "ok"
    pointingAt: "food",  // what they're pointing at
    
    // Presentation
    lookingDirection: "camera",  // "camera" | "left" | "right" | "down" | "at-food"
    professionalAttire: false,
    apronVisible: true,
    
    // Multiple people
    multiplePeople: false,
    peopleInteraction: null  // "talking" | "reacting" | "competing" | null
  },
  
  // ===== TEXT ANALYSIS =====
  textElements: {
    hasText: true,
    textCount: 3,  // number of distinct text elements
    
    // Primary text
    primaryText: {
      content: "16M VIEWS",
      language: "english",
      script: "latin",
      position: "top-left",
      size: "large",
      color: "#FFFF00",
      backgroundColor: "#FF0000",
      hasOutline: true,
      outlineColor: "#000000",
      fontStyle: "bold-sans",  // "bold-sans" | "script" | "handwritten" | "decorative"
      allCaps: true,
      readable: true,
      readabilityScore: 9  // 1-10
    },
    
    // Secondary text (if present)
    secondaryText: {
      content: "వెజ్ మంచూరియా",
      language: "telugu",
      script: "telugu",
      position: "center",
      size: "medium",
      color: "#FFFFFF"
    },
    
    // Text analysis
    languages: ["english", "telugu"],
    hasTeluguScript: true,
    hasEnglishText: true,
    hasNumbers: true,
    numberValue: "16M",
    numberType: "view-count",  // "view-count" | "list-number" | "price" | "time" | "quantity"
    hasEmoji: false,
    emojiList: [],
    
    // Text purpose
    textPurpose: ["social-proof", "dish-name"],  // "title" | "social-proof" | "cta" | "brand" | "dish-name" | "benefit"
    
    // Overall text assessment
    textClarity: "high",  // "low" | "medium" | "high"
    textHierarchy: "clear",  // "clear" | "confused" | "none"
    totalTextCoverage: 15  // percentage of frame
  },
  
  // ===== COLOR ANALYSIS =====
  colors: {
    // Dominant colors (top 5)
    dominantColors: [
      { hex: "#FF6B35", name: "orange", percentage: 35 },
      { hex: "#FFFFFF", name: "white", percentage: 25 },
      { hex: "#FFD700", name: "yellow", percentage: 20 },
      { hex: "#1A1A1A", name: "black", percentage: 15 },
      { hex: "#2E8B57", name: "green", percentage: 5 }
    ],
    
    // Color properties
    palette: "warm",  // "warm" | "cool" | "neutral" | "mixed"
    mood: "energetic",  // "energetic" | "calm" | "appetizing" | "professional" | "playful"
    contrast: "high",  // "low" | "medium" | "high"
    saturation: "high",  // "desaturated" | "medium" | "high" | "vivid"
    brightness: "bright",  // "dark" | "medium" | "bright"
    
    // Background
    backgroundType: "gradient",  // "solid" | "gradient" | "image" | "blurred" | "transparent"
    backgroundColor: "#FF6B35",
    backgroundSecondary: "#FFD700",
    
    // Color harmony
    colorHarmony: "complementary",  // "monochromatic" | "complementary" | "triadic" | "analogous"
    
    // YouTube-specific
    contrastWithYouTube: true,  // stands out in feed
    redAvoidance: true  // avoids YouTube red
  },
  
  // ===== FOOD ANALYSIS (for food/cooking channels) =====
  food: {
    foodPresent: true,
    foodCount: 1,
    mainDish: "manchurian",
    dishCategory: "indo-chinese",  // "rice" | "curry" | "snack" | "dessert" | "bread" | "indo-chinese" | "breakfast"
    cuisineType: "indian-fusion",
    
    // Presentation
    presentation: "close-up",  // "close-up" | "plated" | "cooking-process" | "ingredients" | "before-after"
    platingStyle: "rustic",  // "rustic" | "elegant" | "home-style" | "restaurant"
    container: "bowl",  // "plate" | "bowl" | "pot" | "pan" | "banana-leaf" | "hand"
    
    // Visual appeal
    steam: true,
    sizzle: false,
    garnished: true,
    garnishes: ["spring-onion", "sesame"],
    sauce: true,
    sauceType: "gravy",
    
    // Ingredients visible
    ingredientsVisible: true,
    visibleIngredients: ["vegetables", "sauce", "garnish"],
    
    // Quality indicators
    freshness: "high",  // "low" | "medium" | "high"
    appetiteAppeal: 9,  // 1-10 how appetizing
    colorVibrancy: "high",
    textureVisible: true,
    
    // Portion
    portionSize: "generous",  // "small" | "medium" | "generous" | "huge"
    
    // Cooking stage
    cookingStage: "finished"  // "raw" | "in-progress" | "finished"
  },
  
  // ===== GRAPHIC ELEMENTS =====
  graphics: {
    // Arrows
    hasArrows: true,
    arrowCount: 1,
    arrowColor: "#FF0000",
    arrowStyle: "curved",  // "straight" | "curved" | "hand-drawn"
    arrowPointingTo: "food",
    
    // Circles/Highlights
    hasCircles: false,
    hasHighlights: true,
    highlightColor: "#FFFF00",
    
    // Borders
    hasBorder: true,
    borderColor: "#FFFFFF",
    borderWidth: "thick",
    borderStyle: "solid",  // "solid" | "dashed" | "glow" | "shadow"
    
    // Badges/Labels
    hasBadge: true,
    badgeType: "view-count",  // "new" | "viral" | "view-count" | "trending" | "episode-number"
    badgeText: "16M VIEWS",
    badgePosition: "top-left",
    badgeColor: "#FF0000",
    
    // Other elements
    hasLogo: true,
    logoPosition: "bottom-right",
    logoSize: "small",
    hasWatermark: false,
    hasPlayButton: false,
    
    // Comparison elements
    hasBeforeAfter: false,
    hasVsComparison: false,
    hasSplitScreen: false,
    
    // Icons/Emojis
    hasIcons: false,
    iconTypes: [],
    
    // Effects
    hasGlow: false,
    hasShadow: true,
    hasReflection: false
  },
  
  // ===== BRANDING =====
  branding: {
    channelLogoVisible: true,
    logoPlacement: "corner",
    channelNameVisible: false,
    consistentWithChannel: true,  // matches channel's usual style
    recognizableStyle: true,  // can identify channel from thumbnail
    brandColors: ["#FF6B35", "#FFFFFF"],
    templateUsed: true,  // appears to use a template
    professionalQuality: "high"  // "amateur" | "medium" | "high" | "professional"
  },
  
  // ===== PSYCHOLOGICAL TRIGGERS =====
  psychology: {
    // Trigger types
    curiosityGap: true,  // makes you want to know more
    socialProof: true,   // shows popularity/credibility
    urgency: false,      // creates FOMO
    scarcity: false,     // limited availability
    authority: false,    // expert positioning
    controversy: false,  // divisive/debatable
    transformation: false,  // before/after promise
    luxury: false,       // aspirational/premium
    nostalgia: true,     // traditional/heritage
    shock: false,        // unexpected/surprising
    humor: false,        // funny element
    fear: false,         // warning/danger
    
    // Emotional response
    primaryEmotion: "appetite",  // "curiosity" | "excitement" | "appetite" | "nostalgia" | "amusement"
    emotionalIntensity: "high",
    
    // Click motivation
    clickMotivation: ["learn-recipe", "see-result"],  // why someone would click
    targetAudience: "home-cooks"
  },
  
  // ===== TECHNICAL QUALITY =====
  technicalQuality: {
    resolution: "high",  // "low" | "medium" | "high"
    sharpness: "sharp",  // "blurry" | "acceptable" | "sharp"
    lighting: "professional",  // "poor" | "natural" | "professional" | "studio"
    noiseLevel: "low",
    compression: "minimal",
    aspectRatio: "16:9",
    
    // Composition quality
    framing: "good",
    focus: "sharp",
    exposure: "correct"
  },
  
  // ===== OVERALL SCORES =====
  scores: {
    clickability: 8.5,        // 1-10 likelihood to click
    clarity: 9.0,             // 1-10 clear message
    professionalism: 7.5,     // 1-10 production quality
    uniqueness: 6.0,          // 1-10 stands out
    brandConsistency: 8.0,    // 1-10 matches channel
    appetiteAppeal: 9.0,      // 1-10 (for food content)
    emotionalImpact: 7.5,     // 1-10 emotional response
    
    // Predicted performance
    predictedCTR: "above-average",  // "below-average" | "average" | "above-average" | "exceptional"
    
    // Improvement suggestions
    improvementAreas: [
      "Add more contrast to text",
      "Consider showing face expression more clearly"
    ]
  }
}
```

---

## Title Analysis Schema

### Collection: `channels/{channelId}/videos/{videoId}/analysis/title`

```javascript
{
  // ===== ANALYSIS METADATA =====
  analyzedAt: Timestamp,
  modelUsed: "claude-opus-4-5-20250514",
  analysisVersion: "1.0",
  rawTitle: "Veg Manchurian Recipe | వెజ్ మంచూరియా | Restaurant Style | Vismai Food",
  
  // ===== STRUCTURE =====
  structure: {
    // Pattern detection
    pattern: "dish-name | translation | modifier | channel",
    patternType: "segmented",  // "single" | "segmented" | "question" | "list" | "statement"
    
    // Segments
    segments: [
      { text: "Veg Manchurian Recipe", type: "dish-name", language: "english" },
      { text: "వెజ్ మంచూరియా", type: "translation", language: "telugu" },
      { text: "Restaurant Style", type: "modifier", language: "english" },
      { text: "Vismai Food", type: "channel-name", language: "english" }
    ],
    segmentCount: 4,
    
    // Separators
    separator: "|",
    separatorConsistent: true,
    
    // Length metrics
    characterCount: 67,
    characterCountNoSpaces: 58,
    wordCount: 9,
    teluguCharacterCount: 12,
    englishCharacterCount: 46
  },
  
  // ===== LANGUAGE =====
  language: {
    // Languages present
    languages: ["english", "telugu"],
    primaryLanguage: "english",
    secondaryLanguage: "telugu",
    
    // Script analysis
    scripts: ["latin", "telugu"],
    hasTeluguScript: true,
    hasLatinScript: true,
    
    // Transliteration
    hasTransliteration: false,  // Telugu words in English letters
    transliteratedWords: [],
    
    // Code switching
    codeSwitch: true,  // mixes languages
    codeSwitchStyle: "translation",  // "translation" | "mixed" | "parallel"
    
    // Telugu analysis
    teluguWords: ["వెజ్", "మంచూరియా"],
    teluguWordCount: 2,
    teluguReadability: "easy",  // "easy" | "medium" | "difficult"
    
    // English analysis
    englishWords: ["Veg", "Manchurian", "Recipe", "Restaurant", "Style", "Vismai", "Food"],
    englishWordCount: 7,
    
    // Language ratio
    teluguRatio: 0.18,  // percentage of title in Telugu
    englishRatio: 0.69,
    otherRatio: 0.13  // separators, etc.
  },
  
  // ===== HOOKS & TRIGGERS =====
  hooks: {
    // Question hooks
    isQuestion: false,
    questionType: null,  // "how" | "why" | "what" | "which" | "can" | "should"
    questionWord: null,
    
    // Number hooks
    hasNumber: false,
    numbers: [],
    numberContext: null,  // "list" | "time" | "money" | "quantity" | "ranking" | "year"
    
    // Power words - Positive
    hasPowerWord: true,
    powerWords: ["Restaurant Style"],
    powerWordCategories: ["quality"],
    
    // Power word categories detected
    exclusivityWords: [],      // "secret", "hidden", "exclusive"
    urgencyWords: [],          // "now", "today", "limited"
    curiosityWords: [],        // "revealed", "truth", "actually"
    qualityWords: ["Restaurant Style"],  // "perfect", "best", "authentic"
    emotionWords: [],          // "amazing", "incredible", "shocking"
    
    // Telugu power words
    teluguPowerWords: [],
    teluguPowerWordMeanings: [],
    
    // Emotional triggers
    triggers: {
      curiosityGap: false,     // incomplete information
      socialProof: false,      // popularity indicators
      urgency: false,          // time pressure
      exclusivity: false,      // special/secret
      controversy: false,      // debatable topic
      transformation: false,   // before/after
      challenge: false,        // difficulty/competition
      comparison: false,       // vs, better than
      personal: false,         // my, our, your
      storytelling: false      // journey, story, experience
    },
    
    // Hook strength
    hookStrength: "moderate",  // "weak" | "moderate" | "strong" | "viral"
    primaryHook: "quality-promise"  // main reason to click
  },
  
  // ===== KEYWORDS =====
  keywords: {
    // Primary keyword
    primaryKeyword: "Veg Manchurian Recipe",
    primaryKeywordPosition: "start",  // "start" | "middle" | "end"
    
    // Secondary keywords
    secondaryKeywords: ["Restaurant Style", "వెజ్ మంచూరియా"],
    
    // All keywords extracted
    allKeywords: [
      { word: "veg manchurian", type: "dish", searchVolume: "high" },
      { word: "manchurian recipe", type: "recipe", searchVolume: "high" },
      { word: "restaurant style", type: "modifier", searchVolume: "medium" },
      { word: "vismai food", type: "brand", searchVolume: "medium" }
    ],
    
    // Search intent
    searchIntent: "how-to",  // "how-to" | "review" | "comparison" | "information" | "entertainment"
    
    // Niche classification
    niche: "cooking",
    subNiche: "indian-chinese",
    microNiche: "vegetarian-starters",
    
    // Trend analysis
    evergreen: true,  // always relevant
    seasonal: false,
    trendingPotential: "medium",
    
    // Competition
    keywordCompetition: "high",  // "low" | "medium" | "high" | "extreme"
    
    // SEO assessment
    seoOptimized: true,
    keywordInFirst3Words: true,
    naturalLanguage: true  // vs keyword stuffed
  },
  
  // ===== FORMATTING =====
  formatting: {
    // Capitalization
    capitalization: "title-case",  // "lowercase" | "title-case" | "all-caps" | "mixed"
    allCaps: false,
    partialCaps: false,
    capsWords: [],
    
    // Special characters
    hasEmoji: false,
    emojiList: [],
    emojiPositions: [],
    
    hasBrackets: false,
    bracketType: null,  // "round" | "square" | "curly"
    bracketContent: null,
    
    hasSpecialChars: true,
    specialChars: ["|"],
    
    // Year/Date
    hasYear: false,
    year: null,
    
    // Hashtags
    hasHashtag: false,
    hashtags: [],
    
    // Punctuation
    endsWithPunctuation: false,
    punctuationType: null,
    hasExclamation: false,
    hasQuestion: false
  },
  
  // ===== CONTENT SIGNALS =====
  contentSignals: {
    // Content type
    contentType: "recipe",
    
    // Format indicators
    isRecipe: true,
    isTutorial: true,
    isReview: false,
    isVlog: false,
    isChallenge: false,
    isReaction: false,
    isComparison: false,
    isList: false,
    isStorytime: false,
    isUnboxing: false,
    isExplainer: false,
    isNews: false,
    
    // Series indicators
    isPartOfSeries: false,
    seriesName: null,
    episodeNumber: null,
    
    // Collaboration
    hasCollaboration: false,
    collaboratorMentioned: null,
    
    // Brand mention
    hasBrandMention: true,
    brandMentioned: "Vismai Food",
    brandPosition: "end"
  },
  
  // ===== TELUGU-SPECIFIC =====
  teluguAnalysis: {
    // Register
    formalRegister: false,  // formal vs casual
    respectLevel: "neutral",  // "casual" | "neutral" | "respectful"
    
    // Dialect
    dialectHints: "neutral",  // "andhra" | "telangana" | "rayalaseema" | "neutral"
    
    // Honorifics
    hasHonorifics: false,
    honorificsUsed: [],
    
    // Colloquialisms
    hasColloquialisms: false,
    colloquialWords: [],
    
    // Food terminology
    foodTermsAccurate: true,
    traditionalTerms: [],
    modernTerms: ["మంచూరియా"],
    
    // Audience targeting
    targetAudienceAge: "all",  // "young" | "middle" | "older" | "all"
    urbanVsRural: "urban"  // "urban" | "rural" | "both"
  },
  
  // ===== COMPETITIVE ANALYSIS =====
  competitive: {
    // Uniqueness
    uniquenessScore: 5,  // 1-10 vs similar titles
    
    // Similar titles pattern
    followsNichePattern: true,
    deviatesFrom: [],
    
    // Differentiation
    uniqueElements: ["Restaurant Style"],
    missingCommonElements: ["time duration", "easy/simple"],
    
    // Click competition
    standoutFactor: "quality-promise"
  },
  
  // ===== OPTIMIZATION SCORES =====
  scores: {
    // Individual scores (1-10)
    seoScore: 8.5,
    clickabilityScore: 7.0,
    clarityScore: 9.0,
    emotionalScore: 5.0,
    uniquenessScore: 5.0,
    lengthScore: 8.0,  // optimal length
    
    // Clickbait assessment
    clickbaitLevel: 2,  // 1-10 (10 = extreme clickbait)
    clickbaitElements: [],
    
    // Overall
    overallScore: 7.5,
    
    // Predicted performance
    predictedPerformance: "above-average",
    
    // Improvement suggestions
    suggestions: [
      "Consider adding a time indicator (e.g., '10 Min')",
      "Could add curiosity element",
      "Telugu title portion could be expanded"
    ]
  }
}
```

---

## Description Analysis Schema

### Collection: `channels/{channelId}/videos/{videoId}/analysis/description`

```javascript
{
  // ===== ANALYSIS METADATA =====
  analyzedAt: Timestamp,
  modelUsed: "claude-opus-4-5-20250514",
  analysisVersion: "1.0",
  
  // ===== STRUCTURE =====
  structure: {
    totalLength: 2450,
    lineCount: 45,
    paragraphCount: 8,
    
    // Sections detected
    hasSections: true,
    sections: [
      { name: "intro", startLine: 1, endLine: 3 },
      { name: "ingredients", startLine: 5, endLine: 20 },
      { name: "timestamps", startLine: 22, endLine: 35 },
      { name: "social-links", startLine: 37, endLine: 42 },
      { name: "hashtags", startLine: 44, endLine: 45 }
    ],
    
    // Organization
    wellOrganized: true,
    usesBulletPoints: true,
    usesNumberedLists: true,
    usesEmojis: true,
    
    // First line analysis (most important)
    firstLine: "Learn the authentic Hyderabadi Biryani recipe that tastes exactly like restaurant!",
    firstLineHook: true,
    first100Chars: "Learn the authentic..."
  },
  
  // ===== TIMESTAMPS =====
  timestamps: {
    hasTimestamps: true,
    timestampCount: 12,
    timestamps: [
      { time: "0:00", seconds: 0, label: "Intro" },
      { time: "0:45", seconds: 45, label: "Ingredients Overview" },
      { time: "1:30", seconds: 90, label: "Marination" },
      { time: "3:45", seconds: 225, label: "Rice Preparation" },
      { time: "6:00", seconds: 360, label: "Layering" },
      { time: "8:30", seconds: 510, label: "Dum Process" },
      { time: "11:00", seconds: 660, label: "Final Result" },
      { time: "12:30", seconds: 750, label: "Serving Suggestions" }
    ],
    timestampFormat: "m:ss",
    chaptersEnabled: true  // YouTube chapters likely enabled
  },
  
  // ===== RECIPE CONTENT (for cooking videos) =====
  recipeContent: {
    hasIngredients: true,
    ingredientCount: 18,
    ingredients: [
      { item: "Basmati Rice", quantity: "2 cups", category: "grain" },
      { item: "Chicken", quantity: "500g", category: "protein" },
      { item: "Yogurt", quantity: "1 cup", category: "dairy" }
      // ... more
    ],
    
    hasInstructions: true,
    instructionSteps: 12,
    
    hasServingSize: true,
    servingSize: "4-5 people",
    
    hasCookingTime: true,
    prepTime: "20 mins",
    cookTime: "45 mins",
    totalTime: "1 hour 5 mins",
    
    hasTips: true,
    tipCount: 5,
    
    hasNutrition: false
  },
  
  // ===== LINKS =====
  links: {
    hasLinks: true,
    linkCount: 8,
    
    // Social media
    socialMedia: {
      instagram: { present: true, url: "https://instagram.com/vismaifood" },
      facebook: { present: true, url: "https://facebook.com/vismaifood" },
      twitter: { present: false, url: null },
      telegram: { present: true, url: "https://t.me/vismaifood" }
    },
    
    // YouTube links
    otherVideos: true,
    otherVideoCount: 3,
    playlistLinks: true,
    channelLink: true,
    
    // External links
    websiteLink: true,
    websiteUrl: "https://vismaifood.com",
    affiliateLinks: false,
    amazonLinks: false,
    merchandiseLink: false,
    
    // Business
    businessEmail: true,
    email: "business@vismaifood.com"
  },
  
  // ===== HASHTAGS =====
  hashtags: {
    hasHashtags: true,
    hashtagCount: 15,
    hashtags: [
      "#biryani",
      "#hyderabadibiryani",
      "#chickenbiryani",
      "#vismaifood",
      "#telugurecipe",
      "#telugufood",
      "#indiancooking",
      "#recipe",
      "#cooking",
      "#food",
      "#foodie",
      "#homemade",
      "#spicy",
      "#dumbiryani",
      "#biryanirecipe"
    ],
    hashtagPosition: "end",  // "start" | "middle" | "end" | "throughout"
    
    // Hashtag analysis
    brandHashtags: ["#vismaifood"],
    topicHashtags: ["#biryani", "#hyderabadibiryani", "#chickenbiryani"],
    genericHashtags: ["#food", "#foodie", "#cooking"],
    languageHashtags: ["#telugurecipe", "#telugufood"]
  },
  
  // ===== CALL TO ACTIONS =====
  callToActions: {
    hasCTAs: true,
    ctaCount: 5,
    
    // Specific CTAs
    subscribeCTA: true,
    subscribePhrasing: "Don't forget to SUBSCRIBE!",
    
    likeCTA: true,
    likePhrasing: "If you enjoyed, please LIKE the video",
    
    commentCTA: true,
    commentPhrasing: "Comment below your favorite biryani type!",
    commentQuestion: "What's your favorite biryani type?",
    
    shareCTA: true,
    notificationBellCTA: true,
    
    // Engagement prompts
    asksQuestion: true,
    questionAsked: "What recipe should I make next?",
    
    // Other CTAs
    otherCTAs: [
      "Check out my other biryani recipes",
      "Follow me on Instagram for daily updates"
    ]
  },
  
  // ===== SEO ANALYSIS =====
  seo: {
    // Keyword presence
    primaryKeywordPresent: true,
    primaryKeyword: "Hyderabadi Biryani",
    keywordInFirst100Chars: true,
    keywordDensity: 2.3,  // percentage
    
    // All keywords found
    keywordsFound: [
      { keyword: "biryani", count: 8 },
      { keyword: "hyderabadi", count: 5 },
      { keyword: "recipe", count: 4 },
      { keyword: "chicken", count: 3 }
    ],
    
    // Quality
    naturalLanguage: true,  // vs keyword stuffed
    readabilityScore: 7.5,
    
    // Length optimization
    lengthOptimal: true,  // 200-5000 chars recommended
    
    // Link optimization
    hasVideoLinks: true,  // links to other videos
    internalLinking: "good"
  },
  
  // ===== MONETIZATION SIGNALS =====
  monetization: {
    hasAffiliateLinks: false,
    hasSponsorMention: false,
    sponsorName: null,
    hasProductLinks: false,
    hasMerchandise: false,
    hasPatreon: false,
    hasMembership: false,
    
    // Disclosure
    hasDisclosure: false,
    disclosureType: null
  },
  
  // ===== SCORES =====
  scores: {
    completenessScore: 8.5,    // all necessary info present
    organizationScore: 9.0,    // well structured
    seoScore: 8.0,             // keyword optimized
    engagementScore: 7.5,      // CTAs and interaction
    professionalismScore: 8.5, // quality of writing
    
    overallScore: 8.3,
    
    suggestions: [
      "Consider adding nutrition information",
      "Could add more internal video links",
      "Hashtags could be more targeted"
    ]
  }
}
```

---

## Tag Analysis Schema

### Collection: `channels/{channelId}/videos/{videoId}/analysis/tags`

```javascript
{
  // ===== ANALYSIS METADATA =====
  analyzedAt: Timestamp,
  modelUsed: "claude-opus-4-5-20250514",
  analysisVersion: "1.0",
  
  // ===== RAW DATA =====
  rawTags: [
    "biryani recipe",
    "hyderabadi biryani",
    "chicken biryani recipe",
    "how to make biryani",
    "vismai food",
    "vismai food biryani",
    "telugu recipe",
    "telugu cooking",
    "indian cooking",
    "dum biryani",
    "restaurant style biryani",
    "biryani at home",
    "easy biryani recipe",
    "authentic biryani",
    "spicy biryani",
    "biryani masala",
    "basmati rice",
    "chicken recipe",
    "lunch recipe",
    "dinner recipe",
    "బిర్యానీ",
    "హైదరాబాదీ బిర్యానీ",
    "తెలుగు వంటకం"
  ],
  
  tagCount: 23,
  totalCharacters: 412,
  characterLimit: 500,
  utilizationPercent: 82.4,
  
  // ===== CATEGORIZATION =====
  categories: {
    // Brand tags
    brandTags: [
      { tag: "vismai food", purpose: "channel-discovery" },
      { tag: "vismai food biryani", purpose: "series-discovery" }
    ],
    brandTagCount: 2,
    
    // Primary topic tags
    primaryTags: [
      { tag: "biryani recipe", searchVolume: "very-high", competition: "high" },
      { tag: "hyderabadi biryani", searchVolume: "high", competition: "high" },
      { tag: "chicken biryani recipe", searchVolume: "high", competition: "high" }
    ],
    primaryTagCount: 3,
    
    // Modifier tags
    modifierTags: [
      { tag: "restaurant style biryani", modifier: "quality" },
      { tag: "easy biryani recipe", modifier: "difficulty" },
      { tag: "authentic biryani", modifier: "authenticity" }
    ],
    modifierTagCount: 3,
    
    // Ingredient tags
    ingredientTags: [
      { tag: "biryani masala", ingredient: "spice-mix" },
      { tag: "basmati rice", ingredient: "grain" }
    ],
    ingredientTagCount: 2,
    
    // Language tags
    languageTags: [
      { tag: "telugu recipe", language: "telugu" },
      { tag: "telugu cooking", language: "telugu" },
      { tag: "indian cooking", language: "english" }
    ],
    languageTagCount: 3,
    
    // Telugu script tags
    teluguScriptTags: [
      { tag: "బిర్యానీ", meaning: "biryani" },
      { tag: "హైదరాబాదీ బిర్యానీ", meaning: "hyderabadi biryani" },
      { tag: "తెలుగు వంటకం", meaning: "telugu recipe" }
    ],
    teluguTagCount: 3,
    
    // Generic/broad tags
    genericTags: [
      { tag: "chicken recipe", specificity: "medium" },
      { tag: "lunch recipe", specificity: "low" },
      { tag: "dinner recipe", specificity: "low" }
    ],
    genericTagCount: 3,
    
    // Long-tail tags
    longTailTags: [
      { tag: "how to make biryani", words: 4, intent: "tutorial" },
      { tag: "biryani at home", words: 3, intent: "home-cooking" }
    ],
    longTailTagCount: 2,
    
    // Misspelling tags (intentional)
    misspellingTags: [],
    misspellingTagCount: 0
  },
  
  // ===== STRATEGY ANALYSIS =====
  strategy: {
    // Tag diversity
    diversityScore: 8,  // 1-10, mix of types
    
    // Coverage
    hasChannelName: true,
    hasMainKeyword: true,
    hasTeluguTags: true,
    hasLongTail: true,
    hasModifiers: true,
    
    // Intentional strategies
    includesMisspellings: false,
    includesCompetitorNames: false,
    includesTrendingTags: false,
    
    // Tag balance
    broadVsSpecific: {
      broadPercent: 22,
      specificPercent: 52,
      longTailPercent: 26
    },
    
    // Language balance
    languageBalance: {
      englishPercent: 78,
      teluguPercent: 22
    },
    
    // Optimization level
    wellOptimized: true,
    
    // Issues found
    issues: [
      "Could add more Telugu script tags",
      "Missing some high-volume related keywords"
    ]
  },
  
  // ===== SEARCH ANALYSIS =====
  searchAnalysis: {
    // Estimated search volumes
    highVolumeCount: 5,
    mediumVolumeCount: 10,
    lowVolumeCount: 8,
    
    // Search intent coverage
    howToIntent: true,
    recipeIntent: true,
    reviewIntent: false,
    comparisonIntent: false,
    
    // Ranking potential
    rankingPotential: {
      highPotential: ["vismai food biryani", "telugu biryani recipe"],
      mediumPotential: ["hyderabadi biryani", "chicken biryani recipe"],
      lowPotential: ["biryani recipe", "chicken recipe"]
    }
  },
  
  // ===== COMPETITIVE ANALYSIS =====
  competitive: {
    // Overlap with top videos
    commonWithTopVideos: [
      "biryani recipe",
      "hyderabadi biryani",
      "chicken biryani"
    ],
    
    // Unique tags
    uniqueTags: [
      "vismai food",
      "vismai food biryani"
    ],
    
    // Missing opportunities
    missingHighValueTags: [
      "dum biryani recipe",
      "biryani recipe in telugu",
      "authentic hyderabadi biryani recipe"
    ],
    
    // Competitor tag patterns
    competitorPatterns: [
      "Most competitors use 'easy' or 'simple' modifiers",
      "Top videos include cooking time in tags"
    ]
  },
  
  // ===== SCORES =====
  scores: {
    relevanceScore: 9.0,        // tags match content
    diversityScore: 8.0,        // good mix of types
    searchVolumeScore: 7.5,     // targets searchable terms
    competitionScore: 6.0,      // ability to rank
    languageCoverageScore: 7.0, // English + Telugu
    utilizationScore: 8.2,      // uses available space
    
    overallScore: 7.6,
    
    suggestions: [
      "Add 'dum biryani recipe' - high volume, moderate competition",
      "Include more Telugu script variations",
      "Consider adding cooking time tags like '1 hour recipe'",
      "Add seasonal tags if relevant (Eid, Ramadan)"
    ]
  }
}
```

---

# PHASE 3: PATTERN DISCOVERY

## Insights Schema

### Collection: `insights/thumbnails`

```javascript
{
  generatedAt: Timestamp,
  basedOnVideos: 50000,
  basedOnChannels: 100,
  
  // ===== TOP PERFORMING ELEMENTS =====
  topPerformingElements: {
    composition: [
      { element: "face-right-food-left", avgViewMultiplier: 2.4, sampleSize: 1250 },
      { element: "high-contrast", avgViewMultiplier: 2.1, sampleSize: 3400 },
      { element: "rule-of-thirds", avgViewMultiplier: 1.8, sampleSize: 2100 }
    ],
    
    humanPresence: [
      { element: "surprised-expression", avgViewMultiplier: 2.6, sampleSize: 890 },
      { element: "eye-contact", avgViewMultiplier: 2.2, sampleSize: 1540 },
      { element: "pointing-at-food", avgViewMultiplier: 1.9, sampleSize: 420 }
    ],
    
    text: [
      { element: "view-count-badge", avgViewMultiplier: 2.8, sampleSize: 650 },
      { element: "telugu-text-present", avgViewMultiplier: 1.7, sampleSize: 4200 },
      { element: "yellow-text-color", avgViewMultiplier: 1.6, sampleSize: 2800 }
    ],
    
    colors: [
      { element: "orange-background", avgViewMultiplier: 2.2, sampleSize: 980 },
      { element: "red-accents", avgViewMultiplier: 1.9, sampleSize: 1650 },
      { element: "warm-palette", avgViewMultiplier: 1.7, sampleSize: 3200 }
    ],
    
    food: [
      { element: "steam-visible", avgViewMultiplier: 2.5, sampleSize: 720 },
      { element: "close-up-shot", avgViewMultiplier: 2.1, sampleSize: 2100 },
      { element: "garnished", avgViewMultiplier: 1.8, sampleSize: 1890 }
    ]
  },
  
  // ===== WORST PERFORMING ELEMENTS =====
  worstPerformingElements: [
    { element: "cluttered-layout", avgViewMultiplier: 0.4, avoid: true },
    { element: "no-face", avgViewMultiplier: 0.6, avoid: true },
    { element: "low-contrast", avgViewMultiplier: 0.5, avoid: true },
    { element: "text-only", avgViewMultiplier: 0.55, avoid: true },
    { element: "dark-colors", avgViewMultiplier: 0.65, avoid: true }
  ],
  
  // ===== OPTIMAL COMBINATIONS =====
  optimalCombinations: [
    {
      name: "Viral Recipe Thumbnail",
      elements: ["surprised-face", "yellow-text", "food-close-up", "steam", "view-badge"],
      avgViewMultiplier: 4.2,
      sampleSize: 120,
      exampleVideoIds: ["xxx", "yyy", "zzz"]
    },
    {
      name: "Trust Builder",
      elements: ["face-with-food", "clean-layout", "brand-colors", "telugu-english-text"],
      avgViewMultiplier: 2.8,
      sampleSize: 340,
      exampleVideoIds: ["xxx", "yyy", "zzz"]
    }
  ],
  
  // ===== COLOR PALETTES =====
  recommendedPalettes: {
    cooking: {
      primary: ["#FF6B35", "#E74C3C", "#F39C12"],
      secondary: ["#FFFFFF", "#FFFF00"],
      accent: ["#27AE60", "#2ECC71"],
      avoid: ["#3498DB", "#9B59B6"]
    }
  },
  
  // ===== BY CONTENT TYPE =====
  byContentType: {
    recipe: { topElements: [...], optimalLayout: "..." },
    vlog: { topElements: [...], optimalLayout: "..." },
    review: { topElements: [...], optimalLayout: "..." }
  }
}
```

### Collection: `insights/titles`

```javascript
{
  generatedAt: Timestamp,
  basedOnVideos: 50000,
  
  // ===== WINNING PATTERNS =====
  winningPatterns: [
    {
      pattern: "Dish Name + SECRET/రహస్యం + Recipe",
      avgViews: 4200000,
      avgEngagement: 4.8,
      sampleSize: 89,
      examples: [
        "Biryani SECRET Recipe | బిర్యానీ రహస్యం",
        "Dosa SECRET Recipe | దోశ రహస్యం"
      ]
    },
    {
      pattern: "Number + Dish + Challenge/Test",
      avgViews: 3800000,
      avgEngagement: 5.2,
      sampleSize: 45,
      examples: [
        "30 రకాల బిర్యానీ Challenge",
        "100 Dosa Challenge"
      ]
    },
    {
      pattern: "Location Style + Dish + Recipe",
      avgViews: 3100000,
      avgEngagement: 4.1,
      sampleSize: 234,
      examples: [
        "Hyderabadi Style Biryani Recipe",
        "Restaurant Style Manchurian"
      ]
    }
  ],
  
  // ===== POWER WORDS =====
  powerWords: {
    highImpact: [
      { word: "SECRET", telugu: "రహస్యం", multiplier: 2.4 },
      { word: "PERFECT", telugu: "పర్ఫెక్ట్", multiplier: 1.9 },
      { word: "AUTHENTIC", telugu: "అసలైన", multiplier: 1.8 },
      { word: "Restaurant Style", telugu: "హోటల్ స్టైల్", multiplier: 2.2 }
    ],
    mediumImpact: [
      { word: "Easy", telugu: "సులభం", multiplier: 1.3 },
      { word: "Quick", telugu: "త్వరగా", multiplier: 1.4 }
    ],
    lowImpact: [
      { word: "Simple", telugu: "సింపుల్", multiplier: 0.9 },
      { word: "Basic", telugu: "బేసిక్", multiplier: 0.8 }
    ]
  },
  
  // ===== OPTIMAL LENGTH =====
  optimalLength: {
    characters: { min: 45, max: 65, sweetSpot: 55 },
    words: { min: 6, max: 12, sweetSpot: 8 }
  },
  
  // ===== LANGUAGE MIX =====
  optimalLanguageMix: {
    teluguRatio: { min: 0.2, max: 0.5, sweetSpot: 0.35 },
    recommendation: "Start with English keyword, include Telugu translation"
  },
  
  // ===== BY NICHE =====
  byNiche: {
    cooking: { patterns: [...], powerWords: [...] },
    travel: { patterns: [...], powerWords: [...] },
    entertainment: { patterns: [...], powerWords: [...] }
  }
}
```

### Collection: `insights/timing`

```javascript
{
  generatedAt: Timestamp,
  basedOnVideos: 50000,
  
  // ===== BEST POSTING TIMES =====
  bestTimes: {
    byDayOfWeek: [
      { day: "Saturday", avgViews: 125000, multiplier: 1.4 },
      { day: "Sunday", avgViews: 118000, multiplier: 1.32 },
      { day: "Friday", avgViews: 105000, multiplier: 1.18 },
      { day: "Thursday", avgViews: 95000, multiplier: 1.07 },
      { day: "Wednesday", avgViews: 90000, multiplier: 1.01 },
      { day: "Tuesday", avgViews: 85000, multiplier: 0.95 },
      { day: "Monday", avgViews: 82000, multiplier: 0.92 }
    ],
    
    byHourIST: [
      { hour: 18, avgViews: 130000, multiplier: 1.46, label: "6 PM" },
      { hour: 19, avgViews: 125000, multiplier: 1.40, label: "7 PM" },
      { hour: 12, avgViews: 110000, multiplier: 1.23, label: "12 PM" },
      { hour: 20, avgViews: 105000, multiplier: 1.18, label: "8 PM" }
    ],
    
    optimal: {
      day: "Saturday",
      hourIST: 18,
      description: "Saturday 6 PM IST",
      multiplier: 1.6
    }
  },
  
  // ===== SEASONAL TRENDS =====
  seasonalTrends: {
    festivals: [
      { name: "Sankranti", month: 1, boost: 3.2, topContent: ["traditional recipes", "festival vlogs"] },
      { name: "Ugadi", month: 3, boost: 2.8, topContent: ["pachadi recipe", "new year"] },
      { name: "Diwali", month: 10, boost: 2.5, topContent: ["sweets", "snacks"] },
      { name: "Ramadan", month: "varies", boost: 2.1, topContent: ["iftar recipes", "biryani"] }
    ],
    
    summer: { months: [4, 5, 6], trending: ["mango recipes", "cool drinks", "ice cream"] },
    monsoon: { months: [7, 8, 9], trending: ["pakora", "chai", "comfort food"] },
    winter: { months: [11, 12, 1], trending: ["soups", "warm dishes", "sweets"] }
  }
}
```

### Collection: `insights/contentGaps`

```javascript
{
  generatedAt: Timestamp,
  
  // ===== HIGH OPPORTUNITY GAPS =====
  highOpportunity: [
    {
      topic: "Germany Indian Grocery Shopping",
      searchDemand: "medium",
      competition: "very-low",
      existingVideos: 3,
      avgViewsInNiche: 45000,
      opportunityScore: 9.2,
      suggestedTitles: [
        "Germany's CHEAPEST Indian Store | Full Tour + Prices",
        "Indian Grocery Shopping in Germany | Telugu"
      ]
    },
    {
      topic: "Telugu NRI Life in Europe",
      searchDemand: "medium",
      competition: "very-low",
      existingVideos: 8,
      avgViewsInNiche: 32000,
      opportunityScore: 8.8,
      suggestedTitles: [...]
    },
    {
      topic: "German-Indian Fusion Recipes",
      searchDemand: "low-medium",
      competition: "very-low",
      existingVideos: 2,
      avgViewsInNiche: 28000,
      opportunityScore: 8.5,
      suggestedTitles: [...]
    }
  ],
  
  // ===== SATURATED TOPICS (AVOID) =====
  saturatedTopics: [
    { topic: "Biryani Recipe", competition: "extreme", recommendation: "Need unique angle" },
    { topic: "Dosa Recipe", competition: "very-high", recommendation: "Fusion only" },
    { topic: "USA Telugu Vlogs", competition: "very-high", recommendation: "Avoid" }
  ],
  
  // ===== YOUR UNIQUE POSITIONING =====
  uniquePositioning: {
    location: "Germany",
    audience: "Telugu NRIs in Europe",
    uniqueAngles: [
      "Only Telugu cooking channel in Germany",
      "European ingredients + Indian recipes",
      "Germany life for Telugu audience"
    ],
    recommendedNiche: "Germany Telugu NRI Content"
  }
}
```

---

# PHASE 4: RECOMMENDATION ENGINE

## API Specification

### Endpoint: Generate Video Recommendation

```javascript
// Input
{
  topic: "I want to make a biryani video",
  contentType: "recipe",  // optional
  targetAudience: "telugu-nri",  // optional
  uniqueAngle: "German kitchen"  // optional
}

// Output
{
  // ===== TITLE RECOMMENDATIONS =====
  titles: {
    primary: {
      english: "Restaurant Style Hyderabadi Biryani | Germany Kitchen | BEST Recipe",
      telugu: "హోటల్ స్టైల్ హైదరాబాదీ బిర్యానీ | జర్మనీ కిచెన్",
      combined: "Hyderabadi Biryani | హైదరాబాదీ బిర్యానీ | Germany Kitchen | Restaurant Style",
      predictedCTR: "above-average",
      reasoning: "Combines high-search keyword with unique Germany angle and quality modifier"
    },
    alternatives: [
      {
        title: "Germany lo Biryani | SECRET Restaurant Recipe | 30 ఏళ్ల రహస్యం",
        predictedCTR: "high",
        reasoning: "Uses SECRET power word + nostalgia + unique location"
      },
      {
        title: "Biryani with German Ingredients?! | Fusion Experiment | Telugu",
        predictedCTR: "medium-high",
        reasoning: "Curiosity hook + unique fusion angle"
      }
    ]
  },
  
  // ===== THUMBNAIL SPECIFICATION =====
  thumbnail: {
    layout: {
      type: "split-composition",
      description: "Face on right third, biryani on left with steam, text overlay top"
    },
    
    elements: {
      face: {
        required: true,
        expression: "surprised or excited",
        position: "right-third",
        size: "large",
        eyeContact: true
      },
      
      food: {
        required: true,
        type: "biryani-close-up",
        position: "left-center",
        showSteam: true,
        garnished: true
      },
      
      text: {
        primary: {
          content: "GERMANY",
          language: "english",
          position: "top-left",
          color: "#FFFF00",
          style: "bold-with-outline"
        },
        secondary: {
          content: "బిర్యానీ రహస్యం",
          language: "telugu",
          position: "bottom",
          color: "#FFFFFF"
        }
      },
      
      graphics: {
        addArrow: true,
        arrowPointTo: "food",
        addBorder: true,
        borderColor: "#FFFFFF"
      }
    },
    
    colors: {
      background: "#FF6B35",
      accent: "#FFFF00",
      text: "#FFFFFF"
    },
    
    referenceExamples: [
      { videoId: "xxx", reason: "Similar layout that got 5M views" },
      { videoId: "yyy", reason: "Color scheme reference" }
    ]
  },
  
  // ===== TAG RECOMMENDATIONS =====
  tags: {
    primary: [
      "biryani recipe",
      "hyderabadi biryani",
      "biryani recipe in telugu",
      "germany biryani"
    ],
    secondary: [
      "restaurant style biryani",
      "dum biryani",
      "chicken biryani recipe",
      "how to make biryani"
    ],
    telugu: [
      "బిర్యానీ",
      "హైదరాబాదీ బిర్యానీ",
      "తెలుగు వంటకం",
      "బిర్యానీ రెసిపీ"
    ],
    longtail: [
      "biryani recipe in germany",
      "indian cooking in europe",
      "nri cooking telugu"
    ],
    brand: [
      "germany lo guntur ammai",
      "guntur ammai biryani"
    ],
    
    fullTagString: "biryani recipe, hyderabadi biryani, ...",
    characterCount: 487,
    utilizationPercent: 97.4
  },
  
  // ===== POSTING RECOMMENDATION =====
  posting: {
    bestDay: "Saturday",
    bestTime: "6:00 PM IST",
    alternativeTimes: [
      "Sunday 12:00 PM IST",
      "Friday 7:00 PM IST"
    ],
    reasoning: "Weekend evening maximizes Telugu NRI viewership in Europe and India"
  },
  
  // ===== CONTENT RECOMMENDATIONS =====
  content: {
    optimalDuration: "12-15 minutes",
    mustInclude: [
      "Ingredient list with German alternatives",
      "Step-by-step with timestamps",
      "Final reveal with steam shot",
      "Taste test reaction"
    ],
    hooks: [
      "Start with the final dish reveal",
      "Mention 'secret' or 'restaurant trick' in first 30 seconds"
    ],
    
    description: {
      template: "...",
      mustInclude: ["timestamps", "ingredients", "social links", "CTAs"]
    }
  },
  
  // ===== PREDICTED PERFORMANCE =====
  prediction: {
    estimatedViews: {
      low: 15000,
      medium: 45000,
      high: 120000
    },
    basedOn: "Similar videos in your niche with these elements",
    confidence: "medium",
    
    factors: {
      positive: [
        "Unique Germany angle (low competition)",
        "High-search keyword (biryani)",
        "Recommended thumbnail elements"
      ],
      risks: [
        "Channel currently inactive (2 years)",
        "Low subscriber base",
        "Algorithm may need warm-up"
      ]
    }
  }
}
```

---

## Cost Estimation

### Phase 1: YouTube Scraping
| Item | Cost |
|------|------|
| YouTube API | Free (within quota) |
| Firebase Firestore | ~$5-10 (50K documents) |
| Firebase Storage | ~$1-2 (3GB thumbnails) |
| **Subtotal** | **~$10-15** |

### Phase 2: AI Analysis
| Item | Volume | Cost |
|------|--------|------|
| Thumbnail Analysis (Opus Vision) | 50,000 images | ~$150-200 |
| Title Analysis (Opus Text) | 50,000 titles | ~$20-30 |
| Description Analysis | 50,000 descriptions | ~$30-40 |
| Tag Analysis | 50,000 tag sets | ~$15-20 |
| **Subtotal** | | **~$215-290** |

### Phase 3 & 4: Insights & Recommendations
| Item | Cost |
|------|------|
| Correlation Analysis | ~$10-20 |
| Recommendation Queries | ~$5-10 |
| **Subtotal** | **~$15-30** |

### Total Estimated Cost: **~$240-335**

---

## Implementation Timeline

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1: Scraper | 1-2 weeks | YouTube API key, Firebase setup |
| Scraping execution | 3-5 days | Quota limits |
| Phase 2: AI Analysis | 1 week | Claude API key |
| Analysis execution | 2-3 days | API rate limits |
| Phase 3: Insights | 3-4 days | Phase 2 complete |
| Phase 4: Recommender | 3-4 days | Phase 3 complete |
| **Total** | **4-6 weeks** | |

---

## Execution Checklist

### Before Starting
- [ ] YouTube Data API v3 enabled
- [ ] YouTube API key created
- [ ] Firebase project created
- [ ] Firestore database initialized
- [ ] Firebase Storage bucket created
- [ ] Firebase service account JSON downloaded
- [ ] Anthropic API key obtained
- [ ] channels.json populated with 100 channel URLs
- [ ] All environment variables configured

### Phase 1 Complete When
- [ ] All channels scraped
- [ ] All video metadata stored
- [ ] All thumbnails downloaded
- [ ] Calculated metrics generated
- [ ] No "in_progress" channels remaining

### Phase 2 Complete When
- [ ] All thumbnails analyzed
- [ ] All titles analyzed
- [ ] All descriptions analyzed
- [ ] All tags analyzed
- [ ] Analysis stored in Firestore

### Phase 3 Complete When
- [ ] Correlation analysis complete
- [ ] Pattern insights generated
- [ ] Content gaps identified
- [ ] Timing insights generated

### Phase 4 Complete When
- [ ] Recommendation engine functional
- [ ] Can generate title suggestions
- [ ] Can generate thumbnail specs
- [ ] Can generate tag recommendations
- [ ] Can predict performance

---

## Final Notes

1. **This is a comprehensive system** - You're building something that doesn't exist in the market as a turnkey solution.

2. **Data quality matters** - The insights are only as good as the channels you analyze. Focus on successful Telugu channels.

3. **AI analysis is the secret sauce** - The combination of vision + text analysis on 50K videos will reveal patterns no human could find manually.

4. **Start creating while building** - Don't wait for the full system. Use early insights to start making videos.

5. **Iterate on insights** - After creating videos, add your own performance data back into the system.

---