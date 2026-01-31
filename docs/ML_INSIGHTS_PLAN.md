# ML-Enhanced Insights System: Implementation Plan

## Executive Summary

Optimize the YouTube Intelligence System's analyzer for efficiency and enhance the insights
phase with ML-powered, content-type-specific models.

**Current State:** 20,000 analyzed videos, 5 API calls/video (3 unused), global insights only
**Target State:** 2 API calls/video, per-content-type ML models with predictions and feature importance

---

## Phase 2 Changes: Analyzer Optimization

### API Call Reduction: 5 → 2

```
BEFORE (5 calls per video)              AFTER (2 calls per video)
────────────────────────                 ────────────────────────
1. Thumbnail   (vision)     ──────────▶  1. Thumbnail (vision)
2. Title       (text)       ──┐
3. Description (text)       ──┴────────▶  2. Title + Description (combined text)
4. Tags        (text)       ── REMOVE
5. Content Structure (text) ── REMOVE
```

### Combined Title + Description Call

Merging title and description into a single Gemini call because:
- Title and description are contextually related
- Description confirms/enriches niche detection from title
- Ingredient lists prove `isRecipe` (vs guessing from title alone)
- Single call = better context for Gemini, fewer API calls

#### What Gemini Analyzes (Combined Call)

**From Title (~120 fields):**
- structure: pattern, segments, separators, length
- language: Telugu/English mix, script detection, code-switching
- hooks: questions, power words, triggers, hook strength
- keywords: niche, subNiche, primaryKeyword, search intent
- contentSignals: isRecipe, isTutorial, isVlog, etc.
- formatting: caps, emojis, brackets, special chars
- teluguAnalysis: dialect, register, honorifics
- scores: SEO, clickability, emotional impact

**From Description (~20 lean fields):**
- structure: length, lineCount, wellOrganized, firstLineHook
- timestamps: hasTimestamps, timestampCount
- recipeContent: hasIngredients, ingredientCount, hasInstructions, instructionSteps, hasCookingTime
- hashtags: count, position
- ctas: hasSubscribeCTA, hasLikeCTA, hasCommentCTA, commentQuestion
- seo: keywordInFirst100Chars, keywordDensity, internalLinking

**Fields NOT included in description (dropped as noise):**
- Social media URLs (Instagram, Facebook, etc.)
- Affiliate/sponsor/monetization details
- Individual ingredient details
- Individual link URLs
- Business email

#### Additional Python-Parsed Features (Free, No API Call)

```python
def extract_description_features(description: str) -> dict:
    return {
        'desc_length': len(description),
        'desc_line_count': description.count('\n') + 1,
        'desc_has_timestamps': bool(re.search(r'\d{1,2}:\d{2}', description)),
        'desc_timestamp_count': len(re.findall(r'\d{1,2}:\d{2}', description)),
        'desc_link_count': len(re.findall(r'https?://', description)),
        'desc_hashtag_count': len(re.findall(r'#\w+', description)),
        'desc_has_emoji': bool(re.search(r'[\U0001F300-\U0001F9FF]', description)),
    }
```

### Thumbnail Call (Unchanged)

Remains a separate vision API call analyzing the thumbnail image.
~109 fields covering composition, human presence, colors, food, graphics, psychology, scores.

---

## Phase 3 Changes: ML-Enhanced Insights

### Architecture: Start Simple

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   PHASE 1    │     │   PHASE 2    │     │   PHASE 3    │     │   PHASE 4    │
│   Scraper    │────▶│   Analyzer   │────▶│  ML Insights │────▶│  Recommender │
│  (existing)  │     │  (optimized) │     │    (NEW)     │     │  (enhanced)  │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
       │                    │                    │                    │
       ▼                    ▼                    ▼                    ▼
   YouTube API         Firestore            Firestore            Firestore
                     (2 calls/video)     (local Python ML)    (read insights)
