"""Main entry point for insights generation.

Generates per-content-type performance profiles by comparing feature
distributions between all videos and top 10% performers (by viewsPerSubscriber).
Output is raw statistical data — the recommender's LLM handles interpretation.

Firestore output structure:
    insights/{contentType}  — per-type profile (thumbnail + title features + timing)
    insights/contentGaps    — global content gap analysis, in the recommender's shape
                              (root highOpportunity/saturatedTopics + keywordGaps/formatGaps);
                              written only by the gaps step
    insights/summary        — overview of all content types
    insights/thumbnails     — recommender bridge: thumbnail insights
    insights/titles         — recommender bridge: title insights
    insights/timing         — recommender bridge: timing insights
"""

import argparse
import json
import math
import re
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone
from typing import Callable, List, Optional, Tuple

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import numpy as np

from .config import config
from .firebase_client import (
    initialize_firebase,
    get_all_videos_with_analyses,
    load_insight_profiles,
    save_insights,
)
from .profiler import (
    compute_feature_profile,
    compute_timing_profile,
    compute_feature_correlations,
    compute_recency_weight,
    normalize_analysis,
    MAX_CATEGORICAL_VALUES,
    MIN_VIDEOS_PER_TYPE,
)
from .gaps import GapAnalyzer
from .recommender_bridge import build_content_gaps_document, generate_recommender_documents

# Content type bucket for videos without a usable contentType; counted in the
# summary but never profiled as a real type.
UNKNOWN_CONTENT_TYPE = "unknown"

# insights/ doc IDs owned by non-profile documents; a content type normalizing to
# one of these gets a "type_" prefix so its profile cannot overwrite them.
RESERVED_DOC_NAMES = {"summary", "contentgaps", "thumbnails", "titles", "timing"}

# Key on the (copied) video wrapper holding the pre-winsorization VPS, used as a tie-break
UNCAPPED_VPS_KEY = "uncapped_vps"

# Warn when a document approaches Firestore's 1 MiB document limit
MAX_DOC_BYTES_WARNING = 800_000


def get_views_per_subscriber(video_data: dict) -> float:
    """Get viewsPerSubscriber for a video, computing if not stored."""
    calculated = video_data.get("video", {}).get("calculated", {})
    vps = calculated.get("viewsPerSubscriber")
    if vps and vps > 0:
        return float(vps)

    views = video_data.get("video", {}).get("viewCount", 0)
    subs = video_data.get("channel", {}).get("subscriberCount", 1)
    if subs and subs > 0:
        return views / subs
    return 0.0


def get_engagement_rate(video_data: dict) -> float:
    """Get engagementRate for a video."""
    calculated = video_data.get("video", {}).get("calculated", {})
    er = calculated.get("engagementRate")
    if er and er > 0:
        return float(er)
    return 0.0


def normalize_content_type(value) -> str:
    """Normalize a raw contentType: lowercase, trim, and collapse separators to '_'.

    "Recipe", " recipe " -> "recipe"; "list/top", "List Top", "list-top" -> "list_top".
    Missing / non-string / empty values -> "unknown".
    """
    if not isinstance(value, str):
        return UNKNOWN_CONTENT_TYPE
    normalized = re.sub(r"[\W_]+", "_", value.strip().lower()).strip("_")
    return normalized or UNKNOWN_CONTENT_TYPE


def profile_doc_name(content_type: str) -> str:
    """Firestore doc ID for a (normalized) content type profile, avoiding reserved IDs."""
    name = normalize_content_type(content_type)
    return f"type_{name}" if name in RESERVED_DOC_NAMES else name


def get_content_type(video_data: dict) -> str:
    """Extract the normalized content type from title analysis."""
    analysis = video_data.get("title_analysis") or {}
    content_signals = analysis.get("contentSignals") or {}
    return normalize_content_type(content_signals.get("contentType"))


