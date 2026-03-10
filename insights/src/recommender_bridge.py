"""Recommender bridge — transforms profiled insights into the format Phase 4 expects.

The recommender (functions/) reads from:
  - insights/thumbnails  → ThumbnailInsights
  - insights/titles      → TitleInsights
  - insights/timing      → TimingInsights
  - insights/contentGaps → ContentGapInsights (flat format)

This module converts per-content-type profiles into those 4 documents.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from collections import defaultdict

from .profiler import _get_nested, is_significant


# Maps thumbnail analysis section prefixes to recommender categories
THUMBNAIL_SECTION_MAP = {
    'humanPresence': 'humanPresence',
    'food': 'food',
    'colors': 'colors',
    'textElements': 'text',
    'composition': 'composition',
    'scene': 'composition',
    'graphics': 'composition',
    'branding': 'composition',
    'psychology': 'composition',
    'technicalQuality': 'composition',
}


def generate_recommender_documents(
    profiles: Dict[str, dict],
    content_gaps: Optional[dict],
) -> Dict[str, dict]:
    """Generate the 4 documents the recommender expects.

    Args:
        profiles: Dict of content_type -> profile data from generate_content_type_profile().
        content_gaps: The gap_report from GapAnalyzer, or None.

    Returns:
        Dict with keys 'thumbnails', 'titles', 'timing', and optionally 'contentGaps'.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    total_videos = sum(
        p.get('summary', {}).get('totalVideos', 0)
        for p in profiles.values()
    )

    docs = {}

    docs['thumbnails'] = _build_thumbnail_insights(profiles, timestamp, total_videos)
    docs['titles'] = _build_title_insights(profiles, timestamp, total_videos)
    docs['timing'] = _build_timing_insights(profiles, timestamp, total_videos)

    if content_gaps:
        docs['contentGaps'] = _build_content_gap_insights(content_gaps, timestamp)

    return docs


def _build_thumbnail_insights(
    profiles: Dict[str, dict],
    timestamp: str,
    total_videos: int,
) -> dict:
    """Build ThumbnailInsights document.

    Aggregates boolean thumbnail features across all content types,
    computes lift (top10_rate / all_rate), and groups into categories.

    Returns:
        {generatedAt, basedOnVideos, topPerformingElements: {category: [{element, lift}]},
         worstPerformingElements: [{element, lift}]}
    """
    # Collect all boolean thumbnail features across profiles
    feature_lifts = defaultdict(list)  # feature_path -> [(lift, sample_size, all_rate, top_rate)]

    for profile in profiles.values():
        thumb = profile.get('thumbnail', {})
        features = thumb.get('features', {})
        sample = thumb.get('sampleSize', {})
        all_count = sample.get('all', 0)

        _collect_bool_lifts(features, '', feature_lifts, all_count)

    # Aggregate across content types (weighted average by sample size)
    aggregated = {}
    for path, entries in feature_lifts.items():
        total_sample = sum(e[1] for e in entries)
        if total_sample == 0:
            continue
        # Filter low confidence
        if any(e[1] < 10 for e in entries):
            # Only include if at least one content type has enough data
            valid = [e for e in entries if e[1] >= 10]
            if not valid:
                continue
            entries = valid
            total_sample = sum(e[1] for e in entries)

        # Check significance
        significant_entries = [e for e in entries if is_significant(e[2], e[3])]
        if not significant_entries:
            continue

        weighted_lift = sum(e[0] * e[1] for e in entries) / total_sample
        aggregated[path] = {
            'lift': round(weighted_lift, 2),
            'sampleSize': total_sample,
        }

    # Group into categories
    categories = defaultdict(list)
    worst = []

    for path, info in aggregated.items():
        category = _get_thumbnail_category(path)
        element = {
            'element': path,
            'lift': info['lift'],
            'sampleSize': info['sampleSize'],
        }

        if info['lift'] >= 1.0:
            categories[category].append(element)
        elif info['lift'] < 0.7:
            worst.append({**element, 'avoid': True})

    # Sort each category by lift, take top 10
    top_performing = {}
    for category, elements in categories.items():
        elements.sort(key=lambda x: x['lift'], reverse=True)
        top_performing[category] = elements[:10]

    worst.sort(key=lambda x: x['lift'])

    return {
        'generatedAt': timestamp,
        'basedOnVideos': total_videos,
        'topPerformingElements': top_performing,
        'worstPerformingElements': worst[:10],
    }


