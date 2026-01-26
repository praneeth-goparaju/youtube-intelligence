# YouTube Intelligence System

A comprehensive multi-phase analytics platform that scrapes Telugu YouTube channel data, analyzes content with Gemini AI, discovers performance patterns, and generates data-driven recommendations for new video creation.

## Overview

This system answers the question: **"What title, thumbnail, tags, and posting time should I use for maximum views?"**

The platform processes 100+ Telugu YouTube channels to extract actionable insights:

- **50,000+ videos** analyzed for patterns
- **AI-powered analysis** of thumbnails, titles, descriptions, and tags
- **Statistical correlation** between content elements and performance
- **Automated recommendations** based on proven patterns

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATA PIPELINE                                   │
└─────────────────────────────────────────────────────────────────────────────┘

  channels.json
       │
       ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   PHASE 1    │    │   PHASE 2    │    │   PHASE 3    │    │   PHASE 4    │
│   Scraper    │───▶│   Analyzer   │───▶│   Insights   │───▶│ Recommender  │
│  TypeScript  │    │    Python    │    │    Python    │    │  Python/API  │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
       │                   │                   │                   │
       ▼                   ▼                   ▼                   ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         FIREBASE FIRESTORE                                │
│  channels/ ─► videos/ ─► analysis/ ─► insights/                          │
└──────────────────────────────────────────────────────────────────────────┘
                                                                    │
                                                                    ▼
                                                        ┌──────────────────┐
                                                        │ Firebase Function │
                                                        │  REST API / SDK   │
                                                        └──────────────────┘
```

### Phase Components

| Phase | Name | Technology | Purpose |
|-------|------|------------|---------|
| 1 | **Scraper** | TypeScript/Node.js | Collect video data from YouTube API |
| 2 | **Analyzer** | Python + Gemini AI | AI analysis of thumbnails, titles, tags |
| 3 | **Insights** | Python + Pandas/SciPy | Statistical pattern discovery |
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
git clone https://github.com/your-org/youtube-intelligence.git
cd youtube-intelligence

# Configure environment
cp .env.example .env
# Edit .env with your API keys and Firebase credentials

# Install Phase 1 (Scraper)
cd scraper && npm install && cd ..

# Install Phase 2-3 (Python modules)
cd analyzer && pip install -r requirements.txt && cd ..
cd insights && pip install -r requirements.txt && cd ..

# Install Phase 4 (Recommender)
cd functions && npm install && cd ..
```

### Running the Pipeline

```bash
# Phase 1: Scrape YouTube data (may take multiple days due to API quota)
cd scraper
npm start

# Phase 2: Analyze with AI (after scraping completes)
cd ../analyzer
python src/main.py

# Phase 3: Generate insights (after analysis completes)
cd ../insights
python src/main.py

# Phase 4: Get recommendations (two options)

# Option A: CLI (local)
cd ../functions
npm run recommend -- --topic "Biryani Recipe" --type recipe

# Option B: API (after deployment)
curl -X POST https://us-central1-YOUR_PROJECT.cloudfunctions.net/recommend \
  -H "Content-Type: application/json" \
  -d '{"topic": "Biryani Recipe", "type": "recipe"}'
```

## Project Structure

```
youtube_channel_analysis/
├── README.md                    # This file
├── CONTRIBUTING.md              # Contribution guidelines
├── CLAUDE.md                    # AI assistant guidance
├── .env.example                 # Environment template
│
├── config/
│   └── channels.json            # Input: YouTube channel URLs
│
├── scraper/                     # Phase 1: TypeScript YouTube Scraper
│   ├── README.md
│   ├── package.json
│   ├── src/
│   │   ├── youtube/             # YouTube API integration
│   │   ├── firebase/            # Firebase operations
│   │   ├── scraper/             # Core scraping logic
│   │   └── utils/               # Utilities
│   └── tests/
│
├── analyzer/                    # Phase 2: Python AI Analyzer
│   ├── README.md
│   ├── requirements.txt
│   ├── src/
│   │   ├── analyzers/           # Analysis modules
│   │   ├── processors/          # Batch processing
│   │   └── prompts/             # AI prompts
│   └── tests/
│
├── insights/                    # Phase 3: Pattern Discovery
│   ├── README.md
│   ├── requirements.txt
│   ├── src/
│   │   ├── correlations.py      # Statistical analysis
│   │   ├── patterns.py          # Pattern extraction
│   │   └── gaps.py              # Content gap analysis
│   └── outputs/
│
├── shared/                      # Shared utilities
│   ├── constants.py
│   ├── firebase_utils.py
│   └── gemini_utils.py
│
├── functions/                   # Phase 4: Recommendation Engine (CLI + API)
│   ├── README.md
│   ├── package.json
│   └── src/
│       ├── cli.ts               # CLI entry point
│       ├── index.ts             # Firebase Function definitions
│       ├── engine.ts            # Recommendation engine
│       └── templates.ts         # Fallback templates
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

Edit `config/channels.json` to specify channels to analyze:

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
    }
  ],
  "settings": {
    "maxVideosPerChannel": null,
    "includeShorts": true,
    "includePrivate": false
  }
}
```

