# Phase 2: AI Analyzer

A Python-based AI analysis system that processes YouTube video data using Google Gemini 2.0 Flash for comprehensive thumbnail, title, description, and tag analysis.

## Overview

The analyzer performs five types of AI analysis:

| Type | Model | Input | Output |
|------|-------|-------|--------|
| **Thumbnail** | Gemini 2.0 Flash (Vision) | Image | 50+ composition/color/psychology attributes |
| **Title** | Gemini 2.0 Flash | Text | Structure, language, hooks, keywords |
| **Description** | Gemini 2.0 Flash | Text | Timestamps, recipe content, CTAs, SEO |
| **Tags** | Gemini 2.0 Flash | Array | Categorization, strategy, search volume |
| **Content Structure** | Gemini 2.0 Flash | Text | Video structure, segments, talking points (ToS-compliant transcript alternative) |

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
python src/main.py --type title --channel UCxxx --limit 50
```

## Architecture

```
analyzer/
├── requirements.txt
│
├── src/
│   ├── __init__.py
│   ├── main.py                  # Entry point with CLI
│   ├── config.py                # Configuration management
│   ├── firebase_client.py       # Firebase operations
│   ├── gemini_client.py         # Gemini API wrapper
│   │
│   ├── analyzers/               # Analysis modules
│   │   ├── __init__.py
│   │   ├── thumbnail.py         # Vision analysis
│   │   ├── title.py             # Title text analysis
│   │   ├── description.py       # Description analysis
│   │   ├── tags.py              # Tag analysis
│   │   └── content_structure.py # Video structure inference
│   │
│   ├── processors/              # Batch processing
│   │   ├── __init__.py
│   │   ├── batch.py             # Batch orchestration
│   │   └── progress.py          # Progress tracking
│   │
│   └── prompts/                 # AI prompts
│       ├── __init__.py
│       ├── thumbnail_prompt.py  # 175-line detailed prompt
│       ├── title_prompt.py
│       ├── description_prompt.py
│       ├── tags_prompt.py
│       └── content_structure_prompt.py  # Video structure inference prompt
│
├── scripts/
│   ├── run_thumbnail_analysis.py
│   ├── run_title_analysis.py
│   ├── run_description_analysis.py
│   └── run_tag_analysis.py
│
└── tests/
    ├── __init__.py
    └── conftest.py              # Pytest fixtures
```

## Core Components

### 1. Gemini Client

```python
# src/gemini_client.py
import google.generativeai as genai

# Configuration
genai.configure(api_key=config.GOOGLE_API_KEY)

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

# Text analysis (titles, descriptions, tags)
def analyze_text(prompt: str, text: str) -> Dict[str, Any]:
    response = model.generate_content(f"{prompt}\n\nText:\n{text}")
    return json.loads(response.text)
