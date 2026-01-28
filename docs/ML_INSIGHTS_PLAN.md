# ML-Enhanced Insights System: Complete Implementation Plan

## Executive Summary

Transform the YouTube Intelligence System's insights phase from simple statistical analysis to a production-grade ML system using Google Cloud services.

**Current State:** 20,000 analyzed videos, simple lift-based patterns, global insights
**Target State:** Per-content-type ML models with predictions, feature importance, interactions, and archetypes

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ML-ENHANCED ARCHITECTURE                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   PHASE 1    │     │   PHASE 2    │     │   PHASE 3    │     │   PHASE 4    │
│   Scraper    │────▶│   Analyzer   │────▶│  ML Insights │────▶│  Recommender │
│  (existing)  │     │  (existing)  │     │    (NEW)     │     │  (enhanced)  │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
       │                    │                    │                    │
       ▼                    ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           GOOGLE CLOUD PLATFORM                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │  Firestore  │───▶│  BigQuery   │───▶│  Vertex AI  │───▶│Cloud Storage│  │
│  │   (data)    │    │ (warehouse) │    │ (training)  │    │  (models)   │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘  │
│        │                  │                   │                   │         │
│        │    Firebase      │   Scheduled       │   Custom          │         │
│        │    Extension     │   Export &        │   Training        │         │
│        │    (real-time)   │   BigQuery ML     │   Jobs            │         │
│        │                  │                   │                   │         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        MODEL SERVING                                 │   │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐             │   │
│  │  │   Option A  │    │   Option B  │    │   Option C  │             │   │
│  │  │  Vertex AI  │    │   Cloud     │    │  Firebase   │             │   │
│  │  │  Endpoints  │    │  Functions  │    │  Functions  │             │   │
│  │  │  (managed)  │    │  (flexible) │    │  (existing) │             │   │
│  │  └─────────────┘    └─────────────┘    └─────────────┘             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Selection

### Data Pipeline: Firestore → BigQuery

**Choice: Firebase Extension + Scheduled Exports**

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| Firebase BigQuery Extension | Real-time sync, managed | Stream only, schema changes tricky | ✅ Use for live data |
| Scheduled Export (gcloud) | Full control, batch | Manual setup | ✅ Use for ML training |
| Direct Firestore reads | Simple | Slow for 20K+ docs, costly | ❌ Don't use |

**Implementation:**
```bash
# Install Firebase Extension for real-time sync
firebase ext:install firebase/firestore-bigquery-export

# Configuration:
# - Collection: channels/{channelId}/videos/{videoId}/analysis/{type}
# - Dataset: youtube_intelligence
# - Table: video_analysis_raw
```

### Training: Vertex AI Custom Training

**Choice: Vertex AI with Pre-built Containers**

| Option | Pros | Cons | Best For |
|--------|------|------|----------|
| BigQuery ML | SQL-based, no data movement | Limited algorithms, less control | Simple models |
| Vertex AI AutoML | Zero code, automatic | Black box, expensive | Quick prototypes |
| Vertex AI Custom | Full control, any framework | More setup | ✅ Our use case |
| Local training | Free, simple | Not scalable, manual | Development only |

**Why Vertex AI Custom:**
- Use scikit-learn and XGBoost (proven for this data)
- Full control over hyperparameters
- SHAP integration for explainability
- Scalable to larger datasets
- Pre-built containers available

### Model Serving: Hybrid Approach

**Choice: Cloud Storage + Firebase Functions**

| Option | Cost | Latency | Complexity | Recommendation |
|--------|------|---------|------------|----------------|
| Vertex AI Endpoints | ~$50-150/month (always on) | Low (10-50ms) | Low | Overkill for our use |
| Cloud Functions + GCS | Pay-per-use (~$5-20/month) | Medium (100-300ms) | Medium | ✅ Best value |
| Firebase Functions (existing) | Same as above | Medium | Low | ✅ Integrate here |

**Rationale:**
- Models are small (<100MB for XGBoost)
- Predictions are infrequent (per recommendation request)
- Already have Firebase Functions infrastructure
- Load model from Cloud Storage on cold start, cache in memory

---

## Data Pipeline Design

### 1. Firestore to BigQuery Schema

