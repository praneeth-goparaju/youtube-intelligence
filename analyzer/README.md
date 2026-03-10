# Phase 2: AI Analyzer

A Python-based AI analysis system that processes YouTube video data using Google Gemini 2.5 Flash. Performs 2 API calls per video: thumbnail vision analysis and combined title+description text analysis.

Supports two processing modes:
- **Sync mode** (default): Per-video API calls with structured output via `response_schema`
- **Batch mode**: Gemini Batch API for 50% cost savings (works on all paid tiers)

## Overview

| Type | Model | Input | Output |
|------|-------|-------|--------|
| **Thumbnail** | Gemini 2.5 Flash (Vision) | Image | ~132 composition/color/food/psychology attributes |
| **Title + Description** | Gemini 2.5 Flash (Text) | Title + Description text | ~135 structure/language/hooks/keywords/content signals + description SEO fields |

## Quick Start

```bash
# Install dependencies (from project root)
pip3 install -r requirements.txt   # run from project root, or ../requirements.txt from analyzer/

# Validate connections
python3 -m src.main --validate

# Sync mode (default)
python3 -m src.main                                          # All analysis types
python3 -m src.main --type thumbnail                         # Thumbnail only
python3 -m src.main --type title_description --channel UCxxx --limit 50

# Batch mode (50% cost savings)
python3 -m src.main --mode batch --type thumbnail            # Full pipeline
python3 -m src.main --mode batch --phase prepare --type thumbnail --batch-size 10  # Test batch
python3 -m src.main --mode batch --phase status              # Check job statuses
```

## Architecture

```
analyzer/
├── src/
│   ├── __init__.py
│   ├── main.py                        # Entry point with CLI (sync + batch routing)
│   ├── config.py                      # Configuration management
│   ├── firebase_client.py             # Firebase operations + batch_jobs CRUD
│   ├── gemini_client.py               # Gemini API wrapper (response_schema support)
│   │
│   ├── analyzers/                     # Per-video analysis modules (sync mode)
│   │   ├── __init__.py
│   │   ├── thumbnail.py               # Vision analysis
│   │   └── title_description.py       # Combined title+description text analysis
│   │
│   ├── batch_api/                     # Gemini Batch API integration
│   │   ├── __init__.py
│   │   ├── schemas.py                 # Pydantic models for response_schema
│   │   ├── client.py                  # google-genai SDK wrapper
│   │   ├── prepare.py                 # Build JSONL request files
│   │   ├── submit.py                  # Submit jobs + track in Firestore
│   │   └── import_results.py          # Download results + save to Firestore
│   │
│   ├── processors/                    # Sync mode batch orchestration
│   │   ├── __init__.py
│   │   ├── batch.py                   # Channel/video iteration
│   │   └── progress.py                # Progress tracking
│   │
│   └── prompts/                       # AI prompts
│       ├── __init__.py
│       ├── thumbnail_prompt.py        # Vision analysis prompt + system instruction
│       └── title_description_prompt.py # Text analysis prompt + system instruction
│
├── scripts/
│   └── run_thumbnail_analysis.py
│
└── tests/
    ├── __init__.py
    └── conftest.py                    # Pytest fixtures
```

## Processing Modes

### Sync Mode (default)

Per-video API calls using the `google-generativeai` SDK. Each video is processed sequentially with 0.5s delay between calls for rate limiting.

Both sync and batch modes use:
- **`response_schema`**: Pydantic models (`ThumbnailAnalysisSchema`, `TitleDescriptionAnalysisSchema`) guarantee valid JSON output
- **`system_instruction`**: Concise role/domain context set on the model
- **User prompts**: Shorter analysis instructions (no JSON template needed since schema enforces structure)

```bash
python3 -m src.main --type thumbnail
python3 -m src.main --type title_description --channel UCxxx --limit 50
```

### Batch Mode (Gemini Batch API)

Submits all requests as a JSONL file to the Gemini Batch API. Google processes them asynchronously (hours). 50% cheaper than sync because Google schedules work during low-demand periods.

Works on all paid tiers. Tier 1 has a 3M enqueued token limit (~680 requests per job), so you process in smaller batches. Tier 2+ allows up to 50K requests per job.

#### 4-Phase Workflow

```
PREPARE → SUBMIT → POLL → IMPORT
```