```

### 2. Thumbnail Analyzer

The thumbnail analyzer extracts **50+ attributes** using vision AI:

```python
# Analysis categories
{
    "composition": {
        "layoutType": "split-screen|single-focus|collage|text-heavy|minimal",
        "gridStructure": "rule-of-thirds|centered|asymmetric",
        "complexity": "simple|medium|complex|cluttered",
        "focalPoint": "description of main focus",
    },
    "humanPresence": {
        "facePresent": True/False,
        "faceCount": 1,
        "expression": "surprised|happy|curious|neutral",
        "eyeContact": True/False,
        "handGesture": "pointing|thumbs-up|holding-item|none",
    },
    "textElements": {
        "hasText": True/False,
        "languages": ["english", "telugu"],
        "hasTeluguScript": True/False,
        "primaryText": {"content": "...", "position": "...", "color": "#HEX"},
    },
    "colors": {
        "dominantColors": [{"hex": "#FF6B35", "name": "orange", "percentage": 35}],
        "palette": "warm|cool|neutral",
        "contrast": "low|medium|high",
    },
    "food": {  # For cooking channels
        "foodPresent": True/False,
        "mainDish": "dish name",
        "steam": True/False,
        "appetiteAppeal": 1-10,
    },
    "psychology": {
        "curiosityGap": True/False,
        "socialProof": True/False,
        "primaryEmotion": "curiosity|excitement|appetite",
    },
    "scores": {
        "clickability": 1-10,
        "clarity": 1-10,
        "predictedCTR": "below-average|average|above-average",
    }
}
```

### 3. Title Analyzer

```python
{
    "structure": {
        "pattern": "dish-name | translation | modifier",
        "segments": [
            {"text": "Biryani Recipe", "type": "dish-name", "language": "english"},
            {"text": "బిర్యానీ", "type": "translation", "language": "telugu"}
        ],
        "characterCount": 67,
    },
    "language": {
        "languages": ["english", "telugu"],
        "primaryLanguage": "english",
        "teluguRatio": 0.18,
        "codeSwitch": True,
    },
    "hooks": {
        "hasPowerWord": True,
        "powerWords": ["SECRET", "Restaurant Style"],
        "triggers": {"curiosityGap": True, "socialProof": False},
        "hookStrength": "weak|moderate|strong|viral",
    },
    "keywords": {
        "primaryKeyword": "Biryani Recipe",
        "searchIntent": "how-to|review|comparison",
        "seoOptimized": True,
    },
    "scores": {
        "seoScore": 8.5,
        "clickabilityScore": 7.0,
        "overallScore": 7.5,
    }
}
```

### 4. Batch Processor

```python
# src/processors/batch.py
class BatchProcessor:
    def __init__(self, analysis_type: str):
        self.analysis_type = analysis_type
        self.analyzer = self._get_analyzer()
        self.progress = ProgressTracker()

    def process_channel(self, channel_id: str, limit: int = None):
        """Process all unanalyzed videos for a channel."""
        videos = get_unanalyzed_videos(channel_id, self.analysis_type, limit)

        for video in tqdm(videos, desc=f"Analyzing {channel_id}"):
            try:
                result = self.analyzer.analyze(video)
                save_analysis(channel_id, video['videoId'], self.analysis_type, result)
                self.progress.record_success()
            except Exception as e:
                self.progress.record_failure(str(e))

            time.sleep(config.REQUEST_DELAY)  # Rate limiting

    def process_all_channels(self, limit: int = None):
        """Process all channels."""
        channels = get_all_channels()
        for channel in channels:
            self.process_channel(channel['channelId'], limit)
```

## Command Line Interface

### Basic Usage

```bash
# Run all analysis types on all channels
python src/main.py

# Run specific analysis type
python src/main.py --type thumbnail
python src/main.py --type title
python src/main.py --type description
python src/main.py --type tags
python src/main.py --type content_structure

# Process specific channel
python src/main.py --type thumbnail --channel UCBSwcE0p0PMwhvE6FVjgITw

# Limit videos per channel
python src/main.py --type thumbnail --limit 50

# Validate connections only (dry run)
python src/main.py --validate
```

### CLI Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--type` | Analysis type: `all`, `thumbnail`, `title`, `description`, `tags`, `content_structure` | `all` |
| `--channel` | Specific channel ID to process | All channels |
| `--limit` | Max videos per channel | No limit |
| `--validate` | Test connections only | False |

## Configuration

### Environment Variables

```bash
# Gemini API (required)
GOOGLE_API_KEY=your_gemini_api_key

# Firebase (required)
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_CLIENT_EMAIL=firebase-adminsdk@your-project.iam.gserviceaccount.com
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
FIREBASE_STORAGE_BUCKET=your-project.appspot.com

# Optional settings
BATCH_SIZE=10              # Videos per batch
REQUEST_DELAY=0.5          # Seconds between API calls
RETRY_DELAY=1.0            # Seconds before retry
MAX_RETRIES=3              # Max retry attempts
```

### Config Class

```python
# src/config.py
class Config:
    GOOGLE_API_KEY: str
    GEMINI_MODEL: str = 'gemini-2.0-flash'

    FIREBASE_PROJECT_ID: str
    FIREBASE_CLIENT_EMAIL: str
    FIREBASE_PRIVATE_KEY: str
    FIREBASE_STORAGE_BUCKET: str

    BATCH_SIZE: int = 10
    MAX_RETRIES: int = 3
    RETRY_DELAY: float = 1.0
    REQUEST_DELAY: float = 0.5
```

## Data Storage

### Analysis Results Location

Analysis results are stored as Firestore subcollections:

```
channels/{channelId}/videos/{videoId}/analysis/
├── thumbnail         # Thumbnail analysis
├── title             # Title analysis
├── description       # Description analysis
├── tags              # Tag analysis
└── content_structure # Video structure inference
```

### Example Document

```python
# channels/{channelId}/videos/{videoId}/analysis/thumbnail
{
    "analyzedAt": "2024-01-25T10:30:00Z",
    "modelUsed": "gemini-2.0-flash",
    "analysisVersion": "1.0",

    "composition": {...},
    "humanPresence": {...},
    "textElements": {...},
    "colors": {...},
    "food": {...},
    "graphics": {...},
    "psychology": {...},
    "scores": {...}
}
```