def group_by_content_type(videos: list) -> dict:
    """Group videos by their normalized content type."""
    groups = defaultdict(list)
    for video in videos:
        content_type = get_content_type(video)
        groups[content_type].append(video)
    return dict(groups)


def remove_outliers(
    videos: list,
    get_vps_fn: Callable,
    min_subscribers: int = 1000,
    cap_percentile: int = 95,
) -> Tuple[list, dict]:
    """Remove outlier videos based on channel size and winsorize VPS.

    Args:
        videos: List of video data dicts.
        get_vps_fn: Function to get VPS from a video dict.
        min_subscribers: Minimum channel subscribers to include.
        cap_percentile: VPS percentile cap for winsorization.

    Returns:
        Tuple of (filtered_videos, outlier_stats).
    """
    original_count = len(videos)

    # Filter by minimum subscribers
    filtered = [v for v in videos if (v.get("channel", {}).get("subscriberCount") or 0) >= min_subscribers]
    removed_low_sub = original_count - len(filtered)

    # Winsorize VPS at cap_percentile
    if filtered:
        vps_values = [get_vps_fn(v) for v in filtered]
        cap = float(np.percentile(vps_values, cap_percentile))
        winsorized_count = sum(1 for vps in vps_values if vps > cap)

        # Store the effective (capped) VPS on copies of every video — including those
        # whose VPS was derived from viewCount/subscriberCount — so every downstream
        # consumer sees the same capped value. Originals are not mutated.
        for i, (v, vps) in enumerate(zip(filtered, vps_values)):
            video = v.get("video") or {}
            calculated = video.get("calculated") or {}
            capped_calculated = {**calculated, "viewsPerSubscriber": min(vps, cap)}
            filtered[i] = {
                **v,
                "video": {**video, "calculated": capped_calculated},
                UNCAPPED_VPS_KEY: vps,
            }
    else:
        cap = 0
        winsorized_count = 0

    stats = {
        "originalCount": original_count,
        "filteredCount": len(filtered),
        "removedLowSubscribers": removed_low_sub,
        "winsorizedCount": winsorized_count,
        "vpsCap": round(cap, 2),
        "minSubscribers": min_subscribers,
    }

    return filtered, stats


def split_top_performers(
    videos: list,
    percentile: int = 90,
    metric_fn: Optional[Callable] = None,
) -> tuple:
    """Split videos into all and top performers by a metric.

    The top group is chosen by rank: the ceil((100 - percentile)%) highest videos
    (at least one). Ties are broken deterministically by uncapped VPS (only when
    ranking by VPS), then video id, then input order. Selecting by rank rather than
    ``value >= threshold`` keeps the group at ~10% even when winsorizing creates
    many ties at the cap.

    Args:
        videos: List of video data dicts.
        percentile: Percentile threshold for top performers.
        metric_fn: Function to extract metric value (defaults to get_views_per_subscriber).

    Returns:
        Tuple of (all_videos, top_videos, threshold_value). threshold_value is the
        metric's percentile value (np.percentile), reported for reference only.
    """
    if metric_fn is None:
        metric_fn = get_views_per_subscriber

    metric_values = [metric_fn(v) for v in videos]

    if not metric_values:
        return videos, [], 0.0

    threshold = float(np.percentile(metric_values, percentile))
    top_n = max(1, math.ceil(len(videos) * (100 - percentile) / 100))
    by_vps = metric_fn is get_views_per_subscriber

    def rank_key(i: int):
        video = videos[i]
        uncapped = float(video.get(UNCAPPED_VPS_KEY, metric_values[i])) if by_vps else 0.0
        video_id = str(video.get("video_id") or (video.get("video") or {}).get("id") or "")
        return (-metric_values[i], -uncapped, video_id, i)

    top_indices = sorted(sorted(range(len(videos)), key=rank_key)[:top_n])
    top_videos = [videos[i] for i in top_indices]

    return videos, top_videos, threshold


