"""Feature profiler for computing content-type performance profiles.

Compares feature distributions between all videos and top 10% performers
within each content type. Output is raw data (counts, percentages, averages)
without interpretation — the recommender's LLM handles interpretation.
"""

import math
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from collections import Counter, defaultdict
import numpy as np


# Metadata fields to skip during profiling
SKIP_FIELDS = {
    "analyzedAt",
    "modelUsed",
    "analysisVersion",
    "rawTitle",
    "hasDescription",
    "inputMetadata",
}

# String fields with too many unique values are not useful as categories
MAX_CATEGORICAL_VALUES = 20

# Minimum videos for a content type to generate a profile
MIN_VIDEOS_PER_TYPE = 30

# Max bytes for a Firestore field name (limit is 1500 for full path)
_MAX_KEY_BYTES = 200


def _safe_key(key: str) -> str:
    """Truncate a string used as a Firestore field key to stay within path limits."""
    if len(key.encode("utf-8")) <= _MAX_KEY_BYTES:
        return key
    # Truncate by chars until under byte limit
    truncated = key
    while len(truncated.encode("utf-8")) > _MAX_KEY_BYTES - 3:
        truncated = truncated[:-1]
    return truncated + "..."


def compute_confidence(sample_size: int) -> str:
    """Classify statistical confidence based on sample size.

    Returns:
        'low' (<10), 'medium' (10-50), 'high' (50+)
    """
    if sample_size < 10:
        return "low"
    if sample_size < 50:
        return "medium"
    return "high"


def is_significant(all_rate: float, top_rate: float, threshold: float = 0.05) -> bool:
    """Check if the difference between all and top10 rates is significant.

    Uses a simple absolute difference threshold — if the top10 rate differs
    from the all rate by more than the threshold, the difference is significant.
    """
    return abs(top_rate - all_rate) > threshold


def compute_recency_weight(published_at: str, half_life_days: float = 365.0) -> float:
    """Compute exponential decay weight based on publish date.

    Args:
        published_at: ISO 8601 date string.
        half_life_days: Days for the weight to halve (default 365).

    Returns:
        Weight between 0 and 1 (1.0 = just published, 0.5 = one half-life ago).
    """
    try:
        if isinstance(published_at, str):
            # Handle both Z and +00:00 suffixes
            dt_str = published_at.replace("Z", "+00:00")
            pub_date = datetime.fromisoformat(dt_str)
        else:
            return 1.0  # Default weight if not a string

        now = datetime.now(timezone.utc)
        days_ago = (now - pub_date).total_seconds() / 86400.0
        if days_ago < 0:
            days_ago = 0

        return math.exp(-math.log(2) * days_ago / half_life_days)
    except (ValueError, TypeError):
        return 1.0


def compute_feature_profile(
    all_analyses: List[Dict],
    top_analyses: List[Dict],
    all_weights: Optional[List[float]] = None,
    top_weights: Optional[List[float]] = None,
) -> Dict[str, Any]:
    """
    Compare feature distributions between all and top performing videos.

    Automatically detects feature types (boolean, categorical, numeric, list)
    and computes appropriate statistics for each.

    Args:
        all_analyses: Analysis dicts from all videos in the group.
        top_analyses: Analysis dicts from top 10% performers.
        all_weights: Optional recency weights for all_analyses (same length).
        top_weights: Optional recency weights for top_analyses (same length).

    Returns:
        Nested dict mirroring the analysis structure with all vs top10 stats.
    """
    all_values = _collect_values(all_analyses)
    top_values = _collect_values(top_analyses)

    # Collect per-index weights aligned to each path
    all_path_weights = None
    top_path_weights = None
    if all_weights is not None:
        all_path_weights = _collect_weights(all_analyses, all_weights)
    if top_weights is not None:
        top_path_weights = _collect_weights(top_analyses, top_weights)

    profile = {}
    for path, values in all_values.items():
        top_vals = top_values.get(path, [])

        if not values:
            continue

        a_weights = all_path_weights.get(path) if all_path_weights else None
        t_weights = top_path_weights.get(path) if top_path_weights else None

        stat = _compute_stats(values, top_vals, a_weights, t_weights)
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
        video = video_data["video"]
        vps = get_vps(video_data)
        calculated = video.get("calculated", {})

        day = calculated.get("publishDayOfWeek")
        hour = calculated.get("publishHourIST")

        if day and vps > 0:
            day_views[day].append(vps)
        if hour is not None and vps > 0:
            hour_views[hour].append(vps)

    # Compute day stats
    best_days = []
    for day, vps_list in day_views.items():
        if len(vps_list) < 5:
            continue
        best_days.append(
            {
                "day": day,
                "avgViewsPerSubscriber": round(float(np.mean(vps_list)), 2),
                "videoCount": len(vps_list),
            }
        )
    best_days.sort(key=lambda x: x["avgViewsPerSubscriber"], reverse=True)

    # Compute hour stats
    best_hours = []
    for hour, vps_list in hour_views.items():
        if len(vps_list) < 5:
            continue
        best_hours.append(
            {
                "hour": hour,
                "avgViewsPerSubscriber": round(float(np.mean(vps_list)), 2),
                "videoCount": len(vps_list),
            }
        )
    best_hours.sort(key=lambda x: x["avgViewsPerSubscriber"], reverse=True)

    return {
        "bestDays": best_days,
        "bestHours": best_hours,
    }


