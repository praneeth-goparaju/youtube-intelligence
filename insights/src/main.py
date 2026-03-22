"""Main entry point for insights generation.

Generates per-content-type performance profiles by comparing feature
distributions between all videos and top 10% performers (by viewsPerSubscriber).
Output is raw statistical data — the recommender's LLM handles interpretation.

Firestore output structure:
    insights/{contentType}  — per-type profile (thumbnail + title features + timing)
    insights/contentGaps    — global content gap analysis
    insights/summary        — overview of all content types
    insights/thumbnails     — recommender bridge: thumbnail insights
    insights/titles         — recommender bridge: title insights
    insights/timing         — recommender bridge: timing insights
"""

import argparse
import json
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
    save_insights,
)
from .profiler import (
    compute_feature_profile,
    compute_timing_profile,
    compute_feature_correlations,
    compute_recency_weight,
    MIN_VIDEOS_PER_TYPE,
)
from .gaps import GapAnalyzer


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


def get_content_type(video_data: dict) -> str:
    """Extract content type from title analysis."""
    analysis = video_data.get("title_analysis", {})
    content_signals = analysis.get("contentSignals", {})
    return content_signals.get("contentType", "unknown")


def group_by_content_type(videos: list) -> dict:
    """Group videos by their content type."""
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

        # Cap the calculated VPS in-place
        for v in filtered:
            calculated = v.get("video", {}).get("calculated", {})
            vps = calculated.get("viewsPerSubscriber")
            if vps and vps > cap:
                calculated["viewsPerSubscriber"] = cap
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

    Args:
        videos: List of video data dicts.
        percentile: Percentile threshold for top performers.
        metric_fn: Function to extract metric value (defaults to get_views_per_subscriber).

    Returns:
        Tuple of (all_videos, top_videos, threshold_value)
    """
    if metric_fn is None:
        metric_fn = get_views_per_subscriber

    metric_values = [metric_fn(v) for v in videos]

    if not metric_values:
        return videos, [], 0.0

    threshold = float(np.percentile(metric_values, percentile))
    top_videos = [v for v, val in zip(videos, metric_values) if val >= threshold]

    return videos, top_videos, threshold


def _extract_description_analysis(title_analysis: dict) -> dict:
    """Extract the descriptionAnalysis sub-dict for separate profiling.

    Args:
        title_analysis: The full title_description analysis dict.

    Returns:
        The descriptionAnalysis sub-dict, or empty dict if not present.
    """
    return title_analysis.get("descriptionAnalysis", {})


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

    # Title profile
    all_title = [v["title_analysis"] for v in all_videos if v.get("title_analysis")]
    top_title = [v["title_analysis"] for v in top_videos if v.get("title_analysis")]
    all_title_w = _align_weights(all_videos, all_weights, lambda v: v.get("title_analysis"))
    top_title_w = _align_weights(top_videos, top_weights, lambda v: v.get("title_analysis"))

    if all_title:
        profile["title"] = {
            "sampleSize": {"all": len(all_title), "top10": len(top_title)},
            "features": compute_feature_profile(all_title, top_title, all_title_w, top_title_w),
        }

    # Description profile (extracted from title_description analysis)
    all_desc = [
        desc
        for v in all_videos
        if v.get("title_analysis") and (desc := _extract_description_analysis(v["title_analysis"]))
    ]
    top_desc = [
        desc
        for v in top_videos
        if v.get("title_analysis") and (desc := _extract_description_analysis(v["title_analysis"]))
    ]

    if all_desc:

        def _has_desc(v):
            return v.get("title_analysis") and _extract_description_analysis(v["title_analysis"])

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
        eng_top_title = [v["title_analysis"] for v in eng_top_videos if v.get("title_analysis")]

        engagement_profile = {
            "metric": "engagementRate",
            "top10Threshold": round(eng_threshold, 4),
            "top10Count": len(eng_top_videos),
        }

        if all_thumb and eng_top_thumb:
            engagement_profile["thumbnail"] = {
                "sampleSize": {"all": len(all_thumb), "top10": len(eng_top_thumb)},
                "features": compute_feature_profile(all_thumb, eng_top_thumb),
            }
        if all_title and eng_top_title:
            engagement_profile["title"] = {
                "sampleSize": {"all": len(all_title), "top10": len(eng_top_title)},
                "features": compute_feature_profile(all_title, eng_top_title),
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
            if len(type_videos) < MIN_VIDEOS_PER_TYPE:
                print(f"  Skipping '{content_type}' ({len(type_videos)} videos, need {MIN_VIDEOS_PER_TYPE})")
                continue

            print(f"\n  Profiling '{content_type}' ({len(type_videos)} videos)...")
            profile = generate_content_type_profile(content_type, type_videos)

            # Save to file first (for debugging), then Firestore
            doc_name = content_type.replace(" ", "_").replace("/", "_").replace(",", "_").lower()
            save_to_file(doc_name, profile)
            if not dry_run:
                save_insights(doc_name, profile)
                print(f"    Saved to Firestore: insights/{doc_name}")

            generated_profiles[doc_name] = profile

    # Generate content gaps
    gap_report = None
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

        if not dry_run:
            save_insights("contentGaps", gap_report)
            print("    Saved to Firestore: insights/contentGaps")
        save_to_file("contentGaps", gap_report)

    # Generate recommender bridge documents
    if args.type in ["all", "bridge"]:
        print("\nGenerating recommender bridge documents...")
        from .recommender_bridge import generate_recommender_documents

        bridge_docs = generate_recommender_documents(generated_profiles, gap_report)

        for doc_name, doc_data in bridge_docs.items():
            if not dry_run:
                save_insights(doc_name, doc_data)
                print(f"    Saved to Firestore: insights/{doc_name}")
            save_to_file(f"bridge_{doc_name}", doc_data)

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
    if not dry_run:
        save_insights("summary", summary)
        print("\n    Saved summary to Firestore: insights/summary")
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