def _compute_recency_weights(videos: list) -> List[float]:
    """Compute recency weights for a list of videos."""
    weights = []
    for v in videos:
        published_at = v.get("video", {}).get("publishedAt", "")
        weights.append(compute_recency_weight(published_at))
    return weights


def _align_weights(videos: list, all_weights: List[float], has_analysis_fn: Callable) -> List[float]:
    """Return weights only for videos that pass the has_analysis_fn filter."""
    return [w for v, w in zip(videos, all_weights) if has_analysis_fn(v)]


def _title_features(title_analysis: dict) -> dict:
    """Title analysis prepared for profiling: normalized lists, no descriptionAnalysis subtree."""
    normalized = normalize_analysis(title_analysis)
    return {k: v for k, v in normalized.items() if k != "descriptionAnalysis"}


def _pattern_performance(videos: list) -> dict:
    """Average (capped) VPS per categorical title patternType, for the recommender bridge."""
    by_pattern = defaultdict(list)
    for v in videos:
        structure = (v.get("title_analysis") or {}).get("structure") or {}
        pattern_type = structure.get("patternType")
        if isinstance(pattern_type, str) and pattern_type.strip():
            by_pattern[pattern_type.strip()].append(get_views_per_subscriber(v))
    if not by_pattern or len(by_pattern) > MAX_CATEGORICAL_VALUES:
        return {}
    return {
        pattern: {"avgViewsPerSubscriber": round(float(np.mean(vals)), 2), "count": len(vals)}
        for pattern, vals in by_pattern.items()
    }