```sql
-- BigQuery Table: youtube_intelligence.video_features
CREATE TABLE youtube_intelligence.video_features (
  -- Identifiers
  video_id STRING NOT NULL,
  channel_id STRING NOT NULL,
  analyzed_at TIMESTAMP,

  -- Target Variables
  view_count INT64,
  like_count INT64,
  comment_count INT64,
  engagement_rate FLOAT64,
  views_per_day FLOAT64,
  performance_percentile FLOAT64,
  is_top_10_percent BOOL,

  -- Content Classification
  content_type STRING,  -- recipe, vlog, tutorial, review, challenge
  niche STRING,
  sub_niche STRING,

  -- Thumbnail Features (flattened from JSON)
  thumb_face_present BOOL,
  thumb_face_count INT64,
  thumb_face_expression STRING,
  thumb_face_position STRING,
  thumb_eye_contact BOOL,
  thumb_layout_type STRING,
  thumb_color_palette STRING,
  thumb_color_mood STRING,
  thumb_food_present BOOL,
  thumb_food_category STRING,
  thumb_appetite_appeal INT64,
  thumb_has_text BOOL,
  thumb_text_language STRING,
  thumb_has_arrows BOOL,
  thumb_curiosity_gap BOOL,
  thumb_clickability_score INT64,
  -- ... ~100 more thumbnail features

  -- Title Features (flattened)
  title_word_count INT64,
  title_char_count INT64,
  title_telugu_ratio FLOAT64,
  title_has_power_word BOOL,
  title_power_words ARRAY<STRING>,
  title_is_question BOOL,
  title_has_number BOOL,
  title_hook_strength STRING,
  title_seo_score INT64,
  title_clickability_score INT64,
  -- ... ~120 more title features

  -- Video Metadata
  duration_seconds INT64,
  publish_day_of_week STRING,
  publish_hour_ist INT64,
  tag_count INT64,
  description_length INT64,

  -- Raw JSON for complex nested fields
  thumbnail_analysis_json STRING,
  title_analysis_json STRING
)
PARTITION BY DATE(analyzed_at)
CLUSTER BY content_type, channel_id;
```

### 2. Data Export Pipeline

```python
# insights/src/data_pipeline/bigquery_export.py

from google.cloud import bigquery
from google.cloud import firestore
import pandas as pd

class BigQueryExporter:
    """Export Firestore analysis data to BigQuery for ML training."""

    def __init__(self, project_id: str, dataset_id: str = 'youtube_intelligence'):
        self.bq_client = bigquery.Client(project=project_id)
        self.fs_client = firestore.Client(project=project_id)
        self.dataset_id = dataset_id
        self.table_id = f"{project_id}.{dataset_id}.video_features"

    def export_all_videos(self, batch_size: int = 1000) -> int:
        """Export all analyzed videos to BigQuery."""
        channels_ref = self.fs_client.collection('channels')
        total_exported = 0

        for channel_doc in channels_ref.stream():
            videos_ref = channel_doc.reference.collection('videos')

            batch = []
            for video_doc in videos_ref.stream():
                video_data = video_doc.to_dict()

                # Get all analysis types
                analysis_ref = video_doc.reference.collection('analysis')
                analyses = {doc.id: doc.to_dict() for doc in analysis_ref.stream()}

                if 'thumbnail' in analyses and 'title' in analyses:
                    flattened = self._flatten_video(video_data, analyses)
                    batch.append(flattened)

                if len(batch) >= batch_size:
                    self._write_batch(batch)
                    total_exported += len(batch)
                    batch = []

            if batch:
                self._write_batch(batch)
                total_exported += len(batch)

        return total_exported

    def _flatten_video(self, video: dict, analyses: dict) -> dict:
        """Flatten nested analysis JSON into tabular format."""
        thumb = analyses.get('thumbnail', {})
        title = analyses.get('title', {})

        return {
            # Identifiers
            'video_id': video.get('videoId'),
            'channel_id': video.get('channelId'),
            'analyzed_at': thumb.get('analyzedAt'),

            # Targets
            'view_count': video.get('viewCount', 0),
            'like_count': video.get('likeCount', 0),
            'comment_count': video.get('commentCount', 0),
            'engagement_rate': video.get('calculated', {}).get('engagementRate', 0),
            'views_per_day': video.get('calculated', {}).get('viewsPerDay', 0),
            'performance_percentile': video.get('calculated', {}).get('performancePercentile', 0),
            'is_top_10_percent': video.get('calculated', {}).get('performancePercentile', 0) >= 90,

            # Content type
            'content_type': title.get('contentSignals', {}).get('contentType', 'unknown'),
            'niche': title.get('keywords', {}).get('niche', 'unknown'),
            'sub_niche': title.get('keywords', {}).get('subNiche', ''),

            # Thumbnail features
            'thumb_face_present': thumb.get('humanPresence', {}).get('facePresent', False),
            'thumb_face_count': thumb.get('humanPresence', {}).get('faceCount', 0),
            'thumb_face_expression': thumb.get('humanPresence', {}).get('expression', 'none'),
            'thumb_face_position': thumb.get('humanPresence', {}).get('facePosition', 'none'),
            'thumb_eye_contact': thumb.get('humanPresence', {}).get('eyeContact', False),
            'thumb_layout_type': thumb.get('composition', {}).get('layoutType', 'unknown'),
            'thumb_color_palette': thumb.get('colors', {}).get('palette', 'unknown'),
            'thumb_color_mood': thumb.get('colors', {}).get('mood', 'unknown'),
            'thumb_food_present': thumb.get('food', {}).get('foodPresent', False),
            'thumb_food_category': thumb.get('food', {}).get('dishCategory', 'none'),
            'thumb_appetite_appeal': thumb.get('food', {}).get('appetiteAppeal', 0),
            'thumb_has_text': thumb.get('textElements', {}).get('hasText', False),
            'thumb_text_language': thumb.get('textElements', {}).get('primaryLanguage', 'none'),
            'thumb_has_arrows': thumb.get('graphics', {}).get('hasArrows', False),
            'thumb_curiosity_gap': thumb.get('psychology', {}).get('curiosityGap', False),
            'thumb_clickability_score': thumb.get('scores', {}).get('clickability', 0),

            # Title features
            'title_word_count': title.get('structure', {}).get('wordCount', 0),
            'title_char_count': title.get('structure', {}).get('characterCount', 0),
            'title_telugu_ratio': title.get('language', {}).get('teluguRatio', 0),
            'title_has_power_word': title.get('hooks', {}).get('hasPowerWord', False),
            'title_power_words': title.get('hooks', {}).get('powerWords', []),
            'title_is_question': title.get('hooks', {}).get('isQuestion', False),
            'title_has_number': title.get('hooks', {}).get('hasNumber', False),
            'title_hook_strength': title.get('hooks', {}).get('hookStrength', 'weak'),
            'title_seo_score': title.get('scores', {}).get('seoScore', 0),
            'title_clickability_score': title.get('scores', {}).get('clickabilityScore', 0),

            # Video metadata
            'duration_seconds': video.get('durationSeconds', 0),
            'publish_day_of_week': video.get('calculated', {}).get('publishDayOfWeek', 'unknown'),
            'publish_hour_ist': video.get('calculated', {}).get('publishHourIST', 0),
            'tag_count': video.get('calculated', {}).get('tagCount', 0),
            'description_length': video.get('calculated', {}).get('descriptionLength', 0),

            # Raw JSON for additional features
            'thumbnail_analysis_json': json.dumps(thumb),
            'title_analysis_json': json.dumps(title),
        }

    def _write_batch(self, rows: list):
        """Write batch to BigQuery."""
        errors = self.bq_client.insert_rows_json(self.table_id, rows)
        if errors:
            raise RuntimeError(f"BigQuery insert errors: {errors}")
```

