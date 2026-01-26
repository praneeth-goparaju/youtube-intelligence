"""Main entry point for insights generation."""

import argparse
import sys
from pathlib import Path

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.constants import (
    ANALYSIS_TYPE_THUMBNAIL,
    ANALYSIS_TYPE_TITLE,
    ANALYSIS_TYPE_DESCRIPTION,
    INSIGHT_TYPE_THUMBNAILS,
    INSIGHT_TYPE_TITLES,
    INSIGHT_TYPE_TIMING,
    INSIGHT_TYPE_CONTENT_GAPS,
)

from .config import config
from .firebase_client import initialize_firebase, get_all_videos_with_analysis
from .correlations import CorrelationAnalyzer
from .patterns import PatternExtractor
from .gaps import GapAnalyzer
from .reports import ReportGenerator


def run_thumbnail_insights(videos: list, reporter: ReportGenerator) -> dict:
    """Generate thumbnail insights."""
    print("\nGenerating thumbnail insights...")

    correlator = CorrelationAnalyzer(videos)
    correlations = correlator.find_top_correlations('view_count')

    extractor = PatternExtractor(videos)
    patterns = extractor.extract_thumbnail_patterns()

    report = reporter.generate_thumbnail_report(patterns, correlations)
    reporter.save_to_firestore(INSIGHT_TYPE_THUMBNAILS, report)
    reporter.save_to_file(INSIGHT_TYPE_THUMBNAILS, report)

    return report


def run_title_insights(videos: list, reporter: ReportGenerator) -> dict:
    """Generate title insights."""
    print("\nGenerating title insights...")

    correlator = CorrelationAnalyzer(videos)
    correlations = correlator.find_top_correlations('view_count')

    extractor = PatternExtractor(videos)
    patterns = extractor.extract_title_patterns()

    report = reporter.generate_title_report(patterns, correlations)
    reporter.save_to_firestore(INSIGHT_TYPE_TITLES, report)
    reporter.save_to_file(INSIGHT_TYPE_TITLES, report)

    return report


def run_timing_insights(videos: list, reporter: ReportGenerator) -> dict:
    """Generate timing insights."""
    print("\nGenerating timing insights...")

    extractor = PatternExtractor(videos)
    timing = extractor.extract_timing_patterns()

    report = reporter.generate_timing_report(timing)
    reporter.save_to_firestore(INSIGHT_TYPE_TIMING, report)
    reporter.save_to_file(INSIGHT_TYPE_TIMING, report)

    return report


def run_gap_analysis(videos: list, reporter: ReportGenerator) -> dict:
    """Generate content gap analysis."""
    print("\nGenerating content gap analysis...")

    analyzer = GapAnalyzer(videos)

    content_gaps = analyzer.find_content_gaps()
    keyword_gaps = analyzer.analyze_keyword_gaps()
    format_gaps = analyzer.analyze_format_gaps()

    report = reporter.generate_gap_report(content_gaps, keyword_gaps, format_gaps)
    reporter.save_to_firestore(INSIGHT_TYPE_CONTENT_GAPS, report)
    reporter.save_to_file(INSIGHT_TYPE_CONTENT_GAPS, report)

    return report


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='YouTube Intelligence System - Phase 3: Pattern Discovery'
    )
    parser.add_argument(
        '--type', '-t',
        choices=['all', 'thumbnails', 'titles', 'timing', 'gaps'],
        default='all',
        help='Type of insights to generate'
    )

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("  YouTube Intelligence System - Phase 3: Insights")
    print("=" * 60 + "\n")

    # Initialize
    print("Initializing Firebase...")
    initialize_firebase()
    print("Connected\n")

    reporter = ReportGenerator()

    # Load data based on analysis type
    print("Loading analyzed videos...")

    if args.type in ['all', 'thumbnails']:
        thumbnail_videos = get_all_videos_with_analysis(ANALYSIS_TYPE_THUMBNAIL)
        print(f"  Thumbnail analysis: {len(thumbnail_videos)} videos")
    else:
        thumbnail_videos = []

    if args.type in ['all', 'titles']:
        title_videos = get_all_videos_with_analysis(ANALYSIS_TYPE_TITLE)
        print(f"  Title analysis: {len(title_videos)} videos")
    else:
        title_videos = []

    # Use any available analysis for timing and gaps
    # Fix: Check length explicitly since empty list is falsy but we want non-empty lists
    if len(thumbnail_videos) > 0:
        all_videos = thumbnail_videos
    elif len(title_videos) > 0:
        all_videos = title_videos
    else:
        all_videos = get_all_videos_with_analysis(ANALYSIS_TYPE_DESCRIPTION)

    print(f"  Total videos for analysis: {len(all_videos)}")

    if not all_videos:
        print("\nNo analyzed videos found. Run Phase 2 first.")
        sys.exit(1)

    print("\n" + "-" * 60)

    # Generate insights
    reports = {}

    if args.type in ['all', 'thumbnails'] and thumbnail_videos:
        reports[INSIGHT_TYPE_THUMBNAILS] = run_thumbnail_insights(thumbnail_videos, reporter)

    if args.type in ['all', 'titles'] and title_videos:
        reports[INSIGHT_TYPE_TITLES] = run_title_insights(title_videos, reporter)

    if args.type in ['all', 'timing'] and all_videos:
        reports[INSIGHT_TYPE_TIMING] = run_timing_insights(all_videos, reporter)

    if args.type in ['all', 'gaps'] and all_videos:
        reports[INSIGHT_TYPE_CONTENT_GAPS] = run_gap_analysis(all_videos, reporter)

    # Print summary
    print("\n" + "=" * 60)
    print("  Insights Generation Complete!")
    print("=" * 60)

    print(f"\nReports generated: {len(reports)}")
    for report_type in reports:
        print(f"  - {report_type}")

    print(f"\nOutput files saved to: {config.OUTPUTS_DIR}")
    print("Insights saved to Firestore: insights/{{type}}")

    print("\n" + "=" * 60 + "\n")


if __name__ == '__main__':
    main()
