# Phase 3: Pattern Discovery & Insights

A Python-based analytics system that performs statistical analysis on AI-analyzed YouTube data to discover patterns that correlate with high video performance.

## Overview

The insights module performs four types of analysis:

| Type | Method | Output |
|------|--------|--------|
| **Thumbnail Insights** | Correlation + Pattern Extraction | Elements that drive views |
| **Title Insights** | Pattern Analysis | Winning title structures |
| **Timing Insights** | Statistical Analysis | Optimal posting times |
| **Content Gaps** | Opportunity Scoring | Underserved topics |

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Generate all insights
python src/main.py

# Generate specific insight type
python src/main.py --type thumbnails
python src/main.py --type titles
python src/main.py --type timing
python src/main.py --type gaps
```

## Architecture

```
insights/
├── requirements.txt
│
├── src/
│   ├── __init__.py
│   ├── main.py              # Entry point
│   ├── config.py            # Configuration
│   ├── firebase_client.py   # Firebase operations
│   │
│   ├── correlations.py      # Pearson correlation analysis
│   ├── patterns.py          # Pattern extraction from top videos
│   ├── gaps.py              # Content gap analysis
│   └── reports.py           # Report generation & storage
│
├── outputs/                  # Generated reports (JSON/CSV)
│   ├── thumbnail_insights.json
│   ├── title_insights.json
│   ├── timing_insights.json
│   └── content_gaps.json
│
└── tests/
    └── test_correlations.py
```

## Core Components

### 1. Correlation Analyzer

Finds features that correlate with view counts using Pearson correlation:

```python
# src/correlations.py
from scipy import stats

class CorrelationAnalyzer:
    def __init__(self, videos_with_analysis: List[Dict]):
        self.df = self._build_dataframe(videos_with_analysis)

    def find_top_correlations(self, target: str = 'view_count') -> List[Dict]:
        """Find features with strongest correlation to views."""
        correlations = []

        for column in self.numeric_columns:
            corr, p_value = stats.pearsonr(
                self.df[column].values,
                self.df[target].values
            )

            # Filter by significance and effect size
            if abs(corr) > 0.1 and p_value < 0.05:
                correlations.append({
                    'feature': column,
                    'correlation': corr,
                    'p_value': p_value,
                    'direction': 'positive' if corr > 0 else 'negative'
                })

        return sorted(correlations, key=lambda x: abs(x['correlation']), reverse=True)
```

**Filtering criteria:**
- Correlation coefficient > 0.1 (meaningful effect)
- P-value < 0.05 (statistically significant)

### 2. Pattern Extractor

Identifies elements overrepresented in top-performing videos:

```python
# src/patterns.py
import numpy as np

class PatternExtractor:
    def __init__(self, videos_with_analysis: List[Dict]):
        self.videos = videos_with_analysis
        self._categorize_by_performance()

    def _categorize_by_performance(self):
        """Categorize videos by view count percentile."""
        views = [v['video']['viewCount'] for v in self.videos]

        self.top_10_threshold = np.percentile(views, 90)
        self.top_25_threshold = np.percentile(views, 75)

        for video in self.videos:
            view_count = video['video']['viewCount']
            if view_count >= self.top_10_threshold:
                video['tier'] = 'top_10'
            elif view_count >= self.top_25_threshold:
                video['tier'] = 'top_25'
            else:
                video['tier'] = 'normal'

    def extract_patterns(self, category: str) -> List[Dict]:
        """Find elements common in top videos but rare overall."""
        top_videos = [v for v in self.videos if v['tier'] == 'top_10']
        patterns = []

        for element in self._get_elements(category):
            top_rate = self._count_element(top_videos, element) / len(top_videos)
            all_rate = self._count_element(self.videos, element) / len(self.videos)

            # Pattern found if 20% more common in top videos
            if top_rate > all_rate * 1.2:
                patterns.append({
                    'element': element,
                    'top_rate': top_rate,
                    'all_rate': all_rate,
                    'lift': top_rate / all_rate if all_rate > 0 else float('inf')
                })

        return sorted(patterns, key=lambda x: x['lift'], reverse=True)
