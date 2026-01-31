# Phase 2: AI Analyzer

A Python-based AI analysis system that processes YouTube video data using Google Gemini 2.0 Flash. Performs 2 API calls per video: thumbnail vision analysis and combined title+description text analysis.

## Overview

| Type | Model | Input | Output |
|------|-------|-------|--------|
| **Thumbnail** | Gemini 2.0 Flash (Vision) | Image | ~109 composition/color/food/psychology attributes |
| **Title + Description** | Gemini 2.0 Flash (Text) | Title + Description text | ~140 structure/language/hooks/keywords/content signals + description SEO fields |

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Validate connections
python src/main.py --validate

# Run all analysis types
python src/main.py

# Run specific analysis
python src/main.py --type thumbnail
python src/main.py --type title_description --channel UCxxx --limit 50
```

## Architecture

```
analyzer/
├── requirements.txt
│
├── src/
│   ├── __init__.py
│   ├── main.py                        # Entry point with CLI
│   ├── config.py                      # Configuration management
│   ├── firebase_client.py             # Firebase operations
│   ├── gemini_client.py               # Gemini API wrapper
│   │
│   ├── analyzers/                     # Analysis modules
│   │   ├── __init__.py
│   │   ├── thumbnail.py               # Vision analysis
│   │   └── title_description.py       # Combined title+description text analysis
│   │
│   ├── processors/                    # Batch processing
│   │   ├── __init__.py
│   │   ├── batch.py                   # Batch orchestration
│   │   └── progress.py                # Progress tracking
│   │
│   └── prompts/                       # AI prompts
│       ├── __init__.py
│       ├── thumbnail_prompt.py        # Vision analysis prompt
│       └── title_description_prompt.py # Combined text analysis prompt
│
├── scripts/
│   └── run_thumbnail_analysis.py
│
└── tests/
    ├── __init__.py
    └── conftest.py                    # Pytest fixtures
```

## Core Components

### 1. Gemini Client

```python
# src/gemini_client.py
import google.generativeai as genai

model = genai.GenerativeModel(
    model_name='gemini-2.0-flash',
    generation_config={
        'temperature': 0.1,      # Low for consistent JSON output
        'top_p': 0.95,
        'max_output_tokens': 8192,
    }
)

# Vision analysis (thumbnails)
def analyze_image(prompt: str, image_data: bytes) -> Dict[str, Any]:
    image = Image.open(io.BytesIO(image_data))
    response = model.generate_content([prompt, image])
    return json.loads(response.text)

# Text analysis (title + description)
def analyze_text(prompt: str, text: str) -> Dict[str, Any]:
    response = model.generate_content(f"{prompt}\n\nText:\n{text}")
    return json.loads(response.text)
```

### 2. Thumbnail Analyzer

Extracts **~109 attributes** using vision AI across categories:

- **Composition**: Layout type, grid structure, complexity, focal point
- **Human Presence**: Face count, expression, eye contact, gestures
- **Text Elements**: Content, languages, Telugu script, position, readability
- **Colors**: Dominant colors with hex/percentage, palette, contrast
- **Food**: Dish identification, steam, presentation, appetite appeal (for cooking channels)
- **Graphics**: Arrows, badges, borders, effects
- **Psychology**: Curiosity gap, social proof, primary emotion
- **Scores**: Clickability, clarity, predicted CTR

### 3. Title + Description Analyzer

Single API call analyzing both title and description together. Description context improves niche detection (e.g., ingredient list confirms `isRecipe`).

**Title fields (~120)**: Structure, language mix, hooks, power words, keywords, content signals, Telugu-specific patterns

**Description fields (~20, lean)**: Structure, timestamps, recipe content, hashtags, CTAs, SEO signals

### 4. Batch Processor

```python
class BatchProcessor:
    def __init__(self, analysis_type: str):
        self.analysis_type = analysis_type
        self.analyzer = analyzers[analysis_type]
        self.progress = ProgressTracker(analysis_type)

    def process_channel(self, channel_id: str, limit: int = None):
        videos = get_unanalyzed_videos(channel_id, self.analysis_type, limit)
        for video in tqdm(videos):
            result = self._analyze_video(channel_id, video)
            time.sleep(config.REQUEST_DELAY)
```

## Command Line Interface

| Argument | Description | Default |
|----------|-------------|---------|
| `--type` | Analysis type: `all`, `thumbnail`, `title_description` | `all` |
| `--channel` | Specific channel ID to process | All channels |
| `--limit` | Max videos per channel | No limit |
| `--validate` | Test connections only | False |

## Data Storage

Analysis results are stored as Firestore subcollections:

```
channels/{channelId}/videos/{videoId}/analysis/
├── thumbnail           # Thumbnail vision analysis
└── title_description   # Combined title+description text analysis
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
| `google-generativeai` | >=0.3.0 | Gemini API client |
| `firebase-admin` | >=6.4.0 | Firebase Admin SDK |
| `Pillow` | >=10.2.0 | Image processing |
| `tqdm` | >=4.66.2 | Progress bars |
| `python-dotenv` | >=1.0.1 | Environment configuration |