def _collect_bool_lifts(
    features: dict,
    prefix: str,
    result: dict,
    sample_size: int,
):
    """Recursively collect boolean feature lifts from a features dict."""
    for key, value in features.items():
        path = f"{prefix}.{key}" if prefix else key

        if isinstance(value, dict):
            # Check if this is a bool stat dict (has 'all' and 'top10' as floats)
            if 'all' in value and 'top10' in value and isinstance(value.get('all'), (int, float)) and isinstance(value.get('top10'), (int, float)):
                # Check confidence
                confidence = value.get('confidence', 'medium')
                if confidence == 'low':
                    continue

                all_rate = value['all']
                top_rate = value['top10']

                if all_rate > 0.01:  # Avoid division by near-zero
                    lift = top_rate / all_rate
                elif top_rate > 0:
                    lift = 2.0  # Cap lift when all_rate is near zero
                else:
                    continue

                result[path].append((lift, sample_size, all_rate, top_rate))
            else:
                # Nested dict — recurse
                _collect_bool_lifts(value, path, result, sample_size)


def _get_thumbnail_category(feature_path: str) -> str:
    """Map a dot-path feature to a recommender thumbnail category."""
    top_section = feature_path.split('.')[0]
    return THUMBNAIL_SECTION_MAP.get(top_section, 'composition')


