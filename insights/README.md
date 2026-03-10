# Phase 3: Insights

A Python-based analytics system that generates per-content-type performance profiles by comparing feature distributions between all videos and top 10% performers (by viewsPerSubscriber).

Output is raw statistical data — the recommender's LLM handles interpretation of what's obvious vs meaningful.

## Overview

| Mode | Method | Output |
|------|--------|--------|
| **Profiles** | Feature distribution comparison (all vs top 10%) | Per-content-type thumbnail + title feature profiles |
| **Gaps** | Opportunity scoring by viewsPerSubscriber | Underserved topics, keywords, and formats |

## Quick Start

```bash
# Install dependencies
pip3 install -r requirements.txt

# Generate all insights
python3 -m src.main

# Generate specific insight type
python3 -m src.main --type profiles
python3 -m src.main --type gaps
```

## Architecture

```
insights/
├── requirements.txt
│
├── src/
│   ├── __init__.py
│   ├── main.py              # Entry point with CLI
│   ├── config.py            # Configuration
│   ├── firebase_client.py   # Firebase operations
│   ├── profiler.py          # Feature profiling (all vs top 10%)
│   ├── gaps.py              # Content gap analysis
│   └── recommender_bridge.py # Bridge insights for recommender
│
└── outputs/                  # Generated reports (JSON)
```

## Core Components

### 1. Feature Profiler (`profiler.py`)

Compares feature distributions between all videos and top 10% performers within each content type. Auto-detects feature types:

- **Boolean**: Rate of `True` in all vs top 10% (e.g., `facePresent: all=62%, top10=81%`)
- **Numeric**: Average in all vs top 10% (e.g., `clickability: all=6.2, top10=7.8`)
- **Categorical**: Value distribution percentages (e.g., `expression: surprised=45%, happy=30%`)
- **List**: Average length + item frequency for top 15 items

Also computes **timing profiles** — posting day/hour performance using viewsPerSubscriber.

### 2. Gap Analyzer (`gaps.py`)

Uses viewsPerSubscriber (not raw view count) to find opportunities:

- **Content Gaps**: High-performing topics with low competition
- **Keyword Gaps**: High-value keywords used in <10% of videos
- **Format Gaps**: Content formats (recipe, tutorial, vlog, etc.) with above-average viewsPerSubscriber

### 3. Main Orchestrator (`main.py`)

1. Loads all videos with both thumbnail and title analyses from Firestore
2. Groups videos by content type (from `contentSignals.contentType`)
3. Splits each group into all videos vs top 10% by viewsPerSubscriber
4. Generates feature profiles per content type
5. Saves to Firestore and local JSON files

## Output Structure

### Firestore Documents

- `insights/{contentType}` — Per-type profile (e.g., `insights/recipe`, `insights/vlog`)
- `insights/contentGaps` — Global content gap analysis
- `insights/summary` — Overview of all content types

### Per-Content-Type Profile

```json
{
  "contentType": "recipe",
  "generatedAt": "2024-01-25T10:30:00Z",
  "summary": {
    "totalVideos": 1250,
    "top10Count": 125,
    "top10Threshold": 2.45,
    "avgViewsPerSubscriber": 1.23
  },
  "thumbnail": {
    "sampleSize": {"all": 1200, "top10": 120},
    "features": {
      "humanPresence": {
        "facePresent": {"type": "boolean", "all": 0.62, "top10": 0.81},
        "expression": {
          "type": "categorical",
          "all": {"surprised": 0.25, "happy": 0.30},
          "top10": {"surprised": 0.45, "happy": 0.25}
        }
      },
      "food": {
        "steam": {"type": "boolean", "all": 0.31, "top10": 0.61}
      }
    }
  },
  "title": {
    "sampleSize": {"all": 1250, "top10": 125},
    "features": { ... }
  },
  "timing": {
    "byDayOfWeek": { ... },
    "byHourIST": { ... }
  }
}
```

## Command Line Interface

| Argument | Description | Default |
|----------|-------------|---------|
| `--type` | Insight type: `all`, `profiles`, `gaps`, `bridge` | `all` |

## Configuration

### Environment Variables

```bash
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_CLIENT_EMAIL=firebase-adminsdk@your-project.iam.gserviceaccount.com
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
FIREBASE_STORAGE_BUCKET=your-project.appspot.com
```

## Data Requirements

- Minimum 30 videos per content type (configurable via `MIN_VIDEOS_PER_TYPE`)
- Videos must have at least a title analysis (thumbnail analysis optional)
- Title analysis provides content type classification via `contentSignals.contentType`

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `numpy` | >=1.26.0 | Numerical operations |
| `pandas` | >=2.2.0 | Data manipulation |
| `scipy` | >=1.12.0 | Statistical analysis |
| `firebase-admin` | >=6.4.0 | Firebase SDK |
| `python-dotenv` | >=1.0.1 | Environment config |