| Phase | What it does | Duration |
|-------|-------------|----------|
| `prepare` | Scans Firestore for unanalyzed videos, writes JSONL to `data/batch/` | Minutes |
| `submit` | Uploads JSONL to Gemini Files API, creates batch job, tracks in Firestore `batch_jobs` | Seconds |
| `poll` | Checks job status every 60s until terminal state | Hours |
| `import` | Downloads result JSONL, parses results, saves to Firestore | Minutes |
| `status` | Shows all tracked batch jobs and states | Instant |

#### Usage

```bash
# Run all phases sequentially (blocks during poll)
python3 -m src.main --mode batch --type thumbnail

# Or run phases individually (recommended for production)
python3 -m src.main --mode batch --phase prepare --type thumbnail
python3 -m src.main --mode batch --phase submit --type thumbnail
# ... go do something else, come back later ...
python3 -m src.main --mode batch --phase status
python3 -m src.main --mode batch --phase poll --type thumbnail
python3 -m src.main --mode batch --phase import --type thumbnail
```

#### Batch API Limits

- 50,000 requests per job
- 2GB input file size
- 100 concurrent batch jobs

Enqueued token limits by tier:

| Tier | Limit | Max requests per job | Notes |
|------|-------|---------------------|-------|
| Tier 1 | 3M tokens | ~680 | Use `--batch-size 680`, more jobs needed |
| Tier 2 | 400M tokens | ~50K (API max) | One 50K job at a time |
| Tier 3 | 1B tokens | ~50K (API max) | Multiple concurrent jobs |

#### Resume Support

Job state is tracked in Firestore `batch_jobs` collection. If interrupted during polling, re-run `--phase poll` to find and resume monitoring the latest active job.

## Command Line Interface

| Argument | Description | Default |
|----------|-------------|---------|
| `--type`, `-t` | Analysis type: `all`, `thumbnail`, `title_description` | `all` |
| `--channel`, `-c` | Specific channel ID to process | All channels |
| `--limit`, `-l` | Max videos per channel (sync mode) | No limit |
| `--validate` | Test connections only | False |
| `--mode`, `-m` | Processing mode: `sync`, `batch` | `sync` |
| `--phase` | Batch phase: `all`, `prepare`, `submit`, `poll`, `import`, `status` | `all` |
| `--batch-size` | Max requests per batch job | `25` |
| `--poll-interval` | Seconds between poll checks | `60` |
| `--job-name` | Specific batch job name to poll/import | Auto-detect latest |
| `--loop` | Loop batch jobs until all videos analyzed | False |

## Data Storage

Analysis results are stored as Firestore subcollections:

```
channels/{channelId}/videos/{videoId}/analysis/
├── thumbnail           # Thumbnail vision analysis (analysisVersion: "1.0")
└── title_description   # Combined title+description text analysis (analysisVersion: "2.0")

batch_jobs/{jobId}          # Batch job tracking (state, request count, import status)
analysis_progress/{type}    # Sync mode progress tracking (saves every 10 records)
```

Legacy analysis types (`title`, `description`, `tags`, `content_structure`) may exist in Firestore from previous runs but are no longer generated. The insights phase falls back to legacy `title` analysis when `title_description` is not available.

## Configuration

### Environment Variables

```bash
GOOGLE_API_KEY=your_gemini_api_key
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_CLIENT_EMAIL=firebase-adminsdk@your-project.iam.gserviceaccount.com
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
FIREBASE_STORAGE_BUCKET=your-project.appspot.com

# Optional
BATCH_SIZE=10                    # Videos per sync processing batch (default: 10)
BATCH_POLL_INTERVAL=60           # Seconds between batch job poll checks (default: 60)
```

## Testing

```bash
pytest tests/
pytest tests/ -v
pytest tests/ --cov=src
```

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `google-generativeai` | >=0.3.0 | Gemini API client (sync mode) |
| `google-genai` | >=1.0.0 | Gemini API client (batch mode) |
| `pydantic` | >=2.0.0 | Response schema models |
| `firebase-admin` | >=6.4.0 | Firebase Admin SDK |
| `Pillow` | >=10.2.0 | Image processing |
| `tqdm` | >=4.66.2 | Progress bars |
| `python-dotenv` | >=1.0.1 | Environment configuration |
