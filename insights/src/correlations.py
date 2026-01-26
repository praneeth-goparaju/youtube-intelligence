"""Statistical correlation analysis between video elements and performance."""

from typing import Dict, Any, List, Tuple, Optional
import pandas as pd
import numpy as np
from scipy import stats


# Configuration constants for correlation analysis
MIN_CORRELATION_STRENGTH = 0.1  # Minimum absolute correlation to consider significant
SIGNIFICANCE_LEVEL = 0.05  # P-value threshold for statistical significance
MIN_SAMPLE_SIZE = 3  # Minimum samples for correlation calculation
MIN_CATEGORY_SAMPLE = 10  # Minimum samples for categorical analysis
DEFAULT_MIN_SAMPLES = 50  # Default minimum samples for analysis


def calculate_correlation(x: List[float], y: List[float]) -> Tuple[float, float]:
    """
    Calculate Pearson correlation coefficient.

    Args:
        x: First variable values
        y: Second variable values

    Returns:
        Tuple of (correlation coefficient, p-value)
    """
    if len(x) < MIN_SAMPLE_SIZE or len(y) < MIN_SAMPLE_SIZE:
        return 0.0, 1.0

    # Remove NaN values
    mask = ~(np.isnan(x) | np.isnan(y))
    x_clean = np.array(x)[mask]
    y_clean = np.array(y)[mask]

    if len(x_clean) < MIN_SAMPLE_SIZE:
        return 0.0, 1.0

    try:
        corr, p_value = stats.pearsonr(x_clean, y_clean)
        return float(corr), float(p_value)
    except (ValueError, RuntimeWarning, FloatingPointError) as e:
        # scipy.stats.pearsonr can raise ValueError for invalid inputs
        # or produce warnings for edge cases
        return 0.0, 1.0
    except Exception as e:
        # Catch any other unexpected errors but log them for debugging
        print(f"Warning: Unexpected error in correlation calculation: {e}")
        return 0.0, 1.0


def calculate_view_multiplier(group_views: List[float], all_views: List[float]) -> float:
    """
    Calculate how much a group's average views differ from overall average.

    Args:
        group_views: Views for videos in the group
        all_views: Views for all videos

    Returns:
        Multiplier (e.g., 2.0 means 2x the average)
    """
    if not group_views or not all_views:
        return 1.0

    group_avg = np.mean(group_views)
    all_avg = np.mean(all_views)

    if all_avg == 0:
        return 1.0

    return float(group_avg / all_avg)


class CorrelationAnalyzer:
    """Analyze correlations between video elements and performance metrics."""

    def __init__(self, videos_with_analysis: List[Dict[str, Any]]):
        """
        Initialize analyzer with video data.

        Args:
            videos_with_analysis: List of videos with their analysis data
        """
        self.videos = videos_with_analysis
        self.df = self._build_dataframe()

    def _build_dataframe(self) -> pd.DataFrame:
        """Build a DataFrame from video data."""
        records = []

        for item in self.videos:
            video = item['video']
            analysis = item.get('analysis', {})
            channel = item.get('channel', {})

            record = {
                'video_id': item['video_id'],
                'channel_id': item['channel_id'],
                'view_count': video.get('viewCount', 0),
                'like_count': video.get('likeCount', 0),
                'comment_count': video.get('commentCount', 0),
                'subscriber_count': channel.get('subscriberCount', 1),
            }

            # Add calculated metrics if available
            calculated = video.get('calculated', {})
            record.update({
                'engagement_rate': calculated.get('engagementRate', 0),
                'views_per_day': calculated.get('viewsPerDay', 0),
                'views_per_subscriber': calculated.get('viewsPerSubscriber', 0),
            })

            # Flatten analysis data
            record = self._flatten_analysis(record, analysis)

            records.append(record)

        return pd.DataFrame(records)

    def _flatten_analysis(self, record: Dict, analysis: Dict, prefix: str = '') -> Dict:
        """Recursively flatten analysis dictionary."""
        for key, value in analysis.items():
            full_key = f"{prefix}_{key}" if prefix else key

            if isinstance(value, dict):
                record = self._flatten_analysis(record, value, full_key)
            elif isinstance(value, list):
                record[f"{full_key}_count"] = len(value)
            elif isinstance(value, (bool, int, float, str)):
                record[full_key] = value

        return record

    def find_top_correlations(self, target: str = 'view_count',
                             min_samples: int = DEFAULT_MIN_SAMPLES) -> List[Dict[str, Any]]:
        """
        Find features with strongest correlation to target metric.

        Args:
            target: Target metric to correlate against
            min_samples: Minimum samples required

        Returns:
            List of correlations sorted by strength
        """
        if len(self.df) < min_samples:
            return []

        correlations = []
        target_values = self.df[target].values

        # Skip non-numeric columns
        for col in self.df.columns:
            if col == target:
                continue

            values = self.df[col]

            # Handle boolean columns
            if values.dtype == bool:
                values = values.astype(int)

            # Skip non-numeric
            if not pd.api.types.is_numeric_dtype(values):
                continue

            corr, p_value = calculate_correlation(
                values.tolist(),
                target_values.tolist()
            )

            # Filter weak or non-significant correlations
            if abs(corr) > MIN_CORRELATION_STRENGTH and p_value < SIGNIFICANCE_LEVEL:
                correlations.append({
                    'feature': col,
                    'correlation': round(corr, 3),
                    'p_value': round(p_value, 4),
                    'sample_size': len(self.df),
                    'direction': 'positive' if corr > 0 else 'negative'
                })

        # Sort by absolute correlation
        correlations.sort(key=lambda x: abs(x['correlation']), reverse=True)

        return correlations[:50]  # Top 50 correlations

    def analyze_categorical_impact(self, category_col: str,
                                  target: str = 'view_count') -> List[Dict[str, Any]]:
        """
        Analyze impact of categorical features on target.

        Args:
            category_col: Column with categorical values
            target: Target metric

        Returns:
            List of category impacts
        """
        if category_col not in self.df.columns or target not in self.df.columns:
            return []

        all_views = self.df[target].tolist()
        results = []

        for value in self.df[category_col].unique():
            if pd.isna(value):
                continue

            mask = self.df[category_col] == value
            group_views = self.df[mask][target].tolist()

            if len(group_views) < MIN_CATEGORY_SAMPLE:
                continue

            multiplier = calculate_view_multiplier(group_views, all_views)

            results.append({
                'value': value,
                'sample_size': len(group_views),
                'avg_views': round(np.mean(group_views)),
                'view_multiplier': round(multiplier, 2),
            })

        # Sort by multiplier
        results.sort(key=lambda x: x['view_multiplier'], reverse=True)

        return results

    def get_percentile_thresholds(self, column: str = 'view_count') -> Dict[str, int]:
        """Get percentile thresholds for a column."""
        if column not in self.df.columns:
            return {}

        values = self.df[column].dropna()

        return {
            f'p{p}': int(np.percentile(values, p))
            for p in [10, 25, 50, 75, 90, 95]
        }

    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics."""
        return {
            'total_videos': len(self.df),
            'total_channels': self.df['channel_id'].nunique(),
            'avg_views': int(self.df['view_count'].mean()),
            'median_views': int(self.df['view_count'].median()),
            'total_views': int(self.df['view_count'].sum()),
            'view_percentiles': self.get_percentile_thresholds('view_count'),
        }
