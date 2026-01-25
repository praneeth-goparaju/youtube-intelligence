# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

YouTube Intelligence System - a multi-phase analytics platform that scrapes Telugu YouTube channel data, analyzes content with Claude AI, discovers performance patterns, and generates recommendations for new video creation.

## Architecture

Four-phase system with separate technology stacks:

1. **Phase 1 - Scraper (Node.js)**: YouTube Data API v3 integration, stores in Firebase Firestore/Storage
2. **Phase 2 - Analyzer (Python)**: Claude API for thumbnail vision analysis, title/description/tag text analysis
3. **Phase 3 - Insights (Python)**: Statistical correlation and pattern discovery
4. **Phase 4 - Recommender (Python)**: AI-powered recommendation engine

## Project Structure

```
scraper/          # Node.js - YouTube API scraping
analyzer/         # Python - Claude AI analysis
insights/         # Python - Pattern discovery
recommender/      # Python - Recommendation generation
config/           # channels.json input file
```

## Commands

### Scraper (Phase 1)
```bash
cd scraper
npm install
npm start                    # Run scraper
node scripts/validate.js     # Test API connections
node scripts/reset-progress.js  # Clear progress for re-run
```

### Analyzer (Phase 2)
```bash
cd analyzer
pip install -r requirements.txt
python src/main.py
python scripts/run_thumbnail_analysis.py
python scripts/run_title_analysis.py
python scripts/run_description_analysis.py
python scripts/run_tag_analysis.py
```

### Insights (Phase 3)
```bash
cd insights
pip install -r requirements.txt
python src/main.py
```

### Recommender (Phase 4)
```bash
cd recommender
pip install -r requirements.txt
python src/main.py
```

## Environment Variables

Required in `.env`:
- `YOUTUBE_API_KEY` - YouTube Data API v3
- `FIREBASE_PROJECT_ID`, `FIREBASE_CLIENT_EMAIL`, `FIREBASE_PRIVATE_KEY`, `FIREBASE_STORAGE_BUCKET`
- `ANTHROPIC_API_KEY` - Claude API for analysis

## Key Technical Considerations

- YouTube API quota is 10,000 units/day; scraper saves progress and resumes
- Channel URLs resolve via: `@handle` (1 unit), `/channel/UCxxx` (direct), `/user/` (1 unit), `/c/` (100 units - avoid)
- Uploads playlist ID: replace `UC` prefix with `UU` in channel ID
- Batch video details requests in groups of 50
- Use `mqdefault` thumbnail quality for storage efficiency
- Duration format is ISO 8601 (e.g., `PT15M33S`)

## Firebase Collections

- `channels/{channelId}` - Channel metadata and stats
- `channels/{channelId}/videos/{videoId}` - Video data with calculated metrics
- `channels/{channelId}/videos/{videoId}/analysis/{type}` - AI analysis results (thumbnail, title, description, tags)
- `scrape_progress/{channelId}` - Resume state for interrupted scrapes
- `insights/{type}` - Aggregated patterns (thumbnails, titles, timing, contentGaps)

## AI Analysis Models

All analysis uses Claude Opus 4.5 (`claude-opus-4-5-20250514`):
- Thumbnail: Vision analysis for composition, colors, text, food, graphics, psychology
- Title: Structure, language mix, hooks, keywords, Telugu-specific patterns
- Description: Timestamps, recipe content, links, hashtags, CTAs, SEO
- Tags: Categorization, strategy, search volume estimation
