# YouTube Intelligence System

A comprehensive multi-phase analytics platform that scrapes Telugu YouTube channel data, analyzes content with Gemini AI, discovers performance patterns, and generates data-driven recommendations for new video creation.

## Overview

This system answers the question: **"What title, thumbnail, and posting time should I use for maximum views?"**

The platform processes 100+ Telugu YouTube channels to extract actionable insights:

- **208,000+ non-short videos** scraped across 116 channels
- **AI-powered analysis** of thumbnails and title+description (2 API calls per video)
- **Per-content-type profiling** comparing all videos vs top 10% performers
- **Automated recommendations** based on proven patterns

## Architecture

```mermaid
graph TD
    A[channels.json] --> B

    subgraph pipeline [DATA PIPELINE]
        B["Phase 1<br/><b>Scraper</b><br/>TypeScript"] --> C["Phase 2<br/><b>Analyzer</b><br/>Python"]
        C --> D["Phase 3<br/><b>Insights</b><br/>Python"]
        D --> E["Phase 4<br/><b>Recommender</b><br/>TypeScript"]
    end

    B --> F
    C --> F
    D --> F
    E --> F

    F[("Firebase Firestore<br/>channels/ → videos/ → analysis/ → insights/")]

    F --> G["Firebase Function<br/>REST API / SDK"]
```

### Phase Components

| Phase | Name | Technology | Purpose |
|-------|------|------------|---------|
| 1 | **Scraper** | TypeScript/Node.js | Collect video data from YouTube API |
| 2 | **Analyzer** | Python + Gemini AI | Thumbnail vision + hybrid local/LLM title+description analysis (2 API calls/video) |
| 3 | **Insights** | Python | Per-content-type profiling and content gap analysis |
| 4 | **Recommender** | TypeScript | Generate video recommendations (CLI + API) |

## Quick Start

### Prerequisites

- Node.js 18+
- Python 3.11+
- YouTube Data API v3 key
- Firebase project with Firestore and Storage
- Google AI (Gemini) API key

### Installation

```bash
# Clone the repository
git clone https://github.com/praneeth-goparaju/youtube-intelligence.git
cd youtube-intelligence

# Configure environment
cp .env.example .env
# Edit .env with your API keys and Firebase credentials

# Install Phase 1 (Scraper)
cd scraper && npm install && cd ..

# Install Phase 2-3 (Python modules — shared requirements)
pip install -r requirements.txt

# Install Phase 4 (Recommender)
cd functions && npm install && cd ..
```

### Running the Pipeline

```bash
# Phase 1: Scrape YouTube data (may take multiple days due to API quota)
cd scraper
npm start                                  # Full initial scrape
npm start -- --update                      # Incremental update (new videos only)

# Phase 2: Analyze with AI (after scraping completes)
cd ../analyzer
python -m src.main                                   # Sync mode (per-video)
python -m src.main --mode batch --type thumbnail     # Batch mode (50% cheaper)

# Phase 3: Generate insights (after analysis completes)
cd ../insights
python -m src.main

# Phase 4: Get recommendations (two options)

# Option A: CLI (local)
cd ../functions
npm run recommend -- --topic "Biryani Recipe" --type recipe

# Option B: API (after deployment — see docs/DEPLOYMENT.md)
curl -X POST https://us-central1-YOUR_PROJECT.cloudfunctions.net/recommend \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{"topic": "Biryani Recipe", "type": "recipe"}'
```

## Project Structure

```
youtube-intelligence/
├── README.md                    # This file
├── CONTRIBUTING.md              # Contribution guidelines
├── CLAUDE.md                    # AI assistant guidance
├── LICENSE                      # MIT License
├── SECURITY.md                  # Security policy
├── .env.example                 # Environment template
├── requirements.txt             # Shared Python dependencies (analyzer + insights)
├── firebase.json                # Firebase project configuration
├── firestore.rules              # Firestore security rules
├── storage.rules                # Firebase Storage security rules
│
├── config/
│   └── channels.json.example    # Template for YouTube channel URLs
│
├── data/
│   └── channels-review.csv.example  # Template for channel review data
│
├── scraper/                     # Phase 1: TypeScript YouTube Scraper
│   ├── README.md
│   ├── package.json
│   ├── src/
│   │   ├── youtube/             # YouTube API integration
│   │   ├── firebase/            # Firebase operations
│   │   ├── scraper/             # Core scraping logic
│   │   └── utils/               # Utilities
│   ├── scripts/                 # Utility scripts (validate, reset, status, etc.)
│   └── tests/
│
├── analyzer/                    # Phase 2: Python AI Analyzer
│   ├── README.md
│   ├── src/
│   │   ├── analyzers/           # Analysis modules (thumbnail, title_description)
│   │   ├── processors/          # Batch processing
│   │   ├── batch_api/           # Gemini Batch API handling
│   │   └── prompts/             # AI prompts
│   └── tests/
│
├── insights/                    # Phase 3: Per-Content-Type Profiling
│   ├── README.md
│   └── src/
│       ├── profiler.py          # Feature profiling (all vs top 10%)
│       └── gaps.py              # Content gap analysis
│
├── shared/                      # Shared utilities
│   ├── constants.py
│   ├── config.py
│   ├── firebase_utils.py
│   └── gemini_utils.py
│
├── functions/                   # Phase 4: Recommendation Engine (CLI + API)
│   ├── README.md
│   ├── package.json
│   └── src/                    # CLI, Firebase Functions, Gemini, rate limiter
│
└── docs/
    ├── TECHNICAL_DOCUMENTATION.md
    ├── API_REFERENCE.md
    ├── DEPLOYMENT.md
    └── TROUBLESHOOTING.md
```

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# YouTube API
YOUTUBE_API_KEY=your_youtube_api_key

