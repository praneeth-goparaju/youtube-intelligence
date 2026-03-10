# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

YouTube Intelligence System - a multi-phase analytics platform that scrapes Telugu YouTube channel data, analyzes content with Gemini AI, discovers performance patterns, and generates recommendations for new video creation.

## Architecture

Four-phase system with separate technology stacks:

1. **Phase 1 - Scraper (TypeScript)**: YouTube Data API v3 integration, stores in Firebase Firestore/Storage
2. **Phase 2 - Analyzer (Python)**: Gemini 2.5 Flash for thumbnail vision + hybrid local/LLM title+description analysis (2 API calls per video)
3. **Phase 3 - Insights (Python)**: Per-content-type feature profiling (all vs top 10% by viewsPerSubscriber) and content gap analysis
4. **Phase 4 - Recommender (TypeScript)**: AI-powered recommendation engine (CLI + Firebase Functions API)

**Data Flow**: Scraper → Firestore → Analyzer → Firestore → Insights → Firestore → Recommender

**Shared code**: `shared/` Python package provides base config classes (`BaseFirebaseConfig`, `BaseGeminiConfig`), env loading utilities, Firestore collection/analysis type constants, and Gemini model config. Used by both analyzer and insights phases.

## Project Structure

```
config/channels.json    # Input channel list (URL, category, priority, optional analysis_note)
data/batch/             # Batch mode JSONL request/result files (gitignored)
data/channels-review.csv
shared/                 # Python shared utilities (config, constants, firebase_utils, gemini_utils)
scraper/                # Phase 1 - TypeScript
analyzer/               # Phase 2 - Python (src/, tests/, scripts/)
insights/               # Phase 3 - Python (src/, tests/)
functions/              # Phase 4 - TypeScript (Firebase Functions)
```

`config/channels.json` defines all target channels with `url`, `category`, `priority` (1-3), and optional `analysis_note`. The `settings` block controls `maxVideosPerChannel`, `includeShorts`, `includePrivate`, and `skipShortThumbnails`.

## Setup

```bash
# Python dependencies (analyzer + insights)
pip3 install -r requirements.txt

# TypeScript dependencies
cd scraper && npm install
cd ../functions && npm install
```

## Commands

### Scraper (Phase 1)
```bash
cd scraper
npm start                       # Run scraper (full initial scrape)
npm start -- --update           # Incremental update (fetch only new videos for completed channels)
npm start -- --refresh          # Refresh stats (views, likes, comments) for all existing videos
npm start -- --update --refresh # Find new videos AND refresh all existing video stats
npm start -- --ignore-quota     # Ignore quota checks (use with caution)
npm test                        # Run vitest tests
npx tsx scripts/validate.ts     # Test API connections
npx tsx scripts/reset-progress.ts          # Clear progress for re-run
npx tsx scripts/check-status.ts            # Show scrape progress summary
npx tsx scripts/delete-short-thumbnails.ts # Remove thumbnails for Shorts from Storage
npx tsx scripts/migrate-unresolved.ts      # Retry unresolved channel URLs
```

### Analyzer (Phase 2)
```bash
cd analyzer

# Sync mode (default — per-video API calls)
python3 -m src.main --type thumbnail                                 # Thumbnail vision analysis only
python3 -m src.main --type title_description                         # Combined title+description text analysis only
python3 -m src.main --type title_description --channel CHANNEL_ID    # Specific channel
python3 -m src.main --limit 50                                       # Limit videos per channel
python3 -m src.main --validate                                       # Test connections only

# Batch mode (Gemini Batch API — 50% cost savings, works on all tiers)
python3 -m src.main --mode batch --type thumbnail                              # Full: prepare → submit → poll → import
python3 -m src.main --mode batch --type all                                    # Both analysis types
python3 -m src.main --mode batch --type title_description                      # Title+desc only (auto-picks all channels)
python3 -m src.main --mode batch --phase prepare --type thumbnail              # Only build JSONL file
python3 -m src.main --mode batch --phase submit --type thumbnail               # Submit prepared JSONL
python3 -m src.main --mode batch --phase poll --type thumbnail                 # Poll running job until done
python3 -m src.main --mode batch --phase import --type thumbnail               # Import completed results to Firestore
python3 -m src.main --mode batch --phase status                                # Show all batch job statuses
python3 -m src.main --mode batch --channel UCxxx --type thumbnail              # Single channel
python3 -m src.main --mode batch --phase prepare --type thumbnail --batch-size 10  # Small test batch

python3 -m pytest tests/                                                       # Run tests
```

