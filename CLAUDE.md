# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

YouTube Intelligence System - a multi-phase analytics platform that scrapes Telugu YouTube channel data, analyzes content with Gemini AI, discovers performance patterns, and generates recommendations for new video creation.

## Architecture

Four-phase system with separate technology stacks:

1. **Phase 1 - Scraper (TypeScript)**: YouTube Data API v3 integration, stores in Firebase Firestore/Storage
2. **Phase 2 - Analyzer (Python)**: Gemini 2.0 Flash for thumbnail vision analysis, title/description/tag text analysis
3. **Phase 3 - Insights (Python)**: Statistical correlation and pattern discovery
4. **Phase 4 - Recommender (Python)**: AI-powered recommendation engine

**Data Flow**: Scraper → Firestore → Analyzer → Firestore → Insights → Firestore → Recommender

## Commands

### Scraper (Phase 1)
```bash
cd scraper
npm install
npm start                       # Run scraper
npm test                        # Run vitest tests
npx tsx scripts/validate.ts     # Test API connections
npx tsx scripts/reset-progress.ts  # Clear progress for re-run
```

### Analyzer (Phase 2)
```bash
cd analyzer
pip install -r requirements.txt
python src/main.py                                    # Run all analysis types
python src/main.py --type thumbnail                   # Single analysis type
python src/main.py --type title --channel CHANNEL_ID  # Specific channel
python src/main.py --limit 50                         # Limit videos per channel
python src/main.py --validate                         # Test connections only
pytest tests/                                         # Run tests
```

### Insights (Phase 3)
```bash
cd insights
pip install -r requirements.txt
python src/main.py                    # Generate all insights
python src/main.py --type thumbnails  # Specific insight type (thumbnails, titles, timing, gaps)
pytest tests/
```

### Recommender (Phase 4)
```bash
cd recommender
pip install -r requirements.txt
python src/main.py \
  --topic "Hyderabadi Biryani" \
  --type recipe \
  --angle "Restaurant secret recipe" \
  --audience "Telugu home cooks" \
  --output recommendation.json
pytest tests/
```

## Environment Variables

Required in `.env`:
- `YOUTUBE_API_KEY` - YouTube Data API v3
- `FIREBASE_PROJECT_ID`, `FIREBASE_CLIENT_EMAIL`, `FIREBASE_PRIVATE_KEY`, `FIREBASE_STORAGE_BUCKET`
- `GOOGLE_API_KEY` - Gemini API for analysis

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
- `channels/{channelId}/videos/{videoId}/analysis/{type}` - AI analysis results (thumbnail, title, description, tags)
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