def generate_content_type_profile(content_type: str, videos: list) -> dict:
    """Generate a complete profile for a content type.

    Includes thumbnail features, title features, description features,
    timing patterns, feature correlations, and engagement profile.
    Each compares all videos vs top 10% performers.
    """
    timestamp = datetime.now(timezone.utc).isoformat()

    all_videos, top_videos, threshold = split_top_performers(videos)
    vps_values = [get_views_per_subscriber(v) for v in all_videos]
    avg_vps = float(np.mean(vps_values)) if vps_values else 0

    # Compute recency weights (top_videos is a subset — reuse weights by identity)
    all_weights = _compute_recency_weights(all_videos)
    weight_by_id = {id(v): w for v, w in zip(all_videos, all_weights)}
    top_weights = [weight_by_id[id(v)] for v in top_videos]

    profile = {
        "contentType": content_type,
        "generatedAt": timestamp,
        "summary": {
            "totalVideos": len(all_videos),
            "top10Count": len(top_videos),
            "top10Threshold": round(threshold, 2),
            "avgViewsPerSubscriber": round(avg_vps, 2),
        },
    }

    # Thumbnail profile (only for videos that have thumbnail analysis)
    all_thumb = [v["thumbnail_analysis"] for v in all_videos if v.get("thumbnail_analysis")]
    top_thumb = [v["thumbnail_analysis"] for v in top_videos if v.get("thumbnail_analysis")]
    all_thumb_w = _align_weights(all_videos, all_weights, lambda v: v.get("thumbnail_analysis"))
    top_thumb_w = _align_weights(top_videos, top_weights, lambda v: v.get("thumbnail_analysis"))

    if all_thumb:
        profile["thumbnail"] = {
            "sampleSize": {"all": len(all_thumb), "top10": len(top_thumb)},
            "features": compute_feature_profile(all_thumb, top_thumb, all_thumb_w, top_thumb_w),
        }

    # Title profile (descriptionAnalysis is profiled separately below; word-list
    # fields normalized to lists so legacy and title_description data mix cleanly)
    title_by_id = {id(v): _title_features(v["title_analysis"]) for v in all_videos if v.get("title_analysis")}
    all_title = [title_by_id[id(v)] for v in all_videos if v.get("title_analysis")]
    top_title = [title_by_id[id(v)] for v in top_videos if v.get("title_analysis")]
    all_title_w = _align_weights(all_videos, all_weights, lambda v: v.get("title_analysis"))
    top_title_w = _align_weights(top_videos, top_weights, lambda v: v.get("title_analysis"))

    if all_title:
        profile["title"] = {
            "sampleSize": {"all": len(all_title), "top10": len(top_title)},
            "features": compute_feature_profile(all_title, top_title, all_title_w, top_title_w),
        }
        pattern_performance = _pattern_performance(all_videos)
        if pattern_performance:
            profile["title"]["patternPerformance"] = pattern_performance

    # Description profile (extracted from title_description analysis)
    all_desc = [
        desc for v in all_videos if v.get("title_analysis") and (desc := v["title_analysis"].get("descriptionAnalysis"))
    ]
    top_desc = [
        desc for v in top_videos if v.get("title_analysis") and (desc := v["title_analysis"].get("descriptionAnalysis"))
    ]

    if all_desc:

        def _has_desc(v):
            return v.get("title_analysis") and v["title_analysis"].get("descriptionAnalysis")

        all_desc_w = _align_weights(all_videos, all_weights, _has_desc)
        top_desc_w = _align_weights(top_videos, top_weights, _has_desc)

        profile["description"] = {
            "sampleSize": {"all": len(all_desc), "top10": len(top_desc)},
            "features": compute_feature_profile(all_desc, top_desc, all_desc_w, top_desc_w),
        }

    # Timing profile
    profile["timing"] = compute_timing_profile(all_videos, get_views_per_subscriber)

    # Feature correlations (thumbnail boolean features)
    if all_thumb and len(all_thumb) >= 30:
        profile["featureCorrelations"] = {
            "thumbnail": compute_feature_correlations(all_thumb, top_thumb),
        }
        if all_title and len(all_title) >= 30:
            profile["featureCorrelations"]["title"] = compute_feature_correlations(all_title, top_title)

    # Engagement profile (split by engagementRate instead of VPS)
    _, eng_top_videos, eng_threshold = split_top_performers(videos, metric_fn=get_engagement_rate)

    if eng_top_videos:
        eng_top_thumb = [v["thumbnail_analysis"] for v in eng_top_videos if v.get("thumbnail_analysis")]
        eng_top_title = [title_by_id[id(v)] for v in eng_top_videos if v.get("title_analysis")]
        eng_top_weights = [weight_by_id[id(v)] for v in eng_top_videos]
        eng_top_thumb_w = _align_weights(eng_top_videos, eng_top_weights, lambda v: v.get("thumbnail_analysis"))
        eng_top_title_w = _align_weights(eng_top_videos, eng_top_weights, lambda v: v.get("title_analysis"))

        engagement_profile = {
            "metric": "engagementRate",
            "top10Threshold": round(eng_threshold, 4),
            "top10Count": len(eng_top_videos),
        }

        if all_thumb and eng_top_thumb:
            engagement_profile["thumbnail"] = {
                "sampleSize": {"all": len(all_thumb), "top10": len(eng_top_thumb)},
                "features": compute_feature_profile(all_thumb, eng_top_thumb, all_thumb_w, eng_top_thumb_w),
            }
        if all_title and eng_top_title:
            engagement_profile["title"] = {
                "sampleSize": {"all": len(all_title), "top10": len(eng_top_title)},
                "features": compute_feature_profile(all_title, eng_top_title, all_title_w, eng_top_title_w),
            }

        profile["engagementProfile"] = engagement_profile

    return profile


