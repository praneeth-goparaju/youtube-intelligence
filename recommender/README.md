# Phase 4: Recommendation Engine

A recommendation system that generates data-driven suggestions for new YouTube videos based on discovered patterns and AI generation.

## Overview

The recommender generates actionable video recommendations:

| Component | Source | Output |
|-----------|--------|--------|
| **Titles** | Patterns + Gemini AI | Primary + alternatives with reasoning |
| **Thumbnails** | Pattern insights | Layout, elements, colors specification |
| **Tags** | Keyword analysis | Categorized tags with search estimates |
| **Posting Time** | Timing insights | Optimal day/hour with alternatives |
| **Prediction** | Statistical model | Expected view range with factors |

## Usage Options

You have **two ways** to use the recommendation engine:

| Option | Best For | Technology | Response Time |
|--------|----------|------------|---------------|
| **Python CLI** | Local scripts, batch processing, development | Python | 5-10 seconds |
| **Firebase Functions API** | Web apps, mobile apps, REST API | TypeScript | 2-5 seconds |

### Option 1: Python CLI

Run recommendations locally from the command line:

```bash
cd recommender
python src/main.py --topic "Biryani" --type recipe --output recommendation.json
```

**Advantages:**
- Full control over execution
- Easy debugging and development
- Works offline (except for Gemini API calls)
- Good for batch processing multiple topics

### Option 2: Firebase Functions API

Access recommendations via HTTP REST API or Firebase SDK:

```bash
# REST API
curl -X POST https://us-central1-YOUR_PROJECT.cloudfunctions.net/recommend \
  -H "Content-Type: application/json" \
  -d '{"topic": "Biryani", "type": "recipe"}'
```

```typescript
// Firebase SDK (JavaScript/TypeScript)
import { getFunctions, httpsCallable } from 'firebase/functions';

const functions = getFunctions();
const getRecommendation = httpsCallable(functions, 'getRecommendation');
const result = await getRecommendation({ topic: 'Biryani', type: 'recipe' });
```

**Advantages:**
- No local setup required (after deployment)
- Easy integration with web/mobile apps
- Scalable serverless architecture
- Consistent API for any client

See [functions/README.md](../functions/README.md) for complete API documentation.

---

## Quick Start (Python CLI)

```bash
# Install dependencies
pip install -r requirements.txt

# Generate a recommendation
python src/main.py \
  --topic "Hyderabadi Biryani" \
  --type recipe \
  --angle "Restaurant secret recipe" \
  --audience "Telugu home cooks" \
  --output recommendation.json
```

## Architecture

```
recommender/
├── requirements.txt
│
├── src/
│   ├── __init__.py
│   ├── main.py              # CLI entry point
│   ├── config.py            # Configuration
│   ├── firebase_client.py   # Firebase operations
│   │
│   ├── engine.py            # Main recommendation logic
│   └── templates.py         # Fallback title/thumbnail templates
│
├── examples/
│   └── sample_queries.json  # Example inputs and outputs
│
└── tests/
    └── test_engine.py
```

## Core Components

### 1. Recommendation Engine

```python
# src/engine.py
class RecommendationEngine:
    def __init__(self):
        self.insights = None
        self.model = self._init_gemini()

    def generate_recommendation(
        self,
        topic: str,
        content_type: str = 'recipe',
        unique_angle: str = None,
        target_audience: str = 'telugu-audience'
    ) -> Dict:
        """Generate a complete video recommendation."""

        # 1. Load insights from Firestore
        self.insights = get_all_insights()

        # 2. Build context from patterns
        context = self._build_context()

        # 3. Generate with Gemini AI
        try:
            prompt = self._build_prompt(
                topic, content_type, unique_angle,
                target_audience, context
            )
            response = self.model.generate_content(prompt)
            recommendation = json.loads(response.text)
        except Exception:
            # 4. Fallback to templates if AI fails
            recommendation = self._generate_from_templates(
                topic, content_type
            )

        # 5. Add posting recommendation
        recommendation['posting'] = self._get_posting_recommendation()

        # 6. Add performance prediction
        recommendation['prediction'] = self._predict_performance(
            recommendation, topic
        )

        return recommendation
```

### 2. Context Building