### Insights (Phase 3)
```bash
cd insights
python3 -m src.main                    # Generate all insights (profiles + gaps)
python3 -m src.main --type profiles    # Per-content-type profiles only
python3 -m src.main --type gaps        # Content gap analysis only
python3 -m pytest tests/
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
- Channel URLs resolve via: `@handle` (1 unit), `/channel/UCxxx` (direct), `/user/` (1 unit), `/c/` (101 units - avoid)
- Uploads playlist ID: replace `UC` prefix with `UU` in channel ID
- Batch video details requests in groups of 50
- Use `mqdefault` thumbnail quality for storage efficiency
- Duration format is ISO 8601 (e.g., `PT15M33S`)
- Both scraper and analyzer track progress in Firestore for resumable operations
- Scraper supports `--update` mode for incremental fetching of new videos only
- Scraper skips short thumbnails when `skipShortThumbnails: true` in channels.json settings
- Unresolved channel URLs are tracked in Firestore for retry
- Recommender falls back to template-based generation if Gemini fails

## Testing

- **Scraper**: Vitest — `cd scraper && npm test` (tests in `scraper/tests/`)
- **Analyzer**: pytest — `cd analyzer && python3 -m pytest tests/` (fixtures in `conftest.py`)
- **Insights**: pytest — `cd insights && python3 -m pytest tests/` (fixtures in `conftest.py`)
- No linting/formatting tools are configured in this project

## Firebase Collections

- `channels/{channelId}` - Channel metadata and stats
- `channels/{channelId}/videos/{videoId}` - Video data with calculated metrics
- `channels/{channelId}/videos/{videoId}/analysis/{type}` - AI analysis results (thumbnail, title_description)
- `batch_jobs/{jobId}` - Batch API job tracking (state, request count, import status)
- `scrape_progress/{channelId}` - Resume state for interrupted scrapes
- `unresolved_channels/{id}` - Channel URLs that failed resolution (for retry)
- `insights/{contentType}` - Per-content-type profiles (thumbnail + title features, all vs top 10%)
- `insights/contentGaps` - Content gap and keyword opportunity analysis
- `insights/summary` - Overview of all content types and counts

## Calculated Video Metrics

The scraper calculates these performance/timing metrics for each video:
- `engagementRate`: ((likes + comments) / views) * 100
- `likeRatio`: (likes / views) * 100
- `commentRatio`: (comments / views) * 100
- `viewsPerDay`: views / days since publish
- `viewsPerSubscriber`: views / channel subscriber count
- `publishDayOfWeek`, `publishHourIST`: publish timing
- `tagCount`: number of tags

Text analysis fields (titleLength, hasEmoji, etc.) are computed by the analyzer's `local_text_features.py`, not the scraper.

## AI Analysis Models

All analysis uses Gemini 2.5 Flash (`gemini-2.5-flash`) with 2 API calls per video:

1. **Thumbnail** (vision call): Composition, colors, text, food, graphics, psychology (~109 fields, 100% Gemini)
2. **Title + Description** (hybrid local + LLM): ~134 total fields per video
   - **75 Gemini fields** (semantic): pattern recognition, transliteration, code-switching, power words, triggers, keywords, niche classification, content signals, recipe detection, SEO assessment, comment question
   - **59 local fields** (`local_text_features.py`): formatting (20), structure counts (8), language detection (8), hooks basics (3), desc structure/timestamps/hashtags/CTAs/links/monetization (20)
   - Local fields are computed via regex/Unicode detection (no API cost, no hallucination)
   - Both are merged into a single analysis document in Firestore

### Two Processing Modes

- **Sync mode** (default): Per-video API calls using `google-generativeai` SDK. Uses `response_schema` (Pydantic models) and `system_instruction` for structured JSON output. Local features computed inline and merged before saving.
- **Batch mode**: Gemini Batch API using `google-genai` SDK. Builds JSONL request files, submits as batch jobs, polls for completion, imports results. 50% cost savings. Works on all tiers but batch size is constrained by enqueued token limits (Tier 1: ~680 requests/job, Tier 2: ~90K requests/job). Local features computed during the import phase.

### Batch Mode Workflow

1. **Prepare**: Scans Firestore for unanalyzed videos, writes JSONL to `data/batch/`
2. **Submit**: Uploads JSONL via Files API, creates batch job, tracks in Firestore `batch_jobs`
3. **Poll**: Checks job status every 60s until terminal state (can be interrupted and resumed)
4. **Import**: Downloads result JSONL, parses each line, computes local features for title_description, merges, saves to Firestore analysis subcollections

Batch request key format: `{channelId}_{videoId}_{analysisType}` — parsed back using fixed-length channel IDs (24 chars starting with UC) and 11-char video IDs.

Thumbnails use GCS URIs (`gs://{bucket}/thumbnails/UCxxx/videoId.jpg`) directly in batch requests since Firebase Storage is Google Cloud Storage.

### Gemini API Tier Limits for Batch

| Tier | Enqueued Token Limit | Max requests per job | Jobs for 208K videos × 2 types |
|------|---------------------|---------------------|-------------------------------|
| Tier 1 | 3M tokens | ~680 | ~612 sequential jobs |
| Tier 2 | 400M tokens | ~50K (API max) | ~10 sequential jobs |
| Tier 3 | 1B tokens | ~50K (API max) | ~10 jobs, multiple concurrent |

Tier 2 requires: $250 cumulative Google Cloud spending + 30 days since first payment.

### Gemini Schema Budget

The `response_schema` has a hard constraint limit of ~13,500 chars of JSON schema.
- **Thumbnail**: 12,187 chars (tight but stable)
- **Title+Desc**: 8,092 chars (5,408 chars free after moving 59 fields to local computation)

Legacy analysis types (title, description, tags, content_structure) are no longer generated but may exist in Firestore from previous runs. The insights phase falls back to legacy `title` analysis when `title_description` is not available.
