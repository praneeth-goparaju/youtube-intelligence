"""Main entry point for the recommendation engine."""

import argparse
import json
import sys

from .config import config
from .firebase_client import initialize_firebase, get_all_insights
from .engine import RecommendationEngine


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='YouTube Intelligence System - Phase 4: Recommendations'
    )
    parser.add_argument(
        '--topic', '-t',
        type=str,
        required=True,
        help='Topic for the video (e.g., "biryani", "Germany trip")'
    )
    parser.add_argument(
        '--type', '-c',
        type=str,
        default='recipe',
        choices=['recipe', 'vlog', 'tutorial', 'review', 'challenge'],
        help='Content type'
    )
    parser.add_argument(
        '--angle', '-a',
        type=str,
        default=None,
        help='Unique angle (e.g., "Germany kitchen", "budget version")'
    )
    parser.add_argument(
        '--audience',
        type=str,
        default='telugu-audience',
        help='Target audience description'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default=None,
        help='Output file path (JSON)'
    )

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("  YouTube Intelligence System - Recommendations")
    print("=" * 60 + "\n")

    # Initialize
    print("Initializing Firebase...")
    initialize_firebase()
    print("Connected")

    # Check for insights
    print("Loading insights...")
    insights = get_all_insights()
    if not insights:
        print("\nWarning: No insights found. Run Phase 3 first for better recommendations.")
    else:
        print(f"Loaded insights: {', '.join(insights.keys())}")

    # Generate recommendation
    print(f"\nGenerating recommendation for: {args.topic}")
    print(f"Content type: {args.type}")
    if args.angle:
        print(f"Unique angle: {args.angle}")
    print(f"Target audience: {args.audience}")
    print("\n" + "-" * 60)

    engine = RecommendationEngine()
    recommendation = engine.generate_recommendation(
        topic=args.topic,
        content_type=args.type,
        unique_angle=args.angle,
        target_audience=args.audience,
    )

    # Print recommendation
    print("\n" + "=" * 60)
    print("  RECOMMENDATION")
    print("=" * 60 + "\n")

    # Titles
    print("TITLES:")
    titles = recommendation.get('titles', {})
    primary = titles.get('primary', {})
    print(f"  Primary (Combined): {primary.get('combined', 'N/A')}")
    print(f"  Primary (English):  {primary.get('english', 'N/A')}")
    print(f"  Primary (Telugu):   {primary.get('telugu', 'N/A')}")
    print("\n  Alternatives:")
    for alt in titles.get('alternatives', [])[:3]:
        print(f"    - {alt.get('title', 'N/A')}")

    # Thumbnail
    print("\nTHUMBNAIL:")
    thumbnail = recommendation.get('thumbnail', {})
    print(f"  Layout: {thumbnail.get('layout', 'N/A')}")
    elements = thumbnail.get('elements', {})
    if elements.get('face'):
        face = elements['face']
        print(f"  Face: {face.get('expression', 'N/A')} at {face.get('position', 'N/A')}")
    if elements.get('text', {}).get('primary'):
        text = elements['text']['primary']
        print(f"  Primary Text: {text.get('content', 'N/A')} ({text.get('color', 'N/A')})")
    colors = thumbnail.get('colors', {})
    if colors:
        print(f"  Colors: BG={colors.get('background', 'N/A')}, Accent={colors.get('accent', 'N/A')}")

    # Tags
    print("\nTAGS:")
    tags = recommendation.get('tags', {})
    print(f"  Primary: {', '.join(tags.get('primary', [])[:5])}")
    print(f"  Telugu:  {', '.join(tags.get('telugu', [])[:3])}")
    print(f"  Longtail: {', '.join(tags.get('longtail', [])[:3])}")

    # Posting
    print("\nOPTIMAL POSTING:")
    posting = recommendation.get('posting', {})
    print(f"  Best: {posting.get('bestDay', 'N/A')} at {posting.get('bestTime', 'N/A')}")
    print(f"  Alternatives: {', '.join(posting.get('alternativeTimes', [])[:2])}")

    # Prediction
    print("\nPERFORMANCE PREDICTION:")
    prediction = recommendation.get('prediction', {})
    view_range = prediction.get('expectedViewRange', {})
    print(f"  Expected Views: {view_range.get('low', 'N/A')} - {view_range.get('high', 'N/A')}")
    print(f"  Positive Factors: {', '.join(prediction.get('positiveFactors', [])[:3])}")
    print(f"  Risk Factors: {', '.join(prediction.get('riskFactors', [])[:3])}")

    # Content
    print("\nCONTENT TIPS:")
    content = recommendation.get('content', {})
    print(f"  Duration: {content.get('optimalDuration', 'N/A')}")
    print(f"  Must Include: {', '.join(content.get('mustInclude', [])[:4])}")

    print("\n" + "=" * 60)

    # Save to file if requested
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(recommendation, f, indent=2, ensure_ascii=False)
        print(f"\nFull recommendation saved to: {args.output}")

    print("\n")


if __name__ == '__main__':
    main()