The engine builds context from Phase 3 insights:

```python
def _build_context(self) -> str:
    """Build context string from insights."""
    context_parts = []

    # Top thumbnail elements
    if 'thumbnails' in self.insights:
        top_elements = self.insights['thumbnails']['topPerformingElements']
        context_parts.append("Top performing thumbnail elements:")
        for category, elements in top_elements.items():
            for elem in elements[:3]:
                context_parts.append(
                    f"  - {elem['element']} ({elem['lift']}x performance)"
                )

    # Power words
    if 'titles' in self.insights:
        power_words = self.insights['titles']['powerWords']['highImpact']
        context_parts.append("\nTop power words:")
        for pw in power_words[:5]:
            context_parts.append(f"  - {pw['word']} / {pw['telugu']}")

    # Optimal timing
    if 'timing' in self.insights:
        optimal = self.insights['timing']['bestTimes']['optimal']
        context_parts.append(
            f"\nOptimal posting: {optimal['day']} at {optimal['hourIST']}:00 IST"
        )

    # Content gaps
    if 'contentGaps' in self.insights:
        gaps = self.insights['contentGaps']['highOpportunity'][:3]
        context_parts.append("\nHigh opportunity topics:")
        for gap in gaps:
            context_parts.append(
                f"  - {gap['topic']} (score: {gap['opportunityScore']:.0f})"
            )

    return '\n'.join(context_parts)
```

### 3. Template Fallback

When AI generation fails, templates provide basic recommendations:

```python
# src/templates.py
TITLE_TEMPLATES = {
    'recipe': [
        "{dish} Recipe | {dish_telugu} | {modifier}",
        "{modifier} {dish} | {dish_telugu} | Restaurant Style",
        "SECRET {dish} Recipe | {dish_telugu} రహస్యం",
    ],
    'vlog': [
        "My {topic} Experience | {topic_telugu}",
        "A Day in {location} | {topic_telugu}",
    ],
    'tutorial': [
        "How to {topic} | {topic_telugu} | Complete Guide",
        "{topic} for Beginners | {topic_telugu}",
    ],
}

THUMBNAIL_SPECS = {
    'recipe': {
        'layout': 'split-composition',
        'face': {
            'position': 'right-third',
            'expression': 'surprised',
            'required': True
        },
        'food': {
            'position': 'left-center',
            'style': 'close-up with steam',
            'required': True
        },
        'colors': {
            'background': '#FF6B35',
            'accent': '#FFFF00',
            'text': '#FFFFFF'
        }
    }
}

POWER_WORDS = {
    'telugu': ['రహస్యం', 'పర్ఫెక్ట్', 'అసలైన', 'హోటల్ స్టైల్'],
    'english': ['SECRET', 'PERFECT', 'AUTHENTIC', 'Restaurant Style']
}
```

## Command Line Interface

### Arguments

| Argument | Description | Required | Default |
|----------|-------------|----------|---------|
| `--topic` | Video topic | Yes | - |
| `--type` | Content type: `recipe`, `vlog`, `tutorial`, `review`, `challenge` | No | `recipe` |
| `--angle` | Unique positioning angle | No | None |
| `--audience` | Target audience | No | `telugu-audience` |
| `--output` | Output JSON file path | No | stdout |

### Examples

```bash
# Basic recipe recommendation
python src/main.py --topic "Chicken Biryani"

# With unique angle and audience
python src/main.py \
  --topic "Hyderabadi Biryani" \
  --type recipe \
  --angle "Restaurant secret recipe" \
  --audience "Telugu home cooks"

# Save to file
python src/main.py \
  --topic "Biryani" \
  --output recommendation.json

# Different content types
python src/main.py --topic "Germany Trip" --type vlog
python src/main.py --topic "Python Programming" --type tutorial
```

## Output Schema

### Complete Recommendation

