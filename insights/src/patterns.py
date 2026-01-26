"""Pattern extraction from video analysis data."""

from typing import Dict, Any, List, Optional
from collections import Counter, defaultdict
import numpy as np
from datetime import datetime


class PatternExtractor:
    """Extract winning patterns from analyzed videos."""

    def __init__(self, videos_with_analysis: List[Dict[str, Any]]):
        """
        Initialize extractor.

        Args:
            videos_with_analysis: List of videos with analysis data
        """
        self.videos = videos_with_analysis
        self._categorize_by_performance()

    def _categorize_by_performance(self):
        """Categorize videos by performance percentiles."""
        views = [v['video'].get('viewCount', 0) for v in self.videos]

        if not views:
            self.top_10_threshold = 0
            self.top_25_threshold = 0
            return

        self.top_10_threshold = np.percentile(views, 90)
        self.top_25_threshold = np.percentile(views, 75)

        # Tag videos with performance tier
        for video in self.videos:
            view_count = video['video'].get('viewCount', 0)
            if view_count >= self.top_10_threshold:
                video['performance_tier'] = 'top_10'
            elif view_count >= self.top_25_threshold:
                video['performance_tier'] = 'top_25'
            else:
                video['performance_tier'] = 'normal'

    def _get_tier_videos(self, tier: str) -> List[Dict[str, Any]]:
        """Get videos in a specific tier."""
        return [v for v in self.videos if v.get('performance_tier') == tier]

    def extract_thumbnail_patterns(self) -> Dict[str, Any]:
        """Extract patterns from thumbnail analysis."""
        top_videos = self._get_tier_videos('top_10')
        all_videos = self.videos

        patterns = {
            'composition': self._extract_field_patterns(
                top_videos, all_videos, 'analysis.composition'
            ),
            'humanPresence': self._extract_field_patterns(
                top_videos, all_videos, 'analysis.humanPresence'
            ),
            'colors': self._extract_field_patterns(
                top_videos, all_videos, 'analysis.colors'
            ),
            'food': self._extract_field_patterns(
                top_videos, all_videos, 'analysis.food'
            ),
            'graphics': self._extract_field_patterns(
                top_videos, all_videos, 'analysis.graphics'
            ),
            'psychology': self._extract_field_patterns(
                top_videos, all_videos, 'analysis.psychology'
            ),
        }

        return patterns

    def extract_title_patterns(self) -> Dict[str, Any]:
        """Extract patterns from title analysis."""
        top_videos = self._get_tier_videos('top_10')
        all_videos = self.videos

        patterns = {
            'structure': self._extract_field_patterns(
                top_videos, all_videos, 'analysis.structure'
            ),
            'language': self._extract_field_patterns(
                top_videos, all_videos, 'analysis.language'
            ),
            'hooks': self._extract_field_patterns(
                top_videos, all_videos, 'analysis.hooks'
            ),
            'keywords': self._extract_field_patterns(
                top_videos, all_videos, 'analysis.keywords'
            ),
        }

        # Extract power words
        power_words = Counter()
        for v in top_videos:
            hooks = self._get_nested(v, 'analysis.hooks', {})
            for word in hooks.get('powerWords', []):
                power_words[word] += 1

        patterns['topPowerWords'] = [
            {'word': word, 'count': count}
            for word, count in power_words.most_common(20)
        ]

        return patterns

    def extract_timing_patterns(self) -> Dict[str, Any]:
        """Extract optimal posting time patterns."""
        day_performance = defaultdict(list)
        hour_performance = defaultdict(list)

        for video in self.videos:
            calculated = video['video'].get('calculated', {})
            views = video['video'].get('viewCount', 0)

            day = calculated.get('publishDayOfWeek')
            hour = calculated.get('publishHourIST')

            if day:
                day_performance[day].append(views)
            if hour is not None:
                hour_performance[hour].append(views)

        # Calculate averages
        day_stats = []
        all_views = [v['video'].get('viewCount', 0) for v in self.videos]
        total_avg = np.mean(all_views) if all_views else 0

        for day, views in day_performance.items():
            if not views:  # Skip empty lists
                continue
            avg = np.mean(views)
            day_stats.append({
                'day': day,
                'avgViews': int(avg),
                'multiplier': round(avg / total_avg, 2) if total_avg > 0 else 1.0,
                'sampleSize': len(views),
            })

        hour_stats = []
        for hour, views in hour_performance.items():
            if not views:  # Skip empty lists
                continue
            avg = np.mean(views)
            hour_stats.append({
                'hour': hour,
                'hourLabel': f"{hour}:00",
                'avgViews': int(avg),
                'multiplier': round(avg / total_avg, 2) if total_avg > 0 else 1.0,
                'sampleSize': len(views),
            })

        # Sort
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        day_stats.sort(key=lambda x: day_order.index(x['day']) if x['day'] in day_order else 7)
        hour_stats.sort(key=lambda x: x['hour'])

        # Find optimal
        best_day = max(day_stats, key=lambda x: x['multiplier']) if day_stats else None
        best_hour = max(hour_stats, key=lambda x: x['multiplier']) if hour_stats else None

        return {
            'byDayOfWeek': day_stats,
            'byHourIST': hour_stats,
            'optimal': {
                'day': best_day['day'] if best_day else None,
                'hourIST': best_hour['hour'] if best_hour else None,
                'multiplier': round(
                    (best_day['multiplier'] if best_day else 1.0) *
                    (best_hour['multiplier'] if best_hour else 1.0),
                    2
                ),
            },
        }

    def _extract_field_patterns(self, top_videos: List, all_videos: List,
                               field_path: str) -> Dict[str, Any]:
        """Extract patterns for a specific field."""
        top_values = Counter()
        all_values = Counter()

        for v in top_videos:
            value = self._get_nested(v, field_path)
            if isinstance(value, dict):
                for k, val in value.items():
                    if isinstance(val, (bool, str)):
                        top_values[f"{k}:{val}"] += 1
            elif isinstance(value, (bool, str)):
                top_values[str(value)] += 1

        for v in all_videos:
            value = self._get_nested(v, field_path)
            if isinstance(value, dict):
                for k, val in value.items():
                    if isinstance(val, (bool, str)):
                        all_values[f"{k}:{val}"] += 1
            elif isinstance(value, (bool, str)):
                all_values[str(value)] += 1

        # Find patterns more common in top videos
        overrepresented = []
        for key, count in top_values.items():
            top_rate = count / len(top_videos) if top_videos else 0
            all_rate = all_values.get(key, 0) / len(all_videos) if all_videos else 0

            if top_rate > all_rate * 1.2:  # 20% more common in top videos
                overrepresented.append({
                    'pattern': key,
                    'topRate': round(top_rate, 3),
                    'allRate': round(all_rate, 3),
                    'lift': round(top_rate / all_rate, 2) if all_rate > 0 else 0,
                })

        overrepresented.sort(key=lambda x: x['lift'], reverse=True)

        return {
            'topPatterns': overrepresented[:10],
            'sampleSize': len(top_videos),
        }

    def _get_nested(self, obj: Dict, path: str, default=None):
        """Get nested value from dictionary using dot notation."""
        keys = path.split('.')
        value = obj

        for key in keys:
            if isinstance(value, dict):
                value = value.get(key, default)
            else:
                return default

        return value