def _build_title_insights(
    profiles: Dict[str, dict],
    timestamp: str,
    total_videos: int,
) -> dict:
    """Build TitleInsights document.

    Extracts winning patterns, power words, optimal length, and language mix
    from profiled title features across all content types.

    Returns:
        {generatedAt, basedOnVideos, winningPatterns, powerWords,
         optimalLength, optimalLanguageMix}
    """
    all_patterns = defaultdict(lambda: {'all': 0, 'top10': 0, 'count': 0})
    all_char_counts = {'all': [], 'top10': []}
    all_word_counts = {'all': [], 'top10': []}
    all_telugu_ratios = {'all': [], 'top10': []}
    all_power_words = defaultdict(lambda: {'all': 0, 'top10': 0, 'all_total': 0, 'top10_total': 0})

    for profile in profiles.values():
        title = profile.get('title', {})
        features = title.get('features', {})
        sample = title.get('sampleSize', {})
        all_count = sample.get('all', 0)
        top_count = sample.get('top10', 0)

        # Winning patterns from structure.pattern categorical stats
        pattern_stats = _get_nested(features, 'structure.pattern')
        if pattern_stats and isinstance(pattern_stats.get('all'), dict):
            for pattern, rate in pattern_stats['all'].items():
                top_rate = pattern_stats.get('top10', {}).get(pattern, 0)
                all_patterns[pattern]['all'] += rate * all_count
                all_patterns[pattern]['top10'] += top_rate * top_count
                all_patterns[pattern]['count'] += all_count

        # Character count
        char_stats = _get_nested(features, 'structure.characterCount')
        if char_stats:
            if 'all_avg' in char_stats:
                all_char_counts['all'].append((char_stats['all_avg'], all_count))
            if 'top10_avg' in char_stats:
                all_char_counts['top10'].append((char_stats['top10_avg'], top_count))

        # Word count
        word_stats = _get_nested(features, 'structure.wordCount')
        if word_stats:
            if 'all_avg' in word_stats:
                all_word_counts['all'].append((word_stats['all_avg'], all_count))
            if 'top10_avg' in word_stats:
                all_word_counts['top10'].append((word_stats['top10_avg'], top_count))

        # Telugu ratio
        telugu_stats = _get_nested(features, 'language.teluguRatio')
        if telugu_stats:
            if 'all_avg' in telugu_stats:
                all_telugu_ratios['all'].append((telugu_stats['all_avg'], all_count))
            if 'top10_avg' in telugu_stats:
                all_telugu_ratios['top10'].append((telugu_stats['top10_avg'], top_count))

        # Power words from hooks.powerWords list stats
        pw_stats = _get_nested(features, 'hooks.powerWords')
        if pw_stats and 'topItems' in pw_stats:
            for word, rates in pw_stats['topItems'].items():
                all_power_words[word]['all'] += rates.get('all', 0) * all_count
                all_power_words[word]['top10'] += rates.get('top10', 0) * top_count
                all_power_words[word]['all_total'] += all_count
                all_power_words[word]['top10_total'] += top_count

    # Build winning patterns
    winning_patterns = []
    top_total = sum(p.get('title', {}).get('sampleSize', {}).get('top10', 0)
                    for p in profiles.values())
    for pattern, data in all_patterns.items():
        if data['count'] == 0:
            continue
        all_rate = data['all'] / data['count']
        top_rate = data['top10'] / top_total if top_total > 0 else 0
        lift = top_rate / all_rate if all_rate > 0.01 else 0

        if lift > 0:
            winning_patterns.append({
                'pattern': pattern,
                'avgViews': round(lift, 2),  # lift as avgViews (recommender field)
                'sampleSize': int(data['all']),
                'examples': [],
            })

    winning_patterns.sort(key=lambda x: x['avgViews'], reverse=True)

    # Build power words
    power_words_list = []
    for word, data in all_power_words.items():
        all_rate = data['all'] / data['all_total'] if data['all_total'] > 0 else 0
        top_rate = data['top10'] / data['top10_total'] if data['top10_total'] > 0 else 0
        multiplier = top_rate / all_rate if all_rate > 0.01 else 0

        if multiplier > 1.0:
            power_words_list.append({
                'word': word,
                'multiplier': round(multiplier, 2),
            })

    power_words_list.sort(key=lambda x: x['multiplier'], reverse=True)

    # Build optimal length
    optimal_length = None
    char_all = _weighted_avg(all_char_counts['all'])
    char_top = _weighted_avg(all_char_counts['top10'])
    word_all = _weighted_avg(all_word_counts['all'])
    word_top = _weighted_avg(all_word_counts['top10'])

    if char_all > 0 or char_top > 0:
        optimal_length = {
            'characters': {
                'min': round(char_top * 0.7, 0),
                'max': round(char_top * 1.3, 0),
                'sweetSpot': round(char_top, 0),
            },
            'words': {
                'min': round(word_top * 0.7, 0),
                'max': round(word_top * 1.3, 0),
                'sweetSpot': round(word_top, 0),
            },
        }

    # Build optimal language mix
    optimal_language_mix = None
    telugu_all = _weighted_avg(all_telugu_ratios['all'])
    telugu_top = _weighted_avg(all_telugu_ratios['top10'])

    if telugu_top > 0 or telugu_all > 0:
        optimal_language_mix = {
            'teluguRatio': {
                'min': round(max(0, telugu_top - 0.15), 2),
                'max': round(min(1, telugu_top + 0.15), 2),
                'sweetSpot': round(telugu_top, 2),
            },
        }

    result = {
        'generatedAt': timestamp,
        'basedOnVideos': total_videos,
    }

    if winning_patterns:
        result['winningPatterns'] = winning_patterns[:15]

    if power_words_list:
        # Split into high and medium impact
        high_impact = [pw for pw in power_words_list if pw['multiplier'] >= 1.5]
        medium_impact = [pw for pw in power_words_list if 1.0 < pw['multiplier'] < 1.5]
        result['powerWords'] = {}
        if high_impact:
            result['powerWords']['highImpact'] = high_impact[:10]
        if medium_impact:
            result['powerWords']['mediumImpact'] = medium_impact[:10]

    if optimal_length:
        result['optimalLength'] = optimal_length

    if optimal_language_mix:
        result['optimalLanguageMix'] = optimal_language_mix

    return result


