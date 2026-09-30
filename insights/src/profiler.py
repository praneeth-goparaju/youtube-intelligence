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


# Metadata fields to skip during profiling (written by analyzer/src/analyzers/*.py and
# analyzer/src/batch_api/import_results.py alongside the analysis features)
SKIP_FIELDS = {
    "analyzedAt",
    "modelUsed",
    "analysisVersion",
    "rawTitle",
    "hasDescription",
    "batchMode",
    "inputMetadata",
}

# String fields with too many unique values are not useful as categories
MAX_CATEGORICAL_VALUES = 20

# Minimum videos for a content type to generate a profile
MIN_VIDEOS_PER_TYPE = 30

# Max bytes for a Firestore field name (limit is 1500 for full path)
_MAX_KEY_BYTES = 200

# Minimum top-group size before a boolean difference can be flagged significant
MIN_TOP_FOR_SIGNIFICANCE = 10

# z critical value (two-sided, ~95%) used by is_significant
_Z_CRITICAL = 1.96

# Word-list fields that title_description stores as comma-separated strings but the
# legacy `title` analysis stored as lists. Normalized to lists before profiling so
# mixed legacy/new data profiles consistently (per-item topItems, not per-string).
COMMA_SEPARATED_LIST_FIELDS = (
    "language.transliteratedWords",
    "language.teluguWords",
    "language.englishWords",
    "hooks.powerWords",
    "hooks.powerWordCategories",
    "keywords.secondaryKeywords",
)


def split_list_value(value: Any) -> Optional[List[str]]:
    """Normalize a comma-separated string or list into a list of stripped, non-empty strings.

    Returns None for values that are neither (e.g. None), so they stay missing.
    """
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if isinstance(item, str) and item.strip()]
    return None