## Features

### Phase 1: Data Collection
- Multi-format URL resolution (`@handle`, `/channel/`, `/user/`, `/c/`)
- Automatic quota management (10,000 units/day limit)
- Resumable scraping with progress tracking
- Thumbnail downloading and storage
- Calculated metrics (engagement rate, views per day, etc.)

### Phase 2: AI Analysis
- **Thumbnail Analysis**: Composition, colors, human presence, text, food presentation, psychological triggers
- **Title Analysis**: Structure, language mix, hooks, keywords, Telugu-specific patterns
- **Description Analysis**: Timestamps, recipe content, links, CTAs, SEO optimization
- **Tag Analysis**: Categorization, search volume estimation, strategy evaluation

### Phase 3: Pattern Discovery
- Pearson correlation between features and view counts
- Top performer pattern extraction (top 10%, top 25%)
- Optimal posting time analysis (day of week, hour)
- Content gap identification

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

## Recommendation API

The system includes a serverless API deployed as Firebase Functions for real-time recommendations.

### API Endpoint

```bash
POST https://us-central1-YOUR_PROJECT.cloudfunctions.net/recommend
```

### Example Request

```bash
curl -X POST https://us-central1-YOUR_PROJECT.cloudfunctions.net/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Hyderabadi Biryani",
    "type": "recipe",
    "angle": "Restaurant secret recipe",
    "audience": "Telugu home cooks"
  }'
```

### Using Firebase SDK

```typescript
import { getFunctions, httpsCallable } from 'firebase/functions';

const functions = getFunctions();
const getRecommendation = httpsCallable(functions, 'getRecommendation');

const result = await getRecommendation({
  topic: 'Biryani',
  type: 'recipe'
});
console.log(result.data);
```

### Deploy the API

```bash
cd functions
npm install
firebase functions:secrets:set GOOGLE_API_KEY
npm run deploy
```

See [functions/README.md](functions/README.md) for complete API documentation.

## Data Schema

### Firebase Collections

| Collection | Purpose |
|------------|---------|
| `channels/{channelId}` | Channel metadata and stats |
| `channels/{channelId}/videos/{videoId}` | Video data with metrics |
| `channels/{channelId}/videos/{videoId}/analysis/{type}` | AI analysis results |
| `scrape_progress/{channelId}` | Resume state for scraping |
| `insights/{type}` | Aggregated patterns |

### Calculated Metrics

For each video, the scraper calculates:

| Metric | Formula | Purpose |
|--------|---------|---------|
| `engagementRate` | (likes + comments) / views | Overall engagement |
| `viewsPerDay` | views / days since publish | Velocity |
| `viewsPerSubscriber` | views / channel subscribers | Relative performance |
| `publishDayOfWeek` | Day name (Monday-Sunday) | Timing analysis |
| `publishHourIST` | Hour (0-23) in IST | Timing analysis |

## API Quota Management

YouTube Data API has a **10,000 units/day** limit:

| Operation | Cost |
|-----------|------|
| `channels.list` | 1 unit |
| `playlistItems.list` | 1 unit |
| `videos.list` | 1 unit |
| `search.list` | 100 units (avoid!) |

The scraper:
1. Tracks quota usage in memory
2. Saves progress when quota reaches 500 remaining
3. Displays "Run again tomorrow" message
4. Resumes from last position on restart

## Testing

```bash
# Phase 1: TypeScript tests
cd scraper && npm test

# Phase 2-4: Python tests
cd analyzer && pytest tests/
cd insights && pytest tests/
cd recommender && pytest tests/

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
| AI Analysis | Google Gemini 2.0 Flash | - |
| Analytics | Python + Pandas + SciPy | 3.11+ |
| Testing (TS) | Vitest | 1.2+ |
| Testing (Python) | pytest | 8.0+ |

## License

This project is proprietary. All rights reserved.

## Support

For issues and feature requests, please open an issue on GitHub or contact the development team.

---

**Note**: This system is designed specifically for Telugu YouTube content analysis. The patterns and recommendations are optimized for this audience and content type.