## Progress Tracking

The analyzer tracks which videos have been analyzed:

```python
# Check if already analyzed
has_analysis(channel_id, video_id, 'thumbnail')  # Returns True/False

# Save analysis (skips if exists unless force=True)
save_analysis(channel_id, video_id, 'thumbnail', result, force=False)
```

Progress is tracked in:
- Console output with tqdm progress bars
- Firestore `analysis_progress/{type}` collection

## Error Handling

### Retry Logic

```python
def analyze_with_retry(analyzer, video, max_retries=3):
    for attempt in range(max_retries):
        try:
            return analyzer.analyze(video)
        except json.JSONDecodeError:
            # Gemini returned invalid JSON
            logger.warning(f"Invalid JSON, retry {attempt + 1}")
        except Exception as e:
            logger.error(f"Analysis failed: {e}")

        time.sleep(config.RETRY_DELAY * (attempt + 1))

    return None  # Mark as failed
```

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `InvalidAPIKey` | Wrong GOOGLE_API_KEY | Verify API key |
| `RateLimitExceeded` | Too many requests | Increase REQUEST_DELAY |
| `JSONDecodeError` | Gemini returned non-JSON | Automatic retry |
| `ImageTooLarge` | Thumbnail too big | Should not occur with mqdefault |
| `FirebaseError` | Connection issue | Check credentials |

## Performance

### Estimated Processing Times

| Videos | Thumbnail (Vision) | Title/Desc/Tags (Text) |
|--------|-------------------|------------------------|
| 1,000 | ~2 hours | ~30 minutes each |
| 10,000 | ~20 hours | ~5 hours each |
| 50,000 | ~4 days | ~1 day each |

### Rate Limits

- Gemini API: 60 requests/minute (free tier)
- Recommended `REQUEST_DELAY`: 0.5-1.0 seconds

### Memory Usage

- Each thumbnail: ~50-100 KB
- Batch processing: ~100 MB peak
- Recommend: 4 GB RAM minimum

## Testing

```bash
# Run all tests
pytest tests/

# Run specific test
pytest tests/test_analyzers.py

# Run with verbose output
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src
```

### Test Fixtures

```python
# tests/conftest.py
@pytest.fixture
def sample_video():
    return {
        'videoId': 'test123',
        'channelId': 'UCtest',
        'title': 'Test Video | టెస్ట్',
        'description': 'Test description...',
        'tags': ['test', 'video'],
        'thumbnailStoragePath': 'thumbnails/UCtest/test123.jpg'
    }

@pytest.fixture
def mock_gemini():
    with patch('src.gemini_client.model') as mock:
        yield mock
```

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `google-generativeai` | >=0.3.0 | Gemini API client |
| `firebase-admin` | >=6.4.0 | Firebase Admin SDK |
| `Pillow` | >=10.2.0 | Image processing |
| `tqdm` | >=4.66.2 | Progress bars |
| `python-dotenv` | >=1.0.1 | Environment configuration |
| `pytest` | >=8.0.0 | Testing |

## Prompt Engineering

### Thumbnail Prompt Structure

The thumbnail prompt (`src/prompts/thumbnail_prompt.py`) is 175 lines and requests:

1. **Composition analysis**: Layout, grid, balance, complexity
2. **Human presence**: Face, expression, eye contact, gestures
3. **Text elements**: Content, language, position, readability
4. **Color analysis**: Dominant colors, palette, contrast
5. **Food analysis**: Dish, presentation, appeal (for cooking)
6. **Graphics**: Arrows, badges, borders, effects
7. **Psychology**: Triggers, emotions, click motivation
8. **Quality**: Resolution, sharpness, lighting
9. **Scores**: Clickability, clarity, professionalism, CTR prediction

All responses must be valid JSON for consistent parsing.

## Troubleshooting

### "Rate limit exceeded"
- Increase `REQUEST_DELAY` to 1.0 or higher
- Use batch processing with smaller batches

### "Invalid JSON from Gemini"
- Automatic retry handles this
- If persistent, check prompt formatting

### "Thumbnail not found"
- Verify thumbnails were downloaded in Phase 1
- Check `thumbnailStoragePath` in video document

### Memory issues
- Reduce `BATCH_SIZE`
- Process one channel at a time

## Next Steps

After analysis completes:
1. Verify results in Firebase Console
2. Check for failed analyses
3. Proceed to **Phase 3: Insights** for pattern discovery

---

For detailed schemas, see [Technical Documentation](../docs/TECHNICAL_DOCUMENTATION.md).