def normalize_analysis(analysis: Dict, list_fields=COMMA_SEPARATED_LIST_FIELDS) -> Dict:
    """Return a copy of an analysis with word-list fields normalized to lists.

    Only the dicts along each normalized path are copied; the input is not mutated.
    """
    if not isinstance(analysis, dict):
        return analysis
    result = dict(analysis)
    for path in list_fields:
        keys = path.split(".")
        parent = result
        ok = True
        for key in keys[:-1]:
            child = parent.get(key)
            if not isinstance(child, dict):
                ok = False
                break
            child = dict(child)
            parent[key] = child
            parent = child
        if not ok or keys[-1] not in parent:
            continue
        normalized = split_list_value(parent[keys[-1]])
        if normalized is not None:
            parent[keys[-1]] = normalized
    return result


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

    Callers pass the size of the smaller compared group (usually the top 10%),
    since that is what limits how trustworthy an all-vs-top comparison is.

    Returns:
        'low' (<10), 'medium' (10-50), 'high' (50+)
    """
    if sample_size < 10:
        return "low"
    if sample_size < 50:
        return "medium"
    return "high"


def is_significant(
    all_rate: float,
    top_rate: float,
    threshold: float = 0.05,
    n_top: Optional[int] = None,
    n_all: Optional[int] = None,
) -> bool:
    """Check if the difference between all and top10 rates is significant.

    Always requires an absolute difference greater than ``threshold``.

    When the group sizes are known (``n_top``, ``n_all``) it additionally requires
    ``n_top >= MIN_TOP_FOR_SIGNIFICANCE`` and a z-test: the top group is a subset of
    "all", so under the null hypothesis (top is a random subset) its rate has
    standard error ``sqrt(p(1-p)/n_top * (n_all-n_top)/(n_all-1))`` (finite
    population correction). ``|top - all| / se`` must reach 1.96 (~95%).
    """
    diff = abs(top_rate - all_rate)
    if diff <= threshold:
        return False
    if n_top is None:
        return True
    if n_top < MIN_TOP_FOR_SIGNIFICANCE:
        return False
    if n_all is None or n_all <= n_top or n_all < 2:
        return False
    variance = all_rate * (1 - all_rate) / n_top * (n_all - n_top) / (n_all - 1)
    if variance <= 0:
        return False
    return diff / math.sqrt(variance) >= _Z_CRITICAL


def compute_recency_weight(published_at: Any, half_life_days: float = 365.0) -> float:
    """Compute exponential decay weight based on publish date.

    Args:
        published_at: ISO 8601 date string, or a datetime (Firestore returns
            timestamps as DatetimeWithNanoseconds, a datetime subclass).
            Naive datetimes/strings are treated as UTC.
        half_life_days: Days for the weight to halve (default 365).

    Returns:
        Weight between 0 and 1 (1.0 = just published, 0.5 = one half-life ago).
    """
    try:
        if isinstance(published_at, datetime):
            pub_date = published_at
        elif isinstance(published_at, str):
            # Handle both Z and +00:00 suffixes
            dt_str = published_at.replace("Z", "+00:00")
            pub_date = datetime.fromisoformat(dt_str)
        else:
            return 1.0  # Unknown type: no decay
        if pub_date.tzinfo is None:
            pub_date = pub_date.replace(tzinfo=timezone.utc)

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
    and computes appropriate statistics for each. When weights are given they
    apply to every stat type (rates, distributions, averages); sample sizes and
    confidence always use unweighted counts.

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
        # Lists of objects (e.g. legacy structure.segments) have no useful leaf stats
        if any(isinstance(item, dict) for item in obj):
            return
        # Store entire list as a leaf value for list-level stats
        collected[prefix].append(obj)
    else:
        collected[prefix].append(obj)


def _value_kind(value: Any) -> Optional[str]:
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, (int, float)):
        return "numeric"
    if isinstance(value, str):
        return "str"
    if isinstance(value, (list, tuple)):
        return "list"
    return None


def _compute_stats(
    all_values: List,
    top_values: List,
    all_weights: Optional[List[float]] = None,
    top_weights: Optional[List[float]] = None,
) -> Optional[Dict]:
    """Compute appropriate stats based on detected value type.

    Robust to mixed types across videos (e.g. legacy list vs new comma-separated
    string): if any value is a list, strings are split on commas and treated as
    lists; otherwise the most common kind wins and other kinds are dropped.
    """
    all_pairs = _pair_values(all_values, all_weights)
    top_pairs = _pair_values(top_values, top_weights)
    if not all_pairs:
        return None

    kinds = Counter(_value_kind(v) for v, _ in all_pairs)
    kinds.pop(None, None)
    if not kinds:
        return None
    if "list" in kinds:
        kind = "list"
    elif set(kinds) <= {"bool", "numeric"} and "numeric" in kinds:
        kind = "numeric" if kinds["numeric"] >= kinds["bool"] else "bool"
    else:
        kind = kinds.most_common(1)[0][0]

    all_vals, all_w = _coerce(all_pairs, kind)
    top_vals, top_w = _coerce(top_pairs, kind)
    if not all_vals:
        return None

    if kind == "bool":
        return _bool_stats(all_vals, top_vals, all_w, top_w)
    if kind == "numeric":
        return _numeric_stats(all_vals, top_vals, all_w, top_w)
    if kind == "str":
        return _categorical_stats(all_vals, top_vals, all_w, top_w)
    return _list_stats(all_vals, top_vals, all_w, top_w)


def _pair_values(values: List, weights: Optional[List[float]]) -> List[tuple]:
    """Pair values with weights (default 1.0), dropping None values."""
    if weights is None or len(weights) != len(values):
        weights = [1.0] * len(values)
    return [(v, w) for v, w in zip(values, weights) if v is not None]


def _coerce(pairs: List[tuple], kind: str) -> tuple:
    """Keep values of the chosen kind (converting where sensible) and their weights."""
    vals, weights = [], []
    for v, w in pairs:
        vk = _value_kind(v)
        if kind == "list":
            if vk == "list":
                v = list(v)
            elif vk == "str":
                v = split_list_value(v)
            else:
                continue
        elif kind == "numeric":
            if vk == "bool":
                v = int(v)
            elif vk != "numeric":
                continue
        elif vk != kind:
            continue
        vals.append(v)
        weights.append(w)
    return vals, weights


def _wmean(values: List[float], weights: Optional[List[float]]) -> float:
    """Weighted mean (plain mean when weights are missing or sum to zero)."""
    if not values:
        return 0.0
    if weights and len(weights) == len(values) and sum(weights) > 0:
        return float(np.average(values, weights=weights))
    return float(np.mean(values))


def _bool_stats(
    all_vals: List[bool],
    top_vals: List[bool],
    all_weights: Optional[List[float]] = None,
    top_weights: Optional[List[float]] = None,
) -> Dict:
    """Boolean feature: (weighted) rate of True in all vs top 10%."""
    all_rate = _wmean([1.0 if v else 0.0 for v in all_vals], all_weights)
    top_rate = _wmean([1.0 if v else 0.0 for v in top_vals], top_weights)
    return {
        "all": round(all_rate, 3),
        "top10": round(top_rate, 3),
        "confidence": compute_confidence(min(len(all_vals), len(top_vals))),
        "significant": is_significant(all_rate, top_rate, n_top=len(top_vals), n_all=len(all_vals)),
    }


def _numeric_stats(
    all_vals: List, top_vals: List, all_weights: Optional[List[float]] = None, top_weights: Optional[List[float]] = None
) -> Dict:
    """Numeric feature: (weighted) average in all vs top 10%."""
    return {
        "all_avg": round(_wmean(all_vals, all_weights), 2),
        "top10_avg": round(_wmean(top_vals, top_weights), 2),
        "confidence": compute_confidence(min(len(all_vals), len(top_vals))),
    }


def _weighted_counter(values: List, weights: Optional[List[float]]) -> tuple:
    """Return (Counter of value -> summed weight, total weight)."""
    if not weights or len(weights) != len(values):
        weights = [1.0] * len(values)
    counter = Counter()
    for v, w in zip(values, weights):
        counter[v] += w
    return counter, sum(weights)


def _categorical_stats(
    all_vals: List[str],
    top_vals: List[str],
    all_weights: Optional[List[float]] = None,
    top_weights: Optional[List[float]] = None,
) -> Optional[Dict]:
    """Categorical feature: (weighted) value distribution in all vs top 10%.

    Skips fields with too many unique values (free text).
    """
    unique = set(all_vals)
    if len(unique) > MAX_CATEGORICAL_VALUES:
        return None  # Too many unique values — likely free text

    all_counter, all_total = _weighted_counter(all_vals, all_weights)
    top_counter, top_total = _weighted_counter(top_vals, top_weights)

    all_dist = {_safe_key(k): round(v / all_total, 3) for k, v in all_counter.items() if k} if all_total > 0 else {}
    top_dist = {_safe_key(k): round(v / top_total, 3) for k, v in top_counter.items() if k} if top_total > 0 else {}

    return {
        "all": all_dist,
        "top10": top_dist,
        "confidence": compute_confidence(min(len(all_vals), len(top_vals))),
    }


def _list_stats(
    all_vals: List[List],
    top_vals: List[List],
    all_weights: Optional[List[float]] = None,
    top_weights: Optional[List[float]] = None,
) -> Dict:
    """List feature: (weighted) average length + per-video item frequency for string items.

    topItems lists the 15 most frequent items (by video count) with the (weighted)
    share of videos containing each item, in all vs top 10%.
    """
    result = {
        "all_avg_count": round(_wmean([len(v) for v in all_vals], all_weights), 2),
        "top10_avg_count": round(_wmean([len(v) for v in top_vals], top_weights), 2),
        "confidence": compute_confidence(min(len(all_vals), len(top_vals))),
    }

    # Per-video presence of each string item (a video counts an item once)
    all_sets = [{item for item in sublist if isinstance(item, str) and item} for sublist in all_vals]
    frequency = Counter(item for items in all_sets for item in items)

    if frequency:
        top_sets = [{item for item in sublist if isinstance(item, str) and item} for sublist in top_vals]
        items = {}
        # Deterministic order: frequency desc, then item
        for item, _ in sorted(frequency.items(), key=lambda kv: (-kv[1], kv[0]))[:15]:
            items[_safe_key(item)] = {
                "all": round(_wmean([1.0 if item in s else 0.0 for s in all_sets], all_weights), 3),
                "top10": round(_wmean([1.0 if item in s else 0.0 for s in top_sets], top_weights), 3),
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