def _build_timing_insights(
    profiles: Dict[str, dict],
    timestamp: str,
    total_videos: int,
) -> dict:
    """Build TimingInsights document.

    Aggregates timing data across content types (weighted by video count)
    and computes multipliers relative to overall average.

    Returns:
        {generatedAt, basedOnVideos, bestTimes: {byDayOfWeek, byHourIST, optimal}}
    """
    # Aggregate day and hour stats across content types
    day_agg = defaultdict(lambda: {'total_vps': 0, 'total_count': 0})
    hour_agg = defaultdict(lambda: {'total_vps': 0, 'total_count': 0})

    for profile in profiles.values():
        timing = profile.get('timing', {})

        for day_entry in timing.get('bestDays', []):
            day = day_entry['day']
            avg = day_entry['avgViewsPerSubscriber']
            count = day_entry['videoCount']
            day_agg[day]['total_vps'] += avg * count
            day_agg[day]['total_count'] += count

        for hour_entry in timing.get('bestHours', []):
            hour = hour_entry['hour']
            avg = hour_entry['avgViewsPerSubscriber']
            count = hour_entry['videoCount']
            hour_agg[hour]['total_vps'] += avg * count
            hour_agg[hour]['total_count'] += count

    # Compute weighted averages
    day_avgs = {}
    for day, data in day_agg.items():
        if data['total_count'] > 0:
            day_avgs[day] = data['total_vps'] / data['total_count']

    hour_avgs = {}
    for hour, data in hour_agg.items():
        if data['total_count'] > 0:
            hour_avgs[hour] = data['total_vps'] / data['total_count']

    # Compute overall averages for multiplier calculation
    all_day_vps = [avg for avg in day_avgs.values()]
    overall_day_avg = sum(all_day_vps) / len(all_day_vps) if all_day_vps else 1

    all_hour_vps = [avg for avg in hour_avgs.values()]
    overall_hour_avg = sum(all_hour_vps) / len(all_hour_vps) if all_hour_vps else 1

    # Build byDayOfWeek
    by_day = []
    for day, avg in day_avgs.items():
        multiplier = avg / overall_day_avg if overall_day_avg > 0 else 1.0
        by_day.append({
            'day': day,
            'avgViews': round(avg, 2),
            'multiplier': round(multiplier, 2),
        })
    by_day.sort(key=lambda x: x['multiplier'], reverse=True)

    # Build byHourIST
    by_hour = []
    for hour, avg in hour_avgs.items():
        multiplier = avg / overall_hour_avg if overall_hour_avg > 0 else 1.0
        label = _get_hour_label(hour)
        by_hour.append({
            'hour': hour,
            'avgViews': round(avg, 2),
            'multiplier': round(multiplier, 2),
            'label': label,
        })
    by_hour.sort(key=lambda x: x['multiplier'], reverse=True)

    # Optimal
    best_day = by_day[0] if by_day else None
    best_hour = by_hour[0] if by_hour else None

    optimal = {}
    if best_day:
        optimal['day'] = best_day['day']
    if best_hour:
        optimal['hourIST'] = best_hour['hour']
        optimal['description'] = best_hour['label']

    if best_day and best_hour:
        optimal['multiplier'] = round(
            best_day['multiplier'] * best_hour['multiplier'], 2
        )
    elif best_day:
        optimal['multiplier'] = best_day['multiplier']
    elif best_hour:
        optimal['multiplier'] = best_hour['multiplier']

    return {
        'generatedAt': timestamp,
        'basedOnVideos': total_videos,
        'bestTimes': {
            'byDayOfWeek': by_day,
            'byHourIST': by_hour,
            'optimal': optimal,
        },
    }


def _build_content_gap_insights(
    content_gaps: dict,
    timestamp: str,
) -> dict:
    """Build ContentGapInsights document (flat format for recommender).

    Flattens: contentGaps.highOpportunity → root highOpportunity
    Maps avgViewsPerSubscriber → avgViews.
    Ensures saturated topics have {topic, competition} structure.
    """
    gaps = content_gaps.get('contentGaps', {})

    # Flatten high opportunity
    high_opp = []
    for opp in gaps.get('highOpportunity', []):
        high_opp.append({
            'topic': opp.get('topic', ''),
            'avgViews': opp.get('avgViewsPerSubscriber', 0),
            'videoCount': opp.get('videoCount', 0),
            'opportunityScore': opp.get('opportunityScore', 0),
        })

    # Flatten saturated topics with competition classification
    saturated = []
    for topic in gaps.get('saturatedTopics', []):
        content_share = topic.get('contentShare', 0)
        saturated.append({
            'topic': topic.get('topic', ''),
            'competition': 'high' if content_share > 20 else 'medium',
        })

    return {
        'generatedAt': timestamp,
        'highOpportunity': high_opp,
        'saturatedTopics': saturated,
    }


def _weighted_avg(entries: List[tuple]) -> float:
    """Compute weighted average from (value, weight) tuples."""
    if not entries:
        return 0.0
    total_weight = sum(w for _, w in entries)
    if total_weight == 0:
        return 0.0
    return sum(v * w for v, w in entries) / total_weight


def _get_hour_label(hour: int) -> str:
    """Get time-of-day label for an hour (IST)."""
    if 6 <= hour <= 11:
        return 'Morning'
    if 12 <= hour <= 16:
        return 'Afternoon'
    if 17 <= hour <= 21:
        return 'Evening'
    return 'Night'