```

**Key decisions:**
- Train locally (20K videos fits in memory, trains in minutes)
- Read directly from Firestore (no BigQuery needed yet)
- Store insights in Firestore (no Cloud Storage needed yet)
- Migrate to Vertex AI + BigQuery later when data grows

### ML Models: Per Content Type

Train separate models for each content type:

```
Models:
├── recipe     (~4,000 videos) → XGBoost regressor + classifier
├── vlog       (~6,000 videos) → XGBoost regressor + classifier
├── tutorial   (~2,000 videos) → XGBoost regressor + classifier
├── review     (~1,000 videos) → XGBoost regressor + classifier
└── _default   (all 20,000)    → Fallback model
```

Minimum 500 videos per content type to train a model.

### Feature Store

**Total features per video: ~160 (key features, not all 400+)**

| Category | Count | Source |
|----------|-------|--------|
| Thumbnail | ~50 key features | Gemini vision analysis |
| Title | ~60 key features | Combined Gemini call |
| Description (Gemini) | ~20 features | Combined Gemini call |
| Description (Python) | ~7 features | Regex parsing |
| Video metadata | ~25 features | Phase 1 scraper |
| **Total** | **~160** | |

### ML Pipeline

```python
for content_type in ['recipe', 'vlog', 'tutorial', 'review']:
    # 1. Load from Firestore
    videos = load_videos_with_analysis(content_type)

    # 2. Flatten features
    X = flatten_features(videos)  # ~160 features
    y = videos['view_count']

    # 3. Train XGBoost
    model = XGBRegressor(n_estimators=200, max_depth=8)
    model.fit(X_train, y_train)

    # 4. Get feature importance (built into XGBoost)
    importance = model.feature_importances_

    # 5. Discover archetypes (K-Means clustering)
    archetypes = cluster_videos(X, n_clusters=4)

    # 6. Save insights to Firestore
    save_to_firestore(f'insights/ml/{content_type}', {
        'feature_importance': importance[:20],
        'archetypes': archetypes,
        'model_metrics': {'r2': r2_score, 'mae': mae},
        'sample_size': len(videos)
    })
```

### What Each Model Outputs

| Output | Description | Used By |
|--------|-------------|---------|
| **Feature importance** | Top 20 features ranked by impact | Recommender context |
| **Feature interactions** | Top 10 feature pairs that amplify each other | Recommender context |
| **Archetypes** | 3-5 content clusters with traits | Recommender context |
| **Model metrics** | R², MAE, F1 score | Confidence level |
| **Optimal ranges** | Sweet spots for key features | Recommender guidance |

### Insights Storage (Firestore)

```
insights/
├── thumbnails       (existing, keep as fallback)
├── titles           (existing, keep as fallback)
├── timing           (existing, keep)
├── contentGaps      (existing, keep)
└── ml/              (NEW)
    ├── recipe       → ML insights for recipe videos
    ├── vlog         → ML insights for vlog videos
    ├── tutorial     → ML insights for tutorials
    ├── review       → ML insights for reviews
    └── _default     → Global fallback model
```

Each ML insight document:
```json
{
  "contentType": "recipe",
  "sampleSize": 4000,
  "trainedAt": "2026-01-31T10:00:00Z",
  "modelMetrics": {
    "viewPrediction": { "r2Score": 0.68, "mae": 15000 },
    "top10Classification": { "accuracy": 0.82, "f1Score": 0.65 }
  },
  "featureImportance": {
    "thumbnail": [
      {"feature": "thumb_appetite_appeal", "importance": 0.18},
      {"feature": "thumb_face_present", "importance": 0.12}
    ],
    "title": [
      {"feature": "title_has_power_word", "importance": 0.09},
      {"feature": "title_telugu_ratio", "importance": 0.07}
    ],
    "description": [
      {"feature": "desc_has_timestamps", "importance": 0.05},
      {"feature": "desc_has_ingredients", "importance": 0.04}
    ],
    "combined": [/* top 20 across all categories */]
  },
  "interactions": [
    {"features": ["thumb_face_present", "thumb_food_present"], "effect": 2.3},
    {"features": ["title_is_question", "thumb_curiosity_gap"], "effect": 1.8}
  ],
  "archetypes": [
    {
      "name": "Chef Personality",
      "size": 1200,
      "avgViews": 45000,
      "successRate": 0.34,
      "definingTraits": [
        {"feature": "thumb_face_present", "direction": "high"},
        {"feature": "thumb_food_present", "direction": "high"}
      ]
    }
  ]
}
```

---

## Phase 4 Changes: Enhanced Recommender

### Updated Context Building

The recommender loads content-type-specific ML insights:

```
User: { topic: "Biryani", type: "recipe" }
                    │
                    ▼
         Load insights/ml/recipe  ← Content-type specific model
                    │
                    ▼
         Build Gemini prompt:
         "For RECIPE videos (based on 4,000 analyzed):
          - appetite_appeal is #1 factor (18% importance)
          - face + food combo = 2.3x views
          - 'Chef Personality' archetype: 45K avg, 34% hit rate
          - timestamps in description boost views

          Generate recommendation for: Biryani..."
                    │
                    ▼
         Gemini generates biryani-specific recommendation
         using recipe-specific insights
