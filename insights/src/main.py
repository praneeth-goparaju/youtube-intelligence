"""Main entry point for insights generation.

Generates per-content-type performance profiles by comparing feature
distributions between all videos and top 10% performers (by viewsPerSubscriber).
Output is raw statistical data — the recommender's LLM handles interpretation.

Firestore output structure:
    insights/{contentType}  — per-type profile (thumbnail + title features + timing)
    insights/contentGaps    — global content gap analysis
    insights/summary        — overview of all content types
"""

import argparse
import json
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone

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
    MIN_VIDEOS_PER_TYPE,
)
from .gaps import GapAnalyzer


def get_views_per_subscriber(video_data: dict) -> float:
    """Get viewsPerSubscriber for a video, computing if not stored."""
    calculated = video_data.get('video', {}).get('calculated', {})
    vps = calculated.get('viewsPerSubscriber')
    if vps and vps > 0:
        return float(vps)

    views = video_data.get('video', {}).get('viewCount', 0)
    subs = video_data.get('channel', {}).get('subscriberCount', 1)
    if subs and subs > 0:
        return views / subs
    return 0.0


def get_content_type(video_data: dict) -> str:
    """Extract content type from title analysis."""
    analysis = video_data.get('title_analysis', {})
    content_signals = analysis.get('contentSignals', {})
    return content_signals.get('contentType', 'unknown')


def group_by_content_type(videos: list) -> dict:
    """Group videos by their content type."""
    groups = defaultdict(list)
    for video in videos:
        content_type = get_content_type(video)
        groups[content_type].append(video)
    return dict(groups)


def split_top_performers(videos: list, percentile: int = 90) -> tuple:
    """Split videos into all and top performers by viewsPerSubscriber.

    Returns:
        Tuple of (all_videos, top_videos, threshold_value)
    """
    vps_values = [get_views_per_subscriber(v) for v in videos]

    if not vps_values:
        return videos, [], 0.0

    threshold = float(np.percentile(vps_values, percentile))
    top_videos = [
        v for v, vps in zip(videos, vps_values) if vps >= threshold
    ]

    return videos, top_videos, threshold


def generate_content_type_profile(content_type: str, videos: list) -> dict:
    """Generate a complete profile for a content type.

    Includes thumbnail features, title features, and timing patterns,
    each comparing all videos vs top 10% performers.
    """
    timestamp = datetime.now(timezone.utc).isoformat()

    all_videos, top_videos, threshold = split_top_performers(videos)
    vps_values = [get_views_per_subscriber(v) for v in all_videos]
    avg_vps = float(np.mean(vps_values)) if vps_values else 0

    profile = {
        'contentType': content_type,
        'generatedAt': timestamp,
        'summary': {
            'totalVideos': len(all_videos),
            'top10Count': len(top_videos),
            'top10Threshold': round(threshold, 2),
            'avgViewsPerSubscriber': round(avg_vps, 2),
        },
    }

    # Thumbnail profile (only for videos that have thumbnail analysis)
    all_thumb = [
        v['thumbnail_analysis'] for v in all_videos
        if v.get('thumbnail_analysis')
    ]
    top_thumb = [
        v['thumbnail_analysis'] for v in top_videos
        if v.get('thumbnail_analysis')
    ]

    if all_thumb:
        profile['thumbnail'] = {
            'sampleSize': {'all': len(all_thumb), 'top10': len(top_thumb)},
            'features': compute_feature_profile(all_thumb, top_thumb),
        }

    # Title profile
    all_title = [
        v['title_analysis'] for v in all_videos
        if v.get('title_analysis')
    ]
    top_title = [
        v['title_analysis'] for v in top_videos
        if v.get('title_analysis')
    ]

    if all_title:
        profile['title'] = {
            'sampleSize': {'all': len(all_title), 'top10': len(top_title)},
            'features': compute_feature_profile(all_title, top_title),
        }

    # Timing profile
    profile['timing'] = compute_timing_profile(
        all_videos, get_views_per_subscriber
    )

    return profile


