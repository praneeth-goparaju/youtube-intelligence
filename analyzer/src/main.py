"""Main entry point for the analyzer."""

import argparse
import sys

from .config import validate_config, config
from .firebase_client import initialize_firebase
from .gemini_client import test_connection
from .processors.batch import BatchProcessor, run_all_analysis


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='YouTube Intelligence System - AI Analysis'
    )
    parser.add_argument(
        '--type', '-t',
        choices=['all', 'thumbnail', 'title', 'description', 'tags', 'content_structure'],
        default='all',
        help='Type of analysis to run (content_structure infers video structure from metadata)'
    )
    parser.add_argument(
        '--limit', '-l',
        type=int,
        default=None,
        help='Limit videos per channel'
    )
    parser.add_argument(
        '--channel', '-c',
        type=str,
        default=None,
        help='Process only this channel ID'
    )
    parser.add_argument(
        '--validate',
        action='store_true',
        help='Only validate configuration and connections'
    )

    args = parser.parse_args()

    # Validate channel ID format if provided
    if args.channel:
        # YouTube channel IDs start with UC and are 24 characters long
        if not args.channel.startswith('UC') or len(args.channel) != 24:
            print(f"\nError: Invalid channel ID format: {args.channel}")
            print("Channel IDs should start with 'UC' and be 24 characters long.")
            print("Example: UCxxxxxxxxxxxxxxxxxxxxxxx")
            sys.exit(1)

    # Validate configuration
    print("\n" + "=" * 60)
    print("  YouTube Intelligence System - Phase 2: AI Analysis")
    print("=" * 60 + "\n")

    print("Validating configuration...")
    if not validate_config():
        print("\nConfiguration validation failed. Please check your .env file.")
        sys.exit(1)
    print("Configuration OK")

    # Initialize Firebase
    print("Initializing Firebase...")
    initialize_firebase()
    print("Firebase connected")

    # Test Gemini connection
    print("Testing Gemini API connection...")
    if not test_connection():
        print("\nGemini API connection failed. Please check your GOOGLE_API_KEY.")
        sys.exit(1)
    print(f"Gemini API connected (model: {config.GEMINI_MODEL})")

    if args.validate:
        print("\nValidation complete. All connections OK!")
        sys.exit(0)

    # Run analysis
    print("\n" + "-" * 60)

    if args.channel:
        # Process single channel
        if args.type == 'all':
            for analysis_type in ['thumbnail', 'title', 'description', 'tags', 'content_structure']:
                print(f"\nProcessing {analysis_type} analysis for channel {args.channel}...")
                processor = BatchProcessor(analysis_type)
                stats = processor.process_channel(args.channel, limit=args.limit)
                print(f"Completed: {stats['successful']} successful, {stats['failed']} failed")
        else:
            print(f"\nProcessing {args.type} analysis for channel {args.channel}...")
            processor = BatchProcessor(args.type)
            stats = processor.process_channel(args.channel, limit=args.limit)
            print(f"Completed: {stats['successful']} successful, {stats['failed']} failed")
    else:
        # Process all channels
        if args.type == 'all':
            run_all_analysis(limit_per_channel=args.limit)
        else:
            processor = BatchProcessor(args.type)
            processor.process_all_channels(limit=args.limit)

    print("\n" + "=" * 60)
    print("  Analysis Complete!")
    print("=" * 60 + "\n")


if __name__ == '__main__':
    main()