def compute_feature_correlations(
    all_analyses: List[Dict], top_analyses: List[Dict], top_n_features: int = 20, top_n_pairs: int = 10
) -> List[Dict[str, Any]]:
    """Compute pairwise boolean co-occurrence for top-performing features.

    Finds the boolean features with the highest lift (top10_rate / all_rate),
    then computes pairwise co-occurrence rates among them.

    Args:
        all_analyses: Analysis dicts from all videos.
        top_analyses: Analysis dicts from top 10% performers.
        top_n_features: Number of top boolean features to consider.
        top_n_pairs: Number of top co-occurrence pairs to return.

    Returns:
        List of {pair: [feat1, feat2], coOccurrence: {all, top10}, lift}.
    """
    all_values = _collect_values(all_analyses)
    top_values = _collect_values(top_analyses)

    # Find boolean features with highest lift
    bool_lifts = []
    for path, values in all_values.items():
        clean = [v for v in values if isinstance(v, bool)]
        if len(clean) < 10:
            continue

        all_rate = sum(1 for v in clean if v) / len(clean)
        if all_rate < 0.01:
            continue  # Skip near-zero rates

        top_clean = [v for v in top_values.get(path, []) if isinstance(v, bool)]
        if not top_clean:
            continue

        top_rate = sum(1 for v in top_clean if v) / len(top_clean)
        lift = top_rate / all_rate if all_rate > 0 else 0
        bool_lifts.append((path, lift, all_rate, top_rate))

    bool_lifts.sort(key=lambda x: x[1], reverse=True)
    top_features = [item[0] for item in bool_lifts[:top_n_features]]

    if len(top_features) < 2:
        return []

    # Build per-analysis boolean vectors for top features
    def _get_bool_vectors(analyses, features):
        vectors = []
        for analysis in analyses:
            vals = _collect_values([analysis])
            vec = {}
            for feat in features:
                v = vals.get(feat, [None])
                vec[feat] = v[0] if v and isinstance(v[0], bool) else False
            vectors.append(vec)
        return vectors

    all_vectors = _get_bool_vectors(all_analyses, top_features)
    top_vectors = _get_bool_vectors(top_analyses, top_features)

    # Compute pairwise co-occurrence
    pairs = []
    for i in range(len(top_features)):
        for j in range(i + 1, len(top_features)):
            f1, f2 = top_features[i], top_features[j]

            all_co = sum(1 for v in all_vectors if v[f1] and v[f2])
            all_rate = all_co / len(all_vectors) if all_vectors else 0

            top_co = sum(1 for v in top_vectors if v[f1] and v[f2])
            top_rate = top_co / len(top_vectors) if top_vectors else 0

            lift = top_rate / all_rate if all_rate > 0.01 else 0

            pairs.append(
                {
                    "pair": [f1, f2],
                    "coOccurrence": {
                        "all": round(all_rate, 3),
                        "top10": round(top_rate, 3),
                    },
                    "lift": round(lift, 2),
                }
            )

    pairs.sort(key=lambda x: x["lift"], reverse=True)
    return pairs[:top_n_pairs]


def _collect_values(analyses: List[Dict]) -> Dict[str, List]:
    """Collect all values per dot-path key across analyses."""
    collected = defaultdict(list)
    for analysis in analyses:
        _traverse(analysis, "", collected)
    return collected


def _collect_weights(analyses: List[Dict], weights: List[float]) -> Dict[str, List[float]]:
    """Collect weights aligned to each dot-path key.

    For each analysis, we record the corresponding weight for every
    leaf value that analysis contributes.
    """
    path_weights = defaultdict(list)
    for analysis, weight in zip(analyses, weights):
        paths = _collect_values([analysis]).keys()
        for path in paths:
            path_weights[path].append(weight)
    return path_weights