def save_to_file(name: str, data: dict) -> None:
    """Save report to local JSON file."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filepath = config.OUTPUTS_DIR / f"{name}_{timestamp}.json"

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"    Saved to {filepath}")


def _write_insight(doc_name: str, data: dict, dry_run: bool) -> None:
    """Save an insights document to Firestore (unless dry run), warning on large docs."""
    size = len(json.dumps(data, ensure_ascii=False, default=str).encode("utf-8"))
    if size > MAX_DOC_BYTES_WARNING:
        print(f"    WARNING: insights/{doc_name} is ~{size // 1024} KB (Firestore limit is 1 MiB)")
    if not dry_run:
        save_insights(doc_name, data)
        print(f"    Saved to Firestore: insights/{doc_name}")


def _write_bridge_docs(profiles: dict, dry_run: bool) -> None:
    """Generate and save the recommender bridge docs (thumbnails, titles, timing).

    insights/contentGaps is not written here: the gaps step is its only writer.
    """
    print("\nGenerating recommender bridge documents...")
    bridge_docs = generate_recommender_documents(profiles, None)
    for doc_name, doc_data in bridge_docs.items():
        _write_insight(doc_name, doc_data, dry_run)
        save_to_file(f"bridge_{doc_name}", doc_data)


def _run_bridge_only(dry_run: bool) -> None:
    """Rebuild bridge docs from the profiles already stored in Firestore.

    Refuses to write anything when no stored profiles are found, so live
    recommender documents are never overwritten with empty data.
    """
    print("Loading stored content type profiles from Firestore...")
    profiles = {}
    for doc_id, data in load_insight_profiles().items():
        content_type = data["contentType"]
        # Skip stale docs the profiles step would no longer write: an "unknown"
        # profile, or a pre-normalization doc (e.g. "Recipe") whose ID differs
        # from the current doc name for its content type.
        if normalize_content_type(content_type) == UNKNOWN_CONTENT_TYPE or doc_id != profile_doc_name(content_type):
            print(f"  Skipping stale profile doc insights/{doc_id} (contentType={content_type!r})")
            continue
        profiles[doc_id] = data
    if not profiles:
        print("\nNo stored content type profiles found in insights/. Run with --type profiles (or all) first.")
        print("Refusing to overwrite recommender bridge documents with empty data.")
        sys.exit(1)
    print(f"  Loaded {len(profiles)} profiles: {', '.join(sorted(profiles))}")
    _write_bridge_docs(profiles, dry_run)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="YouTube Intelligence System - Phase 3: Insights")
    parser.add_argument(
        "--type",
        "-t",
        choices=["all", "profiles", "gaps", "bridge"],
        default="all",
        help="Type of insights to generate (profiles=per content type, gaps=content gaps, bridge=recommender bridge only)",
    )
    parser.add_argument("--channel", "-c", help="Single channel ID to process (dry run — only loads this channel)")
    parser.add_argument("--dry-run", action="store_true", help="Skip saving to Firestore (local files only)")

    args = parser.parse_args()

    dry_run = args.dry_run or bool(args.channel)

    print("\n" + "=" * 60)
    print("  YouTube Intelligence System - Phase 3: Insights")
    if dry_run:
        print("  MODE: Dry run" + (f" (channel: {args.channel})" if args.channel else ""))
    print("=" * 60 + "\n")

    # Initialize
    print("Initializing Firebase...")
    initialize_firebase()
    print("Connected\n")

    # Bridge-only: transform stored profiles; no video loading, no summary rewrite
    if args.type == "bridge":
        _run_bridge_only(dry_run)
        return

    # Load data
    if args.channel:
        print(f"Loading videos for channel {args.channel}...")
    else:
        print("Loading all videos with analyses...")
    videos = get_all_videos_with_analyses(channel_id=args.channel)
    print(f"  Loaded {len(videos)} videos with analyses")

    if not videos:
        print("\nNo analyzed videos found. Run Phase 2 first.")
        sys.exit(1)

    # Remove outliers
    print("\nRemoving outliers...")
    videos, outlier_stats = remove_outliers(videos, get_views_per_subscriber)
    print(
        f"  Removed {outlier_stats['removedLowSubscribers']} videos from low-subscriber channels (<{outlier_stats['minSubscribers']} subs)"
    )
    print(f"  Winsorized {outlier_stats['winsorizedCount']} videos at VPS cap {outlier_stats['vpsCap']}")
    print(f"  Remaining: {outlier_stats['filteredCount']} videos")

    # Group by content type
    groups = group_by_content_type(videos)
    print(f"\n  Found {len(groups)} content types:")
    for ct, vids in sorted(groups.items(), key=lambda x: -len(x[1])):
        print(f"    {ct}: {len(vids)} videos")

    print("\n" + "-" * 60)

    generated_profiles = {}

    # Generate per-content-type profiles
    if args.type in ["all", "profiles"]:
        print("\nGenerating content type profiles...")

        for content_type, type_videos in sorted(groups.items(), key=lambda x: -len(x[1])):
            if content_type == UNKNOWN_CONTENT_TYPE:
                print(f"  Skipping '{content_type}' ({len(type_videos)} videos without a content type)")
                continue
            if len(type_videos) < MIN_VIDEOS_PER_TYPE:
                print(f"  Skipping '{content_type}' ({len(type_videos)} videos, need {MIN_VIDEOS_PER_TYPE})")
                continue

            print(f"\n  Profiling '{content_type}' ({len(type_videos)} videos)...")
            profile = generate_content_type_profile(content_type, type_videos)

            # Save to file first (for debugging), then Firestore
            doc_name = profile_doc_name(content_type)
            save_to_file(doc_name, profile)
            _write_insight(doc_name, profile, dry_run)

            generated_profiles[doc_name] = profile

        # Report stored profiles for types that were not regenerated (not deleted:
        # a type may be temporarily below MIN_VIDEOS_PER_TYPE)
        if not dry_run:
            stale = sorted(set(load_insight_profiles()) - set(generated_profiles))
            if stale:
                print(f"\n  WARNING: stale profile docs not regenerated this run: {', '.join(stale)}")

    # Generate content gaps (sole writer of insights/contentGaps, in the recommender's shape)
    if args.type in ["all", "gaps"]:
        print("\nGenerating content gap analysis...")
        gap_analyzer = GapAnalyzer(videos, get_views_per_subscriber)

        gap_report = {
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "totalVideos": len(videos),
            "contentGaps": gap_analyzer.find_content_gaps(),
            "keywordGaps": gap_analyzer.analyze_keyword_gaps(),
            "formatGaps": gap_analyzer.analyze_format_gaps(),
        }
        content_gaps_doc = build_content_gaps_document(gap_report, gap_report["generatedAt"])

        _write_insight("contentGaps", content_gaps_doc, dry_run)
        save_to_file("contentGaps", content_gaps_doc)

    # Generate recommender bridge documents
    if args.type == "all":
        if generated_profiles:
            _write_bridge_docs(generated_profiles, dry_run)
        else:
            print("\nNo profiles generated — not overwriting recommender bridge documents.")

    # Generate summary
    summary = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "totalVideos": len(videos),
        "outlierStats": outlier_stats,
        "contentTypes": [
            {
                "type": ct,
                "count": len(vids),
                "avgViewsPerSubscriber": round(float(np.mean([get_views_per_subscriber(v) for v in vids])), 2),
            }
            for ct, vids in sorted(groups.items(), key=lambda x: -len(x[1]))
        ],
    }
    _write_insight("summary", summary, dry_run)
    save_to_file("summary", summary)

    # Print summary
    print("\n" + "=" * 60)
    print("  Insights Generation Complete!")
    print("=" * 60)
    print(f"\n  Profiles generated: {len(generated_profiles)}")
    print(f"  Content types found: {len(groups)}")
    print(f"  Total videos: {len(videos)}")
    print("  Metric: viewsPerSubscriber")
    print(f"\n  Output files: {config.OUTPUTS_DIR}")
    print("  Firestore: insights/{contentType}, insights/contentGaps, insights/summary")
    print("  Recommender bridge: insights/thumbnails, insights/titles, insights/timing")
    print("\n" + "=" * 60 + "\n")


if __name__ == "__main__":
    main()