---

## ML Training Pipeline

### 1. Vertex AI Training Job

```python
# insights/src/ml/vertex_training.py

"""
Vertex AI Custom Training Job for YouTube Performance Prediction
"""

from google.cloud import aiplatform
from google.cloud import storage
import pandas as pd
import numpy as np
from xgboost import XGBRegressor, XGBClassifier
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import mean_absolute_error, r2_score, accuracy_score, f1_score
import shap
import joblib
import json
import os

# Constants
CONTENT_TYPES = ['recipe', 'vlog', 'tutorial', 'review', 'challenge']
MODEL_VERSION = '1.0.0'


class YouTubeMLTrainer:
    """Train ML models for YouTube video performance prediction."""

    def __init__(self, project_id: str, region: str = 'us-central1'):
        self.project_id = project_id
        self.region = region
        self.bucket_name = f"{project_id}-ml-models"
        self.storage_client = storage.Client(project=project_id)

        # Ensure bucket exists
        self._ensure_bucket()

    def _ensure_bucket(self):
        """Create Cloud Storage bucket if it doesn't exist."""
        try:
            self.storage_client.get_bucket(self.bucket_name)
        except:
            self.storage_client.create_bucket(self.bucket_name, location=self.region)

    def load_data_from_bigquery(self, content_type: str = None) -> pd.DataFrame:
        """Load training data from BigQuery."""
        from google.cloud import bigquery

        client = bigquery.Client(project=self.project_id)

        where_clause = ""
        if content_type:
            where_clause = f"WHERE content_type = '{content_type}'"

        query = f"""
        SELECT *
        FROM `{self.project_id}.youtube_intelligence.video_features`
        {where_clause}
        """

        return client.query(query).to_dataframe()

    def prepare_features(self, df: pd.DataFrame) -> tuple:
        """Prepare features for training."""

        # Define feature columns (excluding identifiers and targets)
        exclude_cols = [
            'video_id', 'channel_id', 'analyzed_at',
            'view_count', 'like_count', 'comment_count',
            'engagement_rate', 'views_per_day', 'performance_percentile',
            'is_top_10_percent', 'thumbnail_analysis_json', 'title_analysis_json'
        ]

        feature_cols = [c for c in df.columns if c not in exclude_cols]

        X = df[feature_cols].copy()
        y_views = df['view_count']
        y_top10 = df['is_top_10_percent'].astype(int)

        # Encode categorical features
        categorical_cols = X.select_dtypes(include=['object']).columns
        self.label_encoders = {}

        for col in categorical_cols:
            le = LabelEncoder()
            X[col] = le.fit_transform(X[col].fillna('unknown'))
            self.label_encoders[col] = le

        # Handle missing values
        X = X.fillna(0)

        # Store feature names
        self.feature_names = list(X.columns)

        return X, y_views, y_top10

    def train_models(self, X: pd.DataFrame, y_views: pd.Series, y_top10: pd.Series,
                     content_type: str) -> dict:
        """Train XGBoost models for regression and classification."""

        # Split data
        X_train, X_test, y_views_train, y_views_test, y_top10_train, y_top10_test = \
            train_test_split(X, y_views, y_top10, test_size=0.2, random_state=42)

        # Train view count regressor
        regressor = XGBRegressor(
            n_estimators=200,
            max_depth=8,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            n_jobs=-1
        )
        regressor.fit(X_train, y_views_train)

        # Evaluate regressor
        y_pred_views = regressor.predict(X_test)
        reg_metrics = {
            'r2_score': r2_score(y_views_test, y_pred_views),
            'mae': mean_absolute_error(y_views_test, y_pred_views),
            'cv_score': cross_val_score(regressor, X, y_views, cv=5).mean()
        }

        # Train top 10% classifier
        classifier = XGBClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.05,
            scale_pos_weight=9,  # Handle class imbalance (top 10% vs rest)
            random_state=42,
            n_jobs=-1
        )
        classifier.fit(X_train, y_top10_train)

        # Evaluate classifier
        y_pred_top10 = classifier.predict(X_test)
        clf_metrics = {
            'accuracy': accuracy_score(y_top10_test, y_pred_top10),
            'f1_score': f1_score(y_top10_test, y_pred_top10),
            'cv_score': cross_val_score(classifier, X, y_top10, cv=5).mean()
        }

        return {
            'regressor': regressor,
            'classifier': classifier,
            'reg_metrics': reg_metrics,
            'clf_metrics': clf_metrics,
            'X_train': X_train,
            'content_type': content_type
        }

    def compute_shap_analysis(self, model, X: pd.DataFrame, model_type: str) -> dict:
        """Compute SHAP values for feature importance and interactions."""

        # Create SHAP explainer
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X)

        # Global feature importance
        importance = np.abs(shap_values).mean(axis=0)
        importance_df = pd.DataFrame({
            'feature': self.feature_names,
            'importance': importance
        }).sort_values('importance', ascending=False)

        # Top 30 features
        top_features = importance_df.head(30).to_dict('records')

        # Feature interactions (top 10)
        interaction_values = explainer.shap_interaction_values(X.head(500))  # Sample for speed

        interactions = []
        n_features = len(self.feature_names)
        for i in range(n_features):
            for j in range(i+1, n_features):
                effect = np.abs(interaction_values[:, i, j]).mean()
                if effect > 0.01:
                    interactions.append({
                        'feature_1': self.feature_names[i],
                        'feature_2': self.feature_names[j],
                        'interaction_effect': float(effect)
                    })

        interactions = sorted(interactions, key=lambda x: x['interaction_effect'], reverse=True)[:10]

        return {
            'feature_importance': top_features,
            'interactions': interactions,
            'shap_values_sample': shap_values[:100].tolist()  # Sample for storage
        }

    def discover_archetypes(self, X: pd.DataFrame, df: pd.DataFrame,
                           n_clusters: int = 4) -> list:
        """Discover content archetypes using clustering."""
        from sklearn.cluster import KMeans
        from sklearn.preprocessing import StandardScaler

        # Scale features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # Cluster
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(X_scaled)

        # Analyze clusters
        archetypes = []
        for cluster_id in range(n_clusters):
            mask = labels == cluster_id
            cluster_df = df[mask]
            cluster_X = X[mask]

            # Cluster statistics
            avg_views = cluster_df['view_count'].mean()
            success_rate = cluster_df['is_top_10_percent'].mean()

            # Defining traits (features most different from overall)
            cluster_means = cluster_X.mean()
            overall_means = X.mean()
            differences = (cluster_means - overall_means) / (overall_means.replace(0, 1) + 1e-6)

            top_positive = differences.nlargest(3)
            top_negative = differences.nsmallest(3)

            defining_traits = []
            for feat in top_positive.index:
                defining_traits.append({
                    'feature': feat,
                    'direction': 'high',
                    'difference': f"+{differences[feat]*100:.0f}%"
                })
            for feat in top_negative.index:
                defining_traits.append({
                    'feature': feat,
                    'direction': 'low',
                    'difference': f"{differences[feat]*100:.0f}%"
                })

            # Auto-generate name based on traits
            name = self._generate_archetype_name(defining_traits)

            archetypes.append({
                'cluster_id': cluster_id,
                'name': name,
                'size': int(mask.sum()),
                'avg_views': int(avg_views),
                'success_rate': float(success_rate),
                'defining_traits': defining_traits,
                'exemplar_video_ids': cluster_df.nlargest(3, 'view_count')['video_id'].tolist()
            })

        return sorted(archetypes, key=lambda x: x['avg_views'], reverse=True)

    def _generate_archetype_name(self, traits: list) -> str:
        """Generate human-readable archetype name from traits."""
        # Simple heuristic-based naming
        trait_features = [t['feature'] for t in traits if t['direction'] == 'high']

        if 'thumb_face_present' in trait_features or 'thumb_eye_contact' in trait_features:
            if 'thumb_food_present' in trait_features:
                return "Chef Personality"
            return "Face-Forward"
        elif 'thumb_food_present' in trait_features:
            if 'thumb_appetite_appeal' in trait_features:
                return "Food Showcase"
            return "Recipe Focus"
        elif 'thumb_has_text' in trait_features:
            return "Text-Heavy"
        elif 'thumb_has_arrows' in trait_features:
            return "Clickbait Style"
        else:
            return "Minimalist"

    def save_models(self, models: dict, insights: dict, content_type: str):
        """Save models and insights to Cloud Storage."""

        # Save models
        model_path = f"models/{content_type}/v{MODEL_VERSION}"

        # Regressor
        reg_blob = self.storage_client.bucket(self.bucket_name).blob(
            f"{model_path}/regressor.joblib"
        )
        with reg_blob.open('wb') as f:
            joblib.dump(models['regressor'], f)

        # Classifier
        clf_blob = self.storage_client.bucket(self.bucket_name).blob(
            f"{model_path}/classifier.joblib"
        )
        with clf_blob.open('wb') as f:
            joblib.dump(models['classifier'], f)

        # Label encoders
        enc_blob = self.storage_client.bucket(self.bucket_name).blob(
            f"{model_path}/encoders.joblib"
        )
        with enc_blob.open('wb') as f:
            joblib.dump(self.label_encoders, f)

        # Feature names
        feat_blob = self.storage_client.bucket(self.bucket_name).blob(
            f"{model_path}/feature_names.json"
        )
        with feat_blob.open('w') as f:
            json.dump(self.feature_names, f)

        # Insights
        insights_blob = self.storage_client.bucket(self.bucket_name).blob(
            f"{model_path}/insights.json"
        )
        with insights_blob.open('w') as f:
            json.dump(insights, f, default=str)

        print(f"Saved models to gs://{self.bucket_name}/{model_path}/")

    def train_all_content_types(self):
        """Train models for all content types."""

        results = {}

        for content_type in CONTENT_TYPES:
            print(f"\n{'='*60}")
            print(f"Training models for: {content_type}")
            print('='*60)

            # Load data
            df = self.load_data_from_bigquery(content_type)

            if len(df) < 500:
                print(f"Insufficient data for {content_type}: {len(df)} videos (need 500+)")
                continue

            print(f"Loaded {len(df)} videos")

            # Prepare features
            X, y_views, y_top10 = self.prepare_features(df)
            print(f"Prepared {len(X.columns)} features")

            # Train models
            models = self.train_models(X, y_views, y_top10, content_type)
            print(f"Regressor R²: {models['reg_metrics']['r2_score']:.3f}")
            print(f"Classifier F1: {models['clf_metrics']['f1_score']:.3f}")

            # SHAP analysis
            print("Computing SHAP values...")
            shap_analysis = self.compute_shap_analysis(
                models['regressor'],
                models['X_train'].head(1000),  # Sample for speed
                'regressor'
            )

            # Archetypes
            print("Discovering archetypes...")
            archetypes = self.discover_archetypes(X, df)

            # Compile insights
            insights = {
                'content_type': content_type,
                'sample_size': len(df),
                'model_version': MODEL_VERSION,
                'trained_at': pd.Timestamp.now().isoformat(),
                'model_metrics': {
                    'view_prediction': models['reg_metrics'],
                    'top10_classification': models['clf_metrics']
                },
                'feature_importance': {
                    'thumbnail': [f for f in shap_analysis['feature_importance']
                                  if f['feature'].startswith('thumb_')][:15],
                    'title': [f for f in shap_analysis['feature_importance']
                              if f['feature'].startswith('title_')][:15],
                    'combined': shap_analysis['feature_importance'][:20]
                },
                'interactions': shap_analysis['interactions'],
                'archetypes': archetypes
            }

            # Save
            self.save_models(models, insights, content_type)

            results[content_type] = insights

        return results


# Vertex AI Training Entry Point
def train_vertex_ai(args):
    """Entry point for Vertex AI custom training job."""

    trainer = YouTubeMLTrainer(
        project_id=args.project_id,
        region=args.region
    )

    results = trainer.train_all_content_types()

    print("\n" + "="*60)
    print("TRAINING COMPLETE")
    print("="*60)

    for content_type, insights in results.items():
        print(f"\n{content_type}:")
        print(f"  Sample size: {insights['sample_size']}")
        print(f"  R² Score: {insights['model_metrics']['view_prediction']['r2_score']:.3f}")
        print(f"  Top feature: {insights['feature_importance']['combined'][0]['feature']}")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--project-id', required=True)
    parser.add_argument('--region', default='us-central1')

    args = parser.parse_args()
    train_vertex_ai(args)
```

