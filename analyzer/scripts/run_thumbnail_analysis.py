#!/usr/bin/env python3
"""Run thumbnail analysis on all videos."""

import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import validate_config, Config
from src.firebase_client import initialize_firebase
from src.gemini_client import test_connection
from src.processors.batch import BatchProcessor


def main():
    parser = argparse.ArgumentParser(description='Run thumbnail analysis')
    parser.add_argument('--limit', '-l', type=int, help='Limit videos per channel')
    parser.add_argument('--channel', '-c', type=str, help='Process single channel')
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("  Thumbnail Analysis")
    print("=" * 60 + "\n")

    if not validate_config():
        sys.exit(1)
    Config.load()

    initialize_firebase()
    print("Firebase connected")

    if not test_connection():
        print("Gemini API connection failed")
        sys.exit(1)
    print("Gemini API connected\n")

    processor = BatchProcessor('thumbnail')

    if args.channel:
        stats = processor.process_channel(args.channel, limit=args.limit)
    else:
        stats = processor.process_all_channels(limit=args.limit)

    print(f"\nCompleted: {stats['successful']} success, {stats['failed']} failed, {stats['skipped']} skipped")


if __name__ == '__main__':
    main()