```

### ML Insights → Gemini Prompt → Specific Advice

The ML tells Gemini WHAT matters. Gemini applies it to the specific topic.

| Content Type | ML Insight (Data-Driven) | Gemini Output (Topic-Specific) |
|-------------|-------------------------|-------------------------------|
| recipe/biryani | "appetite_appeal is #1" | "Show steam, layered rice" |
| recipe/idly | "appetite_appeal is #1" | "Show soft texture, chutneys" |
| vlog/travel | "face_present is #1" | "Show excited face at destination" |

---

## Implementation Roadmap

### Step 1: Analyzer Optimization (Days 1-2)
- [ ] Create combined title+description prompt
- [ ] Update analyzer to make 2 calls (thumbnail + combined)
- [ ] Remove tags and content_structure analyzers
- [ ] Test combined analysis quality

### Step 2: ML Development (Days 3-7)
- [ ] Build feature flattening pipeline (Firestore → pandas DataFrame)
- [ ] Train XGBoost models per content type (locally)
- [ ] Extract feature importance
- [ ] Implement K-Means clustering for archetypes
- [ ] Save ML insights to Firestore

### Step 3: Recommender Enhancement (Days 8-10)
- [ ] Update recommender to load ML insights per content type
- [ ] Enhance Gemini prompt with ML context
- [ ] Test end-to-end: request → ML insights → recommendation
- [ ] Verify different advice for different content types

### Step 4: Future Enhancements (Later)
- [ ] Add SHAP for deeper explainability
- [ ] Add niche-level models (biryani vs breakfast) if data supports it
- [ ] Migrate to BigQuery + Vertex AI when data grows beyond 50K+ videos
- [ ] Scheduled retraining pipeline

---

## Dependencies

### Python (insights/requirements.txt additions)

```
scikit-learn>=1.3.0
xgboost>=2.0.0
pandas>=2.0.0
joblib>=1.3.0
```

Note: SHAP, BigQuery, Vertex AI, and Cloud Storage dependencies are NOT needed initially.
Add them in Step 4 when migrating to cloud infrastructure.

---

## Cost

### Immediate (Steps 1-3)

| Item | Cost |
|------|------|
| Gemini API calls | Reduced 60% (5 → 2 calls/video) |
| Training | $0 (local Python) |
| Storage | $0 (existing Firestore) |
| **Total additional cost** | **$0** |

### Future (Step 4, if needed)

| Service | Cost/Month |
|---------|------------|
| BigQuery | ~$5 |
| Vertex AI Training | ~$15 |
| Cloud Storage | ~$1 |
| **Total** | **~$20/month** |

---

## Success Metrics

| Metric | Current | After Step 1 | After Step 3 |
|--------|---------|-------------|-------------|
| API calls/video | 5 | 2 | 2 |
| Analysis quality | Title/desc separate | Combined (better) | Combined |
| Insight granularity | Global | Global | Per content type |
| Feature coverage | ~50 used | ~160 | ~160 |
| Predictions | None | None | View estimates |
| Archetypes | None | None | 3-5 per type |
| Monthly cost delta | $0 | -60% API | -60% API |