### 2. Vertex AI Job Submission

```python
# insights/src/ml/submit_training.py

from google.cloud import aiplatform

def submit_training_job(project_id: str, region: str = 'us-central1'):
    """Submit custom training job to Vertex AI."""

    aiplatform.init(project=project_id, location=region)

    job = aiplatform.CustomJob.from_local_script(
        display_name="youtube-ml-training",
        script_path="vertex_training.py",
        container_uri="us-docker.pkg.dev/vertex-ai/training/scikit-learn-cpu.1-3:latest",
        requirements=["xgboost>=2.0.0", "shap>=0.43.0", "pandas>=2.0.0"],
        args=[
            f"--project-id={project_id}",
            f"--region={region}"
        ],
        replica_count=1,
        machine_type="n1-standard-8",  # 8 vCPUs, 30GB RAM
    )

    job.run(sync=True)

    return job


if __name__ == '__main__':
    import sys
    project_id = sys.argv[1] if len(sys.argv) > 1 else 'your-project-id'
    submit_training_job(project_id)
```

---

## Model Serving Integration

### Firebase Functions Enhancement

```typescript
// functions/src/ml/predictor.ts

import { Storage } from '@google-cloud/storage';
import * as admin from 'firebase-admin';

interface MLInsights {
  contentType: string;
  sampleSize: number;
  modelMetrics: {
    viewPrediction: { r2Score: number; mae: number };
    top10Classification: { accuracy: number; f1Score: number };
  };
  featureImportance: {
    thumbnail: FeatureImportance[];
    title: FeatureImportance[];
    combined: FeatureImportance[];
  };
  interactions: Interaction[];
  archetypes: Archetype[];
}

interface FeatureImportance {
  feature: string;
  importance: number;
}

interface Interaction {
  feature_1: string;
  feature_2: string;
  interaction_effect: number;
}

interface Archetype {
  name: string;
  avgViews: number;
  successRate: number;
  definingTraits: { feature: string; direction: string; difference: string }[];
}

// Cache for ML insights
const insightsCache: Map<string, MLInsights> = new Map();
const CACHE_TTL = 3600000; // 1 hour

/**
 * Load ML insights from Cloud Storage
 */
export async function getMLInsights(contentType: string): Promise<MLInsights | null> {
  // Check cache
  const cacheKey = `ml_${contentType}`;
  if (insightsCache.has(cacheKey)) {
    return insightsCache.get(cacheKey)!;
  }

  try {
    const storage = new Storage();
    const bucketName = `${process.env.FIREBASE_PROJECT_ID}-ml-models`;
    const filePath = `models/${contentType}/v1.0.0/insights.json`;

    const [content] = await storage
      .bucket(bucketName)
      .file(filePath)
      .download();

    const insights = JSON.parse(content.toString()) as MLInsights;

    // Cache it
    insightsCache.set(cacheKey, insights);
    setTimeout(() => insightsCache.delete(cacheKey), CACHE_TTL);

    return insights;
  } catch (error) {
    console.error(`Failed to load ML insights for ${contentType}:`, error);
    return null;
  }
}

/**
 * Build ML-enhanced context for Gemini prompt
 */
export function buildMLContext(insights: MLInsights): string {
  const parts: string[] = [];

  // Model confidence
  const r2 = insights.modelMetrics.viewPrediction.r2Score;
  const confidence = r2 > 0.7 ? 'HIGH' : r2 > 0.5 ? 'MEDIUM' : 'LOW';
  parts.push(`MODEL CONFIDENCE: ${confidence} (R²=${r2.toFixed(2)})`);
  parts.push(`Based on ${insights.sampleSize.toLocaleString()} ${insights.contentType} videos\n`);

  // Top features
  parts.push('TOP PERFORMANCE FACTORS:');
  for (const feat of insights.featureImportance.combined.slice(0, 10)) {
    const pct = (feat.importance * 100).toFixed(1);
    const readable = featureToReadable(feat.feature);
    parts.push(`  ${pct}% - ${readable}`);
  }

  // Interactions
  if (insights.interactions.length > 0) {
    parts.push('\nPOWERFUL COMBINATIONS:');
    for (const int of insights.interactions.slice(0, 5)) {
      const f1 = featureToReadable(int.feature_1);
      const f2 = featureToReadable(int.feature_2);
      const effect = (int.interaction_effect * 10).toFixed(1);
      parts.push(`  - ${f1} + ${f2} = ${effect}x boost`);
    }
  }

  // Archetypes
  parts.push('\nPROVEN ARCHETYPES:');
  for (const arch of insights.archetypes.slice(0, 3)) {
    const successPct = (arch.successRate * 100).toFixed(0);
    parts.push(`  "${arch.name}":`);
    parts.push(`    - Avg views: ${arch.avgViews.toLocaleString()}`);
    parts.push(`    - Success rate: ${successPct}% hit top 10%`);
    parts.push(`    - Key traits: ${arch.definingTraits.slice(0, 3).map(t =>
      `${featureToReadable(t.feature)} (${t.difference})`
    ).join(', ')}`);
  }

  return parts.join('\n');
}

/**
 * Convert feature name to human-readable form
 */
function featureToReadable(feature: string): string {
  const mappings: Record<string, string> = {
    'thumb_face_present': 'Face in thumbnail',
    'thumb_eye_contact': 'Eye contact with viewer',
    'thumb_appetite_appeal': 'Food appeal score',
    'thumb_food_present': 'Food visible',
    'thumb_curiosity_gap': 'Curiosity trigger',
    'thumb_has_arrows': 'Arrows pointing',
    'thumb_layout_type': 'Thumbnail layout',
    'thumb_color_mood': 'Color mood',
    'title_has_power_word': 'Power words in title',
    'title_telugu_ratio': 'Telugu language ratio',
    'title_is_question': 'Question format',
    'title_hook_strength': 'Hook strength',
    'title_word_count': 'Title word count',
    'title_clickability_score': 'Title clickability',
  };

  return mappings[feature] || feature.replace(/_/g, ' ').replace(/thumb |title /, '');
}
```