def save_to_file(name: str, data: dict) -> None:
    """Save report to local JSON file."""
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    filepath = config.OUTPUTS_DIR / f"{name}_{timestamp}.json"

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"    Saved to {filepath}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='YouTube Intelligence System - Phase 3: Insights'
    )
    parser.add_argument(
        '--type', '-t',
        choices=['all', 'profiles', 'gaps'],
        default='all',
        help='Type of insights to generate (profiles=per content type, gaps=content gaps)'
    )

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("  YouTube Intelligence System - Phase 3: Insights")
    print("=" * 60 + "\n")

    # Initialize
    print("Initializing Firebase...")
    initialize_firebase()
    print("Connected\n")

    # Load data
    print("Loading all videos with analyses...")
    videos = get_all_videos_with_analyses()
    print(f"  Loaded {len(videos)} videos with analyses")

    if not videos:
        print("\nNo analyzed videos found. Run Phase 2 first.")
        sys.exit(1)

    # Group by content type
    groups = group_by_content_type(videos)
    print(f"  Found {len(groups)} content types:")
    for ct, vids in sorted(groups.items(), key=lambda x: -len(x[1])):
        print(f"    {ct}: {len(vids)} videos")

    print("\n" + "-" * 60)

    profiles_generated = 0

    # Generate per-content-type profiles
    if args.type in ['all', 'profiles']:
        print("\nGenerating content type profiles...")

        for content_type, type_videos in sorted(
            groups.items(), key=lambda x: -len(x[1])
        ):
            if len(type_videos) < MIN_VIDEOS_PER_TYPE:
                print(f"  Skipping '{content_type}' "
                      f"({len(type_videos)} videos, need {MIN_VIDEOS_PER_TYPE})")
                continue

            print(f"\n  Profiling '{content_type}' ({len(type_videos)} videos)...")
            profile = generate_content_type_profile(content_type, type_videos)

            # Save to Firestore and file
            doc_name = content_type.replace(' ', '_').lower()
            save_insights(doc_name, profile)
            print(f"    Saved to Firestore: insights/{doc_name}")
            save_to_file(doc_name, profile)

            profiles_generated += 1

    # Generate content gaps
    if args.type in ['all', 'gaps']:
        print("\nGenerating content gap analysis...")
        gap_analyzer = GapAnalyzer(videos, get_views_per_subscriber)

        gap_report = {
            'generatedAt': datetime.now(timezone.utc).isoformat(),
            'totalVideos': len(videos),
            'contentGaps': gap_analyzer.find_content_gaps(),
            'keywordGaps': gap_analyzer.analyze_keyword_gaps(),
            'formatGaps': gap_analyzer.analyze_format_gaps(),
        }

        save_insights('contentGaps', gap_report)
        print("    Saved to Firestore: insights/contentGaps")
        save_to_file('contentGaps', gap_report)

    # Generate summary
    summary = {
        'generatedAt': datetime.now(timezone.utc).isoformat(),
        'totalVideos': len(videos),
        'contentTypes': [
            {
                'type': ct,
                'count': len(vids),
                'avgViewsPerSubscriber': round(
                    float(np.mean([
                        get_views_per_subscriber(v) for v in vids
                    ])), 2
                ),
            }
            for ct, vids in sorted(groups.items(), key=lambda x: -len(x[1]))
        ],
    }
    save_insights('summary', summary)
    print("\n    Saved summary to Firestore: insights/summary")
    save_to_file('summary', summary)

    # Print summary
    print("\n" + "=" * 60)
    print("  Insights Generation Complete!")
    print("=" * 60)
    print(f"\n  Profiles generated: {profiles_generated}")
    print(f"  Content types found: {len(groups)}")
    print(f"  Total videos: {len(videos)}")
    print(f"  Metric: viewsPerSubscriber")
    print(f"\n  Output files: {config.OUTPUTS_DIR}")
    print("  Firestore: insights/{contentType}, insights/contentGaps, insights/summary")
    print("\n" + "=" * 60 + "\n")


if __name__ == '__main__':
    main()