```

**Lift calculation:**
```
lift = rate_in_top_videos / rate_in_all_videos
```
A lift of 2.0 means the element is 2x more common in top performers.

### 3. Timing Analyzer

Analyzes posting time performance:

```python
def extract_timing_patterns(self) -> Dict:
    """Analyze posting day and hour performance."""
    day_performance = defaultdict(list)
    hour_performance = defaultdict(list)

    for video in self.videos:
        day = video['video']['calculated']['publishDayOfWeek']
        hour = video['video']['calculated']['publishHourIST']
        views = video['video']['viewCount']

        day_performance[day].append(views)
        hour_performance[hour].append(views)

    total_avg = np.mean([v['video']['viewCount'] for v in self.videos])

    return {
        'byDayOfWeek': [
            {
                'day': day,
                'avgViews': np.mean(views),
                'multiplier': np.mean(views) / total_avg
            }
            for day, views in sorted(day_performance.items(),
                                     key=lambda x: np.mean(x[1]),
                                     reverse=True)
        ],
        'byHourIST': [
            {
                'hour': hour,
                'avgViews': np.mean(views),
                'multiplier': np.mean(views) / total_avg
            }
            for hour, views in sorted(hour_performance.items(),
                                      key=lambda x: np.mean(x[1]),
                                      reverse=True)
        ],
        'optimal': {
            'day': best_day,
            'hourIST': best_hour,
            'multiplier': combined_multiplier
        }
    }
```

### 4. Gap Analyzer

Identifies content opportunities:

```python
# src/gaps.py
class GapAnalyzer:
    def find_content_gaps(self) -> List[Dict]:
        """Find underserved topics with high view potential."""
        topic_performance = defaultdict(list)

        for video in self.videos:
            niche = video['analysis']['keywords']['niche']
            views = video['video']['viewCount']
            topic_performance[niche].append(views)

        opportunities = []
        for topic, views in topic_performance.items():
            avg_views = np.mean(views)
            video_count = len(views)

            # High opportunity = high views + low competition
            opportunity_score = avg_views / (video_count + 1)

            opportunities.append({
                'topic': topic,
                'avgViews': avg_views,
                'videoCount': video_count,
                'opportunityScore': opportunity_score
            })

        return sorted(opportunities,
                      key=lambda x: x['opportunityScore'],
                      reverse=True)
```

**Opportunity Score:**
```
opportunity_score = average_views / (video_count + 1)
```
Higher score = high views with low competition.

## Output Schemas

### Thumbnail Insights (`insights/thumbnails`)

```json
{
  "generatedAt": "2024-01-25T10:30:00Z",
  "basedOnVideos": 50000,
  "basedOnChannels": 100,

  "topPerformingElements": {
    "composition": [
      {"element": "face-right-food-left", "lift": 2.4, "sampleSize": 1250},
      {"element": "high-contrast", "lift": 2.1, "sampleSize": 3400}
    ],
    "humanPresence": [
      {"element": "surprised-expression", "lift": 2.6, "sampleSize": 890},
      {"element": "eye-contact", "lift": 2.2, "sampleSize": 1540}
    ],
    "colors": [
      {"element": "orange-background", "lift": 2.2, "sampleSize": 980},
      {"element": "warm-palette", "lift": 1.7, "sampleSize": 3200}
    ]
  },

  "topCorrelations": [
    {"feature": "psychology_curiosityGap", "correlation": 0.42, "p_value": 0.001},
    {"feature": "scores_clickability", "correlation": 0.38, "p_value": 0.003}
  ],

  "worstPerformingElements": [
    {"element": "cluttered-layout", "lift": 0.4, "avoid": true},
    {"element": "no-face", "lift": 0.6, "avoid": true}
  ]
}
```

### Title Insights (`insights/titles`)

```json
{
  "generatedAt": "2024-01-25T10:30:00Z",
  "basedOnVideos": 50000,

  "winningPatterns": [
    {
      "pattern": "Dish Name + SECRET/రహస్యం + Recipe",
      "avgViews": 4200000,
      "sampleSize": 89,
      "examples": ["Biryani SECRET Recipe | బిర్యానీ రహస్యం"]
    }
  ],

  "powerWords": {
    "highImpact": [
      {"word": "SECRET", "telugu": "రహస్యం", "multiplier": 2.4},
      {"word": "Restaurant Style", "telugu": "హోటల్ స్టైల్", "multiplier": 2.2}
    ],
    "mediumImpact": [
      {"word": "Easy", "telugu": "సులభం", "multiplier": 1.3}
    ]
  },

  "optimalLength": {
    "characters": {"min": 45, "max": 65, "sweetSpot": 55},
    "words": {"min": 6, "max": 12, "sweetSpot": 8}
  },

  "optimalLanguageMix": {
    "teluguRatio": {"min": 0.2, "max": 0.5, "sweetSpot": 0.35}
  }
}
```

### Timing Insights (`insights/timing`)

```json
{
  "generatedAt": "2024-01-25T10:30:00Z",
  "basedOnVideos": 50000,

  "bestTimes": {
    "byDayOfWeek": [
      {"day": "Saturday", "avgViews": 125000, "multiplier": 1.4},
      {"day": "Sunday", "avgViews": 118000, "multiplier": 1.32},
      {"day": "Friday", "avgViews": 105000, "multiplier": 1.18}
    ],
    "byHourIST": [
      {"hour": 18, "avgViews": 130000, "multiplier": 1.46, "label": "6 PM"},
      {"hour": 19, "avgViews": 125000, "multiplier": 1.40, "label": "7 PM"},
      {"hour": 12, "avgViews": 110000, "multiplier": 1.23, "label": "12 PM"}
    ],
    "optimal": {
      "day": "Saturday",
      "hourIST": 18,
      "description": "Saturday 6 PM IST",
      "multiplier": 1.6
    }
  },

  "seasonalTrends": {
    "festivals": [
      {"name": "Sankranti", "month": 1, "boost": 3.2},
      {"name": "Ugadi", "month": 3, "boost": 2.8}
    ]
  }
}
```

### Content Gaps (`insights/contentGaps`)

```json
{
  "generatedAt": "2024-01-25T10:30:00Z",

  "highOpportunity": [
    {
      "topic": "cooking/indo-chinese",
      "avgViews": 85000,
      "videoCount": 45,
      "opportunityScore": 1847
    }
  ],

  "saturatedTopics": [
    {"topic": "cooking/biryani", "competition": "extreme"},
    {"topic": "cooking/dosa", "competition": "very-high"}
  ]
}
```

## Command Line Interface

### Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--type` | Insight type: `all`, `thumbnails`, `titles`, `timing`, `gaps` | `all` |

