"""Feature profiler for computing content-type performance profiles.

Compares feature distributions between all videos and top 10% performers
within each content type. Output is raw data (counts, percentages, averages)
without interpretation — the recommender's LLM handles interpretation.
"""

from typing import Dict, Any, List, Optional
from collections import Counter, defaultdict
import numpy as np


# Metadata fields to skip during profiling
SKIP_FIELDS = {
    'analyzedAt', 'modelUsed', 'analysisVersion', 'rawTitle',
    'hasDescription', 'inputMetadata',
}

# String fields with too many unique values are not useful as categories
MAX_CATEGORICAL_VALUES = 20

# Minimum videos for a content type to generate a profile
MIN_VIDEOS_PER_TYPE = 30


def compute_feature_profile(all_analyses: List[Dict],
                            top_analyses: List[Dict]) -> Dict[str, Any]:
    """
    Compare feature distributions between all and top performing videos.

    Automatically detects feature types (boolean, categorical, numeric, list)
    and computes appropriate statistics for each.

    Args:
        all_analyses: Analysis dicts from all videos in the group.
        top_analyses: Analysis dicts from top 10% performers.

    Returns:
        Nested dict mirroring the analysis structure with all vs top10 stats.
    """
    all_values = _collect_values(all_analyses)
    top_values = _collect_values(top_analyses)

    profile = {}
    for path, values in all_values.items():
        top_vals = top_values.get(path, [])

        if not values:
            continue

        stat = _compute_stats(values, top_vals)
        if stat is not None:
            _set_nested(profile, path, stat)

    return profile


def compute_timing_profile(videos: List[Dict], get_vps) -> Dict[str, Any]:
    """
    Compute posting time patterns for a group of videos.

    Args:
        videos: List of video data dicts.
        get_vps: Function to extract viewsPerSubscriber from a video dict.

    Returns:
        Dict with bestDays and bestHours sorted by performance.
    """
    day_views = defaultdict(list)
    hour_views = defaultdict(list)

    for video_data in videos:
        video = video_data['video']
        vps = get_vps(video_data)
        calculated = video.get('calculated', {})

        day = calculated.get('publishDayOfWeek')
        hour = calculated.get('publishHourIST')

        if day and vps > 0:
            day_views[day].append(vps)
        if hour is not None and vps > 0:
            hour_views[hour].append(vps)

    # Compute day stats
    best_days = []
    for day, vps_list in day_views.items():
        if len(vps_list) < 5:
            continue
        best_days.append({
            'day': day,
            'avgViewsPerSubscriber': round(float(np.mean(vps_list)), 2),
            'videoCount': len(vps_list),
        })
    best_days.sort(key=lambda x: x['avgViewsPerSubscriber'], reverse=True)

    # Compute hour stats
    best_hours = []
    for hour, vps_list in hour_views.items():
        if len(vps_list) < 5:
            continue
        best_hours.append({
            'hour': hour,
            'avgViewsPerSubscriber': round(float(np.mean(vps_list)), 2),
            'videoCount': len(vps_list),
        })
    best_hours.sort(key=lambda x: x['avgViewsPerSubscriber'], reverse=True)

    return {
        'bestDays': best_days,
        'bestHours': best_hours,
    }


def _collect_values(analyses: List[Dict]) -> Dict[str, List]:
    """Collect all values per dot-path key across analyses."""
    collected = defaultdict(list)
    for analysis in analyses:
        _traverse(analysis, '', collected)
    return collected


def _traverse(obj: Any, prefix: str, collected: Dict[str, List]):
    """Recursively traverse analysis dict and collect leaf values."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in SKIP_FIELDS:
                continue
            path = f"{prefix}.{key}" if prefix else key
            _traverse(value, path, collected)
    elif isinstance(obj, list):
        # Store entire list as a leaf value for list-level stats
        collected[prefix].append(obj)
    else:
        collected[prefix].append(obj)


def _compute_stats(all_values: List, top_values: List) -> Optional[Dict]:
    """Compute appropriate stats based on detected value type."""
    all_clean = [v for v in all_values if v is not None]
    top_clean = [v for v in top_values if v is not None]

    if not all_clean:
        return None

    sample = all_clean[0]

    if isinstance(sample, bool):
        return _bool_stats(all_clean, top_clean)
    if isinstance(sample, (int, float)):
        return _numeric_stats(all_clean, top_clean)
    if isinstance(sample, str):
        return _categorical_stats(all_clean, top_clean)
    if isinstance(sample, list):
        return _list_stats(all_clean, top_clean)

    return None


def _bool_stats(all_vals: List[bool], top_vals: List[bool]) -> Dict:
    """Boolean feature: rate of True in all vs top 10%."""
    all_rate = sum(1 for v in all_vals if v) / len(all_vals) if all_vals else 0
    top_rate = sum(1 for v in top_vals if v) / len(top_vals) if top_vals else 0
    return {'all': round(all_rate, 3), 'top10': round(top_rate, 3)}


def _numeric_stats(all_vals: List, top_vals: List) -> Dict:
    """Numeric feature: average in all vs top 10%."""
    all_avg = float(np.mean(all_vals)) if all_vals else 0
    top_avg = float(np.mean(top_vals)) if top_vals else 0
    return {'all_avg': round(all_avg, 2), 'top10_avg': round(top_avg, 2)}


def _categorical_stats(all_vals: List[str], top_vals: List[str]) -> Optional[Dict]:
    """Categorical feature: value distribution in all vs top 10%.

    Skips fields with too many unique values (free text).
    """
    unique = set(all_vals)
    if len(unique) > MAX_CATEGORICAL_VALUES:
        return None  # Too many unique values — likely free text

    all_total = len(all_vals)
    top_total = len(top_vals)

    all_dist = {k: round(v / all_total, 3) for k, v in Counter(all_vals).items()}
    top_dist = (
        {k: round(v / top_total, 3) for k, v in Counter(top_vals).items()}
        if top_total > 0 else {}
    )

    return {'all': all_dist, 'top10': top_dist}


def _list_stats(all_vals: List[List], top_vals: List[List]) -> Dict:
    """List feature: average length + item frequency for string items."""
    all_avg_len = float(np.mean([len(v) for v in all_vals])) if all_vals else 0
    top_avg_len = float(np.mean([len(v) for v in top_vals])) if top_vals else 0

    result = {
        'all_avg_count': round(all_avg_len, 2),
        'top10_avg_count': round(top_avg_len, 2),
    }

    # Item frequency for string items
    all_items = [item for sublist in all_vals for item in sublist
                 if isinstance(item, str)]

    if all_items and len(set(all_items)) <= 50:
        top_items = [item for sublist in top_vals for item in sublist
                     if isinstance(item, str)]
        all_total = len(all_vals)  # Number of videos, not items
        top_total = len(top_vals)
        all_counter = Counter(all_items)
        top_counter = Counter(top_items)

        items = {}
        for item, count in all_counter.most_common(15):
            items[item] = {
                'all': round(count / all_total, 3),
                'top10': round(top_counter.get(item, 0) / top_total, 3)
                         if top_total > 0 else 0,
            }
        result['topItems'] = items

    return result


def _set_nested(d: Dict, path: str, value: Any):
    """Set a value in a nested dict using dot-path notation."""
    keys = path.split('.')
    current = d
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        elif not isinstance(current[key], dict):
            return  # Path conflict, skip
        current = current[key]
    current[keys[-1]] = value