def _traverse(obj: Any, prefix: str, collected: Dict[str, List]):
    """Recursively traverse analysis dict and collect leaf values."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            if not key or key in SKIP_FIELDS:
                continue
            path = f"{prefix}.{key}" if prefix else key
            _traverse(value, path, collected)
    elif isinstance(obj, list):
        # Store entire list as a leaf value for list-level stats
        collected[prefix].append(obj)
    else:
        collected[prefix].append(obj)


def _compute_stats(
    all_values: List,
    top_values: List,
    all_weights: Optional[List[float]] = None,
    top_weights: Optional[List[float]] = None,
) -> Optional[Dict]:
    """Compute appropriate stats based on detected value type."""
    all_clean = [v for v in all_values if v is not None]
    top_clean = [v for v in top_values if v is not None]

    # Also filter weights to match clean values
    if all_weights is not None:
        all_w_clean = [w for v, w in zip(all_values, all_weights) if v is not None]
    else:
        all_w_clean = None
    if top_weights is not None:
        top_w_clean = [w for v, w in zip(top_values, top_weights) if v is not None]
    else:
        top_w_clean = None

    if not all_clean:
        return None

    sample = all_clean[0]

    if isinstance(sample, bool):
        return _bool_stats(all_clean, top_clean)
    if isinstance(sample, (int, float)):
        return _numeric_stats(all_clean, top_clean, all_w_clean, top_w_clean)
    if isinstance(sample, str):
        return _categorical_stats(all_clean, top_clean)
    if isinstance(sample, list):
        return _list_stats(all_clean, top_clean)

    return None


def _bool_stats(all_vals: List[bool], top_vals: List[bool]) -> Dict:
    """Boolean feature: rate of True in all vs top 10%."""
    all_rate = sum(1 for v in all_vals if v) / len(all_vals) if all_vals else 0
    top_rate = sum(1 for v in top_vals if v) / len(top_vals) if top_vals else 0
    return {
        "all": round(all_rate, 3),
        "top10": round(top_rate, 3),
        "confidence": compute_confidence(len(all_vals)),
        "significant": is_significant(all_rate, top_rate),
    }


def _numeric_stats(
    all_vals: List, top_vals: List, all_weights: Optional[List[float]] = None, top_weights: Optional[List[float]] = None
) -> Dict:
    """Numeric feature: average in all vs top 10%."""
    if all_weights and len(all_weights) == len(all_vals):
        all_avg = float(np.average(all_vals, weights=all_weights))
    else:
        all_avg = float(np.mean(all_vals)) if all_vals else 0

    if top_weights and len(top_weights) == len(top_vals) and top_vals:
        top_avg = float(np.average(top_vals, weights=top_weights))
    else:
        top_avg = float(np.mean(top_vals)) if top_vals else 0

    return {
        "all_avg": round(all_avg, 2),
        "top10_avg": round(top_avg, 2),
        "confidence": compute_confidence(len(all_vals)),
    }


def _categorical_stats(all_vals: List[str], top_vals: List[str]) -> Optional[Dict]:
    """Categorical feature: value distribution in all vs top 10%.

    Skips fields with too many unique values (free text).
    """
    unique = set(all_vals)
    if len(unique) > MAX_CATEGORICAL_VALUES:
        return None  # Too many unique values — likely free text

    all_total = len(all_vals)
    top_total = len(top_vals)

    all_dist = {_safe_key(k): round(v / all_total, 3) for k, v in Counter(all_vals).items() if k}
    top_dist = (
        {_safe_key(k): round(v / top_total, 3) for k, v in Counter(top_vals).items() if k} if top_total > 0 else {}
    )

    return {
        "all": all_dist,
        "top10": top_dist,
        "confidence": compute_confidence(all_total),
    }


def _list_stats(all_vals: List[List], top_vals: List[List]) -> Dict:
    """List feature: average length + item frequency for string items."""
    all_avg_len = float(np.mean([len(v) for v in all_vals])) if all_vals else 0
    top_avg_len = float(np.mean([len(v) for v in top_vals])) if top_vals else 0

    result = {
        "all_avg_count": round(all_avg_len, 2),
        "top10_avg_count": round(top_avg_len, 2),
        "confidence": compute_confidence(len(all_vals)),
    }

    # Item frequency for string items
    all_items = [item for sublist in all_vals for item in sublist if isinstance(item, str)]

    if all_items and len(set(all_items)) <= 50:
        top_items = [item for sublist in top_vals for item in sublist if isinstance(item, str)]
        all_total = len(all_vals)  # Number of videos, not items
        top_total = len(top_vals)
        all_counter = Counter(all_items)
        top_counter = Counter(top_items)

        items = {}
        for item, count in all_counter.most_common(15):
            if not item:
                continue  # Skip empty strings — invalid as Firestore keys
            items[_safe_key(item)] = {
                "all": round(count / all_total, 3),
                "top10": round(top_counter.get(item, 0) / top_total, 3) if top_total > 0 else 0,
            }
        result["topItems"] = items

    return result


def _get_nested(d: Dict, path: str) -> Any:
    """Get a value from a nested dict using dot-path notation."""
    keys = path.split(".")
    current = d
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def _set_nested(d: Dict, path: str, value: Any):
    """Set a value in a nested dict using dot-path notation."""
    keys = path.split(".")
    current = d
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        elif not isinstance(current[key], dict):
            return  # Path conflict, skip
        current = current[key]
    current[keys[-1]] = value