```json
{
  "titles": {
    "primary": {
      "english": "Restaurant Style Hyderabadi Biryani | BEST Recipe",
      "telugu": "హోటల్ స్టైల్ హైదరాబాదీ బిర్యానీ",
      "combined": "Hyderabadi Biryani | హైదరాబాదీ బిర్యానీ | Restaurant Style",
      "predictedCTR": "above-average",
      "reasoning": "Combines high-search keyword with quality modifier"
    },
    "alternatives": [
      {
        "title": "SECRET Biryani Recipe | బిర్యానీ రహస్యం",
        "predictedCTR": "high",
        "reasoning": "Uses power word SECRET with Telugu translation"
      },
      {
        "title": "Biryani with German Ingredients?! | Telugu",
        "predictedCTR": "medium-high",
        "reasoning": "Curiosity hook with unique fusion angle"
      }
    ]
  },

  "thumbnail": {
    "layout": {
      "type": "split-composition",
      "description": "Face on right third, biryani on left with steam"
    },
    "elements": {
      "face": {
        "required": true,
        "expression": "surprised or excited",
        "position": "right-third",
        "size": "large",
        "eyeContact": true
      },
      "mainVisual": {
        "type": "biryani-close-up",
        "position": "left-center",
        "showSteam": true,
        "garnished": true
      },
      "text": {
        "primary": {
          "content": "SECRET",
          "position": "top-left",
          "color": "#FFFF00",
          "style": "bold-with-outline"
        },
        "secondary": {
          "content": "బిర్యానీ రహస్యం",
          "language": "telugu",
          "position": "bottom"
        }
      },
      "graphics": {
        "addArrow": true,
        "arrowPointTo": "food",
        "addBorder": true,
        "borderColor": "#FFFFFF"
      }
    },
    "colors": {
      "background": "#FF6B35",
      "accent": "#FFFF00",
      "text": "#FFFFFF"
    },
    "referenceExamples": [
      {"videoId": "xxx", "reason": "Similar layout with 5M views"}
    ]
  },

  "tags": {
    "primary": [
      "biryani recipe",
      "hyderabadi biryani",
      "biryani recipe in telugu"
    ],
    "secondary": [
      "restaurant style biryani",
      "dum biryani",
      "chicken biryani recipe"
    ],
    "telugu": [
      "బిర్యానీ",
      "హైదరాబాదీ బిర్యానీ",
      "తెలుగు వంటకం"
    ],
    "longtail": [
      "how to make biryani at home",
      "easy biryani recipe for beginners"
    ],
    "brand": [
      "your_channel_name",
      "your_channel_name biryani"
    ],
    "fullTagString": "biryani recipe, hyderabadi biryani, ...",
    "characterCount": 487,
    "utilizationPercent": 97.4
  },

  "posting": {
    "bestDay": "Saturday",
    "bestTime": "18:00 IST",
    "alternativeTimes": [
      "Sunday 12:00 IST",
      "Friday 19:00 IST"
    ],
    "reasoning": "Weekend evening maximizes Telugu audience viewership"
  },

  "prediction": {
    "expectedViewRange": {
      "low": 15000,
      "medium": 45000,
      "high": 120000
    },
    "confidence": "medium",
    "positiveFactors": [
      "High-search keyword (biryani)",
      "Optimal thumbnail elements",
      "Power word in title"
    ],
    "riskFactors": [
      "High competition in biryani niche",
      "Saturated topic"
    ]
  },

  "content": {
    "optimalDuration": "12-15 minutes",
    "mustInclude": [
      "Ingredient list with measurements",
      "Step-by-step with timestamps",
      "Final reveal with steam shot",
      "Taste test reaction"
    ],
    "hooks": [
      "Start with final dish reveal",
      "Mention 'secret' or 'restaurant trick' in first 30 seconds"
    ],
    "description": {
      "template": "[Provided template]",
      "mustInclude": ["timestamps", "ingredients", "social links", "CTAs"]
    }
  }
}
```

## Configuration

### Environment Variables

```bash
# Gemini API (required for AI generation)
GOOGLE_API_KEY=your_gemini_api_key

# Firebase (required)
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_CLIENT_EMAIL=firebase-adminsdk@your-project.iam.gserviceaccount.com
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
```

### Config Class

```python
class Config:
    # Gemini
    GOOGLE_API_KEY: str
    GEMINI_MODEL: str = 'gemini-2.0-flash'

    # Firebase
    FIREBASE_PROJECT_ID: str
    FIREBASE_CLIENT_EMAIL: str
    FIREBASE_PRIVATE_KEY: str
```