### Updated Engine Integration

```typescript
// functions/src/engine.ts - Updated buildContext method

import { getMLInsights, buildMLContext } from './ml/predictor';

private async buildContext(): Promise<string> {
  const parts: string[] = [];
  const contentType = this.request.type;

  // Try to load ML insights first
  const mlInsights = await getMLInsights(contentType);

  if (mlInsights) {
    // Use ML-enhanced context
    parts.push('=== ML-POWERED INSIGHTS ===\n');
    parts.push(buildMLContext(mlInsights));
    parts.push('\n=== ADDITIONAL PATTERNS ===\n');
  }

  // Fallback to existing statistical insights
  if (this.insights.thumbnails?.topPerformingElements) {
    parts.push('THUMBNAIL PATTERNS:');
    // ... existing code
  }

  // ... rest of existing context building

  return parts.join('\n');
}
```

---

## Firestore Insights Storage

```typescript
// Store ML insights in Firestore for fast access

// Collection: insights/ml/{contentType}
interface MLInsightDocument {
  contentType: string;
  generatedAt: Timestamp;
  sampleSize: number;
  modelVersion: string;

  modelMetrics: {
    viewPrediction: {
      r2Score: number;
      mae: number;
      rmse: number;
    };
    top10Classification: {
      accuracy: number;
      precision: number;
      recall: number;
      f1Score: number;
    };
  };

  featureImportance: {
    thumbnail: Array<{
      feature: string;
      importance: number;
      insight: string;  // Human-readable
    }>;
    title: Array<{...}>;
    combined: Array<{...}>;
  };

  interactions: Array<{
    features: [string, string];
    effect: number;
    insight: string;  // "Face + food together = 2.3x views"
  }>;

  archetypes: Array<{
    id: string;
    name: string;
    size: number;
    avgViews: number;
    successRate: number;
    definingTraits: Array<{
      feature: string;
      direction: 'high' | 'low';
      difference: string;
    }>;
    recommendation: string;
    exemplarVideoIds: string[];
  }>;

  optimalRanges: {
    [feature: string]: {
      min: number;
      max: number;
      sweetSpot: number;
      impact: string;
    };
  };
}
```

