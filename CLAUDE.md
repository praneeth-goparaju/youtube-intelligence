# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

YouTube Intelligence System - a multi-phase analytics platform that scrapes Telugu YouTube channel data, analyzes content with Gemini AI, discovers performance patterns, and generates recommendations for new video creation.

## Architecture

Four-phase system with separate technology stacks:

1. **Phase 1 - Scraper (TypeScript)**: YouTube Data API v3 integration, stores in Firebase Firestore/Storage
2. **Phase 2 - Analyzer (Python)**: Gemini 2.0 Flash for thumbnail vision analysis, title/description/tag text analysis
3. **Phase 3 - Insights (Python)**: Statistical correlation and pattern discovery
4. **Phase 4 - Recommender (TypeScript)**: AI-powered recommendation engine (CLI + Firebase Functions API)

**Data Flow**: Scraper → Firestore → Analyzer → Firestore → Insights → Firestore → Recommender

## Setup

```bash
# Python dependencies (analyzer + insights)
pip install -r requirements.txt

# TypeScript dependencies
cd scraper && npm install
cd ../functions && npm install
```

## Commands

### Scraper (Phase 1)
```bash
cd scraper
npm start                       # Run scraper
npm test                        # Run vitest tests
npx tsx scripts/validate.ts     # Test API connections
npx tsx scripts/reset-progress.ts  # Clear progress for re-run
```

### Analyzer (Phase 2)
```bash
cd analyzer
python src/main.py                                    # Run all analysis types
python src/main.py --type thumbnail                   # Single analysis type
python src/main.py --type title --channel CHANNEL_ID  # Specific channel
python src/main.py --type content_structure           # Infer video structure (transcript alternative)
python src/main.py --limit 50                         # Limit videos per channel
python src/main.py --validate                         # Test connections only
pytest tests/                                         # Run tests
```

### Insights (Phase 3)
```bash
cd insights
python src/main.py                    # Generate all insights
python src/main.py --type thumbnails  # Specific insight type (thumbnails, titles, timing, gaps)
pytest tests/
```

### Recommender (Phase 4)
```bash
cd functions
npm install

# CLI usage
npm run recommend -- --topic "Hyderabadi Biryani" --type recipe
npm run recommend -- --topic "Biryani" --angle "Restaurant secret" --output recommendation.json

# API usage (local emulator)
npm run serve
curl -X POST http://localhost:5001/PROJECT/us-central1/recommend \
  -H "Content-Type: application/json" \
  -d '{"topic": "Biryani", "type": "recipe"}'

# Deploy to Firebase
npm run deploy
```

## Environment Variables

Required in `.env`:
- `YOUTUBE_API_KEY` - YouTube Data API v3
- `FIREBASE_PROJECT_ID`, `FIREBASE_CLIENT_EMAIL`, `FIREBASE_PRIVATE_KEY`, `FIREBASE_STORAGE_BUCKET`
- `GOOGLE_API_KEY` - Gemini API for analysis

## Security Configuration

For Firebase Functions deployment, set these secrets:
```bash
firebase functions:secrets:set GOOGLE_API_KEY        # Required: Gemini API key
firebase functions:secrets:set RECOMMEND_API_KEY     # Required: API key for authentication
firebase functions:secrets:set ALLOWED_ORIGINS       # Optional: Comma-separated allowed origins for CORS
```

API Authentication:
- All `/recommend` endpoint calls require `Authorization: Bearer <API_KEY>` header
- Rate limiting: 100 requests per hour per API key
- Firestore rules require Firebase Authentication for client reads

## Key Technical Considerations

- YouTube API quota is 10,000 units/day; scraper saves progress and resumes
- Channel URLs resolve via: `@handle` (1 unit), `/channel/UCxxx` (direct), `/user/` (1 unit), `/c/` (100 units - avoid)
- Uploads playlist ID: replace `UC` prefix with `UU` in channel ID
- Batch video details requests in groups of 50
- Use `mqdefault` thumbnail quality for storage efficiency
- Duration format is ISO 8601 (e.g., `PT15M33S`)
- Both scraper and analyzer track progress in Firestore for resumable operations
- Recommender falls back to template-based generation if Gemini fails

## Firebase Collections

- `channels/{channelId}` - Channel metadata and stats
- `channels/{channelId}/videos/{videoId}` - Video data with calculated metrics
- `channels/{channelId}/videos/{videoId}/analysis/{type}` - AI analysis results (thumbnail, title, description, tags, content_structure)
- `scrape_progress/{channelId}` - Resume state for interrupted scrapes
- `insights/{type}` - Aggregated patterns (thumbnails, titles, timing, contentGaps)

## Calculated Video Metrics

The scraper calculates these metrics for each video:
- `engagementRate`: (likes + comments) / views
- `viewsPerDay`: views / days since publish
- `viewsPerSubscriber`: views / channel subscriber count

## AI Analysis Models

All analysis uses Gemini 2.0 Flash (`gemini-2.0-flash`):
- Thumbnail: Vision analysis for composition, colors, text, food, graphics, psychology
- Title: Structure, language mix, hooks, keywords, Telugu-specific patterns
- Description: Timestamps, recipe content, links, hashtags, CTAs, SEO
- Tags: Categorization, strategy, search volume estimation
- Content Structure: Infers video structure from metadata (transcript-like insights without actual transcripts)
  - Video segments and pacing analysis from timestamps
  - Talking points and content outline inference
  - Recipe structure detection (steps, techniques, equipment)
  - Engagement points and retention strategies
  - Content classification and SEO insights