## Data Dependencies

The recommender requires:
1. **Insights data** (Phase 3 complete)
   - `insights/thumbnails`
   - `insights/titles`
   - `insights/timing`
   - `insights/contentGaps`

Without insights, only template-based recommendations are available.

## AI Generation

### Prompt Structure

```
You are a YouTube video optimization expert specializing in Telugu content.

Based on the following performance patterns from successful Telugu videos:
{context}

Generate a complete recommendation for a video about:
Topic: {topic}
Content Type: {content_type}
Unique Angle: {unique_angle}
Target Audience: {target_audience}

Provide recommendations for:
1. Titles (primary + 2 alternatives)
2. Thumbnail specification
3. Tags (categorized)
4. Content structure

Output as valid JSON matching this schema:
{schema}
```

### Model Configuration

```python
generation_config = {
    'temperature': 0.7,     # Higher for creative suggestions
    'top_p': 0.95,
    'max_output_tokens': 4096,
}
```

## Fallback Behavior

If Gemini API fails:
1. Engine catches the exception
2. Generates recommendation from templates
3. Adds posting time from insights (if available)
4. Returns template-based recommendation

This ensures the engine always returns something useful.

## Testing

```bash
# Run tests
pytest tests/

# Test specific module
pytest tests/test_engine.py

# Run with coverage
pytest tests/ --cov=src
```

### Test Examples

```python
def test_recommendation_structure():
    """Verify recommendation has all required fields."""
    engine = RecommendationEngine()
    result = engine.generate_recommendation(
        topic="Test Recipe",
        content_type="recipe"
    )

    assert 'titles' in result
    assert 'thumbnail' in result
    assert 'tags' in result
    assert 'posting' in result

def test_fallback_generation():
    """Test template fallback when AI fails."""
    engine = RecommendationEngine()
    result = engine._generate_from_templates(
        topic="Biryani",
        content_type="recipe"
    )

    assert result['titles']['primary'] is not None
```

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `google-generativeai` | >=0.3.0 | Gemini API client |
| `firebase-admin` | >=6.4.0 | Firebase SDK |
| `python-dotenv` | >=1.0.1 | Environment config |

## Performance

- **Response time**: 5-10 seconds (with AI generation)
- **Fallback response**: < 1 second
- **Memory usage**: ~100 MB

## Sample Queries

See `examples/sample_queries.json` for example inputs:

```json
{
  "queries": [
    {
      "topic": "Hyderabadi Biryani",
      "type": "recipe",
      "angle": "Restaurant secret",
      "audience": "Telugu home cooks"
    },
    {
      "topic": "Germany Trip",
      "type": "vlog",
      "angle": "Telugu NRI perspective",
      "audience": "Telugu NRIs"
    }
  ]
}
```

## Integration

### Programmatic Usage

```python
from src.engine import RecommendationEngine

engine = RecommendationEngine()

recommendation = engine.generate_recommendation(
    topic="Chicken Biryani",
    content_type="recipe",
    unique_angle="Restaurant secret",
    target_audience="Telugu home cooks"
)

# Access specific parts
print(recommendation['titles']['primary']['combined'])
print(recommendation['posting']['bestDay'])
print(recommendation['prediction']['expectedViewRange'])
```

### Firebase Functions API

A production-ready API is available via Firebase Functions. See [functions/README.md](../functions/README.md) for:

- **REST API**: `POST /recommend` endpoint for any HTTP client
- **Callable Function**: `getRecommendation` for Firebase SDK integration
- **Health Check**: `GET /health` endpoint for monitoring

**Quick API Example:**

```bash
# Deploy the API
cd functions
npm install
firebase functions:secrets:set GOOGLE_API_KEY
npm run deploy

# Use the API
curl -X POST https://us-central1-YOUR_PROJECT.cloudfunctions.net/recommend \
  -H "Content-Type: application/json" \
  -d '{"topic": "Biryani", "type": "recipe"}'
```

The TypeScript Firebase Functions implementation mirrors the Python engine, providing identical recommendations with the same fallback behavior.

---

For detailed documentation, see [Technical Documentation](../docs/TECHNICAL_DOCUMENTATION.md).