---

## Cost Estimation

### Monthly Costs (20,000 videos, weekly retraining)

| Service | Usage | Cost/Month |
|---------|-------|------------|
| **BigQuery** | 1GB storage, 10GB queries | ~$5 |
| **Vertex AI Training** | 4 jobs × 1hr × n1-standard-8 | ~$15 |
| **Cloud Storage** | 500MB models | ~$1 |
| **Firebase Functions** | Existing usage | ~$0 (included) |
| **Firestore** | Existing usage | ~$0 (included) |
| **Total** | | **~$20-25/month** |

### Comparison: Always-On Vertex AI Endpoint

| Option | Cost/Month |
|--------|------------|
| Vertex AI Endpoint (n1-standard-2) | ~$110 |
| Cloud Functions + GCS (our approach) | ~$20 |
| **Savings** | **~$90/month** |

---

## Implementation Roadmap

### Phase 1: Data Pipeline (Week 1)
- [ ] Install Firebase BigQuery Export extension
- [ ] Create BigQuery dataset and schema
- [ ] Build data flattening pipeline
- [ ] Initial export of 20,000 videos
- [ ] Validate data quality

### Phase 2: Local Development (Week 2)
- [ ] Set up ML development environment
- [ ] Train initial XGBoost models locally
- [ ] Implement SHAP analysis
- [ ] Implement clustering/archetypes
- [ ] Validate model performance