### Examples

```bash
# Generate all insights
python src/main.py

# Generate thumbnail insights only
python src/main.py --type thumbnails

# Generate timing analysis
python src/main.py --type timing
```

## Configuration

### Environment Variables

```bash
# Firebase (required)
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_CLIENT_EMAIL=firebase-adminsdk@your-project.iam.gserviceaccount.com
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"

# Analysis settings (optional)
MIN_VIDEOS_FOR_CORRELATION=50
TOP_PERCENTILE=10
MID_PERCENTILE=25
```

### Config Class

```python
class Config:
    # Firebase
    FIREBASE_PROJECT_ID: str
    FIREBASE_CLIENT_EMAIL: str
    FIREBASE_PRIVATE_KEY: str

    # Analysis thresholds
    MIN_VIDEOS_FOR_CORRELATION: int = 50
    TOP_PERCENTILE: int = 10
    MID_PERCENTILE: int = 25
    MIN_CORRELATION: float = 0.1
    MAX_P_VALUE: float = 0.05
```

## Data Requirements

The insights module requires:
1. **Scraped video data** (Phase 1 complete)
2. **AI analysis data** (Phase 2 complete)

Minimum data:
- At least 50 videos for meaningful correlations
- Analysis data for each video

## Output Files

Results are saved to both Firestore and local files:

### Firestore
- `insights/thumbnails`
- `insights/titles`
- `insights/timing`
- `insights/contentGaps`

### Local Files
- `outputs/thumbnail_insights.json`
- `outputs/title_insights.json`
- `outputs/timing_insights.json`
- `outputs/content_gaps.json`

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `pandas` | >=2.2.0 | Data manipulation |
| `numpy` | >=1.26.0 | Numerical operations |
| `scipy` | >=1.12.0 | Statistical analysis |
| `firebase-admin` | >=6.4.0 | Firebase SDK |
| `python-dotenv` | >=1.0.1 | Environment config |
| `tqdm` | >=4.66.2 | Progress bars |

## Testing

```bash
# Run tests
pytest tests/

# Run with coverage
pytest tests/ --cov=src
```

## Performance

### Estimated Processing Time

| Videos | Processing Time |
|--------|-----------------|
| 10,000 | ~5 minutes |
| 50,000 | ~20 minutes |
| 100,000 | ~45 minutes |

### Memory Usage

- ~500 MB for 50,000 videos
- Recommend: 8 GB RAM for large datasets

## Statistical Notes

### Correlation Interpretation

| Correlation | Interpretation |
|-------------|----------------|
| 0.7 - 1.0 | Strong positive |
| 0.4 - 0.7 | Moderate positive |
| 0.1 - 0.4 | Weak positive |
| -0.1 - 0.1 | No correlation |
| -0.4 - -0.1 | Weak negative |

### Lift Interpretation

| Lift | Interpretation |
|------|----------------|
| > 2.0 | Strong pattern (2x more common in top videos) |
| 1.5 - 2.0 | Moderate pattern |
| 1.2 - 1.5 | Weak pattern |
| < 1.2 | Not significant |

## Next Steps

After generating insights:
1. Review output files for patterns
2. Proceed to **Phase 4: Recommender** to generate recommendations

---

For detailed documentation, see [Technical Documentation](../docs/TECHNICAL_DOCUMENTATION.md).