# Firebase
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_CLIENT_EMAIL=firebase-adminsdk@your-project.iam.gserviceaccount.com
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
FIREBASE_STORAGE_BUCKET=your-project.appspot.com

# Gemini API
GOOGLE_API_KEY=your_gemini_api_key

# Optional: Scraper settings
API_DELAY_MS=100
QUOTA_WARNING_THRESHOLD=500
```

### Channel Configuration

Copy the example template and edit it with your target channels:

```bash
cp config/channels.json.example config/channels.json
```

```json
{
  "channels": [
    {
      "url": "https://www.youtube.com/@YourChannel1",
      "category": "cooking",
      "priority": 1
    },
    {
      "url": "https://www.youtube.com/@YourChannel2",
      "category": "entertainment",
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

## Features

### Phase 1: Data Collection
- Multi-format URL resolution (`@handle`, `/channel/`, `/user/`, `/c/`)
- Automatic quota management (10,000 units/day limit)
- Resumable scraping with progress tracking
- Incremental update mode (`--update`) for fetching only new videos
- Thumbnail downloading and storage (skips Shorts when `skipShortThumbnails` enabled)
- Unresolved channel URL tracking for retry
- Calculated metrics (engagement rate, views per day, etc.)

### Phase 2: AI Analysis (2 API calls per video)
- **Thumbnail Analysis** (100% Gemini vision): Composition, colors, human presence, text, food presentation, psychological triggers (~141 fields)
- **Title + Description Analysis** (hybrid local + LLM): 75 Gemini fields (semantic analysis, pattern recognition, niche classification) + 59 local fields (formatting, structure, language detection via regex/Unicode — no API cost)

### Phase 3: Per-Content-Type Profiling
- Group videos by content type (recipe, vlog, tutorial, etc.)
- Compare all videos vs top 10% performers (by viewsPerSubscriber)
- Feature profiling with auto-detected types (boolean, numeric, categorical, list)
- Content gap and keyword opportunity analysis

### Phase 4: Recommendations
- AI-generated title suggestions
- Thumbnail specification (layout, colors, elements)
- Tag recommendations with search volume estimates
- Optimal posting time
- Performance predictions

### Recommendation API (Firebase Functions)
- **REST API** for any client (web, mobile, scripts)
- **Callable Function** for Firebase SDK integration
- Automatic fallback to templates if AI fails
- Real-time recommendations in 2-5 seconds

## Testing

```bash
# Phase 1: TypeScript tests
cd scraper && npm test

# Phase 2-3: Python tests
cd analyzer && pytest tests/
cd insights && pytest tests/

# Validate API connections
cd scraper && npx tsx scripts/validate.ts
```

## Documentation

| Document | Description |
|----------|-------------|
| [Technical Documentation](docs/TECHNICAL_DOCUMENTATION.md) | Detailed system documentation |
| [API Reference](docs/API_REFERENCE.md) | Programmatic interface documentation |
| [Deployment Guide](docs/DEPLOYMENT.md) | Production deployment instructions |
| [Troubleshooting](docs/TROUBLESHOOTING.md) | Common issues and solutions |
| [Contributing](CONTRIBUTING.md) | How to contribute |

## Example Output

### Recommendation Engine Output

```json
{
  "titles": {
    "primary": {
      "english": "Restaurant Style Hyderabadi Biryani | BEST Recipe",
      "telugu": "హోటల్ స్టైల్ హైదరాబాదీ బిర్యానీ",
      "combined": "Hyderabadi Biryani | హైదరాబాదీ బిర్యానీ | Restaurant Style"
    }
  },
  "thumbnail": {
    "layout": "split-composition",
    "elements": {
      "face": { "position": "right-third", "expression": "surprised" },
      "food": { "position": "left-center", "showSteam": true }
    },
    "colors": { "background": "#FF6B35", "accent": "#FFFF00" }
  },
  "posting": {
    "bestDay": "Saturday",
    "bestTime": "18:00 IST"
  },
  "prediction": {
    "expectedViewRange": { "low": 15000, "medium": 45000, "high": 120000 }
  }
}
```

## Technology Stack

| Component | Technology | Version |
|-----------|------------|---------|
| Scraper Runtime | Node.js | 18+ |
| Scraper Language | TypeScript | 5.3+ |
| YouTube Integration | googleapis | 131.0+ |
| Database | Firebase Firestore | - |
| File Storage | Firebase Storage | - |
| AI Analysis | Google Gemini 2.5 Flash | - |
| Analytics | Python + Pandas | 3.11+ |
| Testing (TS) | Vitest | 1.2+ |
| Testing (Python) | pytest | 8.0+ |

## License

This project is licensed under the [MIT License](LICENSE).

## Support

For issues and feature requests, please open an issue on GitHub or contact the development team.

---

**Note**: This system is designed specifically for Telugu YouTube content analysis. The patterns and recommendations are optimized for this audience and content type.