### Phase 3: Vertex AI Integration (Week 3)
- [ ] Create training container/script
- [ ] Submit first Vertex AI training job
- [ ] Set up Cloud Storage for models
- [ ] Implement model versioning
- [ ] Create scheduled retraining

### Phase 4: Serving Integration (Week 4)
- [ ] Update Firebase Functions to load ML insights
- [ ] Enhance recommender with ML context
- [ ] Add prediction endpoint
- [ ] Test end-to-end flow
- [ ] Deploy to production

### Phase 5: Monitoring & Iteration (Ongoing)
- [ ] Set up model performance monitoring
- [ ] Create retraining triggers
- [ ] A/B test ML vs non-ML recommendations
- [ ] Iterate on features and models

---

## File Structure

```
youtube_channel_analysis/
├── insights/
│   ├── src/
│   │   ├── ml/                          # NEW: ML module
│   │   │   ├── __init__.py
│   │   │   ├── data_pipeline/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── bigquery_export.py   # Firestore → BigQuery
│   │   │   │   ├── feature_engineering.py
│   │   │   │   └── schema.py
│   │   │   ├── training/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── trainer.py           # XGBoost training
│   │   │   │   ├── shap_analysis.py     # Feature importance
│   │   │   │   └── clustering.py        # Archetype discovery
│   │   │   ├── vertex_training.py       # Vertex AI entry point
│   │   │   └── submit_training.py       # Job submission
│   │   ├── main.py                      # Updated to include ML
│   │   └── ...existing files...
│   └── requirements.txt                 # Updated with ML deps
├── functions/
│   └── src/
│       ├── ml/                          # NEW: ML serving
│       │   ├── predictor.ts             # Load & serve insights
│       │   └── types.ts                 # ML type definitions
│       ├── engine.ts                    # Updated with ML context
│       └── ...existing files...
└── docs/
    └── ML_INSIGHTS_PLAN.md              # This document
```

---

## Dependencies

### Python (insights/requirements.txt)

```
# Existing
google-cloud-firestore>=2.11.0
numpy>=1.24.0
tqdm>=4.65.0

# NEW: ML dependencies
scikit-learn>=1.3.0
xgboost>=2.0.0
shap>=0.43.0
pandas>=2.0.0
google-cloud-bigquery>=3.11.0
google-cloud-storage>=2.10.0
google-cloud-aiplatform>=1.28.0
joblib>=1.3.0
```

### TypeScript (functions/package.json)

```json
{
  "dependencies": {
    "@google-cloud/storage": "^7.0.0"
  }
}
```

---

## Success Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Insight granularity | 1 (global) | 5 (per content type) | Count of insight documents |
| Feature coverage | ~50 | 200+ | Features in model |
| Prediction accuracy | N/A | R² > 0.6 | Cross-validation |
| Recommendations quality | Generic | Content-specific | User feedback |
| API calls (analyzer) | 5/video | 2/video | 60% reduction |

---

## Next Steps

1. **Approve this plan** - Review and confirm approach
2. **Set up GCP project** - Enable required APIs
3. **Start Phase 1** - Data pipeline implementation

Ready to proceed?
