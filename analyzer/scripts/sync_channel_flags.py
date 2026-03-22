#!/usr/bin/env python3
"""Sync channel analyzeEnabled flags and categories from CSV to Firebase.

Reads a CSV file with channel URLs, yes/no analyze flags, and categories.
Matches each row to a Firebase channel document by handle (customUrl) and
updates `analyzeEnabled` (bool) and `category` (string) fields.

Usage:
    cd analyzer
    python3 -m scripts.sync_channel_flags --csv ../data/channels-review.csv
"""

import argparse
import csv
import re
import sys
from pathlib import Path

# Add parent to path so we can import src
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import validate_config, Config
from src.firebase_client import initialize_firebase, get_db


def extract_handle(url: str) -> str:
    """Extract the @handle from a YouTube channel URL.

    Supports:
        https://www.youtube.com/@handle
        https://youtube.com/@handle
    """
    match = re.search(r"/@([^/?]+)", url)
    return match.group(1).lower() if match else ""


def load_csv(csv_path: str) -> list:
    """Load and parse the CSV file.

    Expected columns: Analyze, Channel Name, Link, Channel, Subscribers, Videos, Category
    Handles case-insensitive header matching.
    """
    rows = []
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        # Normalize headers to lowercase for case-insensitive matching
        if reader.fieldnames:
            header_map = {h: h for h in reader.fieldnames}
            lower_map = {h.lower(): h for h in reader.fieldnames}
        else:
            lower_map = {}

        for row in reader:
            # Case-insensitive column access
            def col(name):
                key = lower_map.get(name.lower(), name)
                return (row.get(key, "") or "").strip()

            analyze_val = col("analyze").lower()
            link = col("link")
            category = col("category")
            channel_name = col("channel name") or col("channel")

            handle = extract_handle(link)

            if not link and not handle:
                continue

            rows.append(
                {
                    "handle": handle,
                    "link": link,
                    "analyze_enabled": analyze_val in ("yes", "true"),
                    "category": category,
                    "channel_name": channel_name,
                }
            )
    return rows


def sync_flags(csv_path: str, dry_run: bool = False):
    """Sync analyzeEnabled and category from CSV to Firebase channels."""
    # Load CSV
    csv_rows = load_csv(csv_path)
    print(f"Loaded {len(csv_rows)} rows from CSV")

    # Build handle -> csv_row lookup
    csv_by_handle = {}
    for row in csv_rows:
        if row["handle"]:
            csv_by_handle[row["handle"]] = row

    # Fetch all channels from Firebase
    db = get_db()
    channel_docs = list(db.collection("channels").stream())
    print(f"Found {len(channel_docs)} channels in Firebase\n")

    matched = 0
    unmatched_csv = set(csv_by_handle.keys())
    unmatched_firebase = []
    updated = 0
    skipped = 0

    for doc in channel_docs:
        data = doc.to_dict()
        channel_id = doc.id

        # Try to match by customUrl (stored as @handle or handle)
        custom_url = (data.get("customUrl", "") or "").lstrip("@").lower()

        csv_row = csv_by_handle.get(custom_url)
        if csv_row:
            unmatched_csv.discard(custom_url)
            matched += 1

            # Build update
            updates = {}
            new_enabled = csv_row["analyze_enabled"]
            new_category = csv_row["category"]

            if data.get("analyzeEnabled") != new_enabled:
                updates["analyzeEnabled"] = new_enabled
            if new_category and data.get("category") != new_category:
                updates["category"] = new_category

            if updates:
                title = data.get("title", data.get("channelTitle", channel_id))
                flag_str = "ON" if new_enabled else "OFF"
                cat_str = f", category={new_category}" if "category" in updates else ""
                print(f"  {'[DRY] ' if dry_run else ''}Update {title[:40]:<40}  analyze={flag_str}{cat_str}")

                if not dry_run:
                    db.collection("channels").document(channel_id).update(updates)
                updated += 1
            else:
                skipped += 1
        else:
            title = data.get("title", data.get("channelTitle", channel_id))
            unmatched_firebase.append(title)

    # Summary
    print(f"\n{'=' * 50}")
    print(f"  Matched:     {matched}/{len(csv_rows)} CSV rows")
    print(f"  Updated:     {updated}")
    print(f"  No changes:  {skipped}")

    if unmatched_csv:
        print(f"\n  CSV rows with no Firebase match ({len(unmatched_csv)}):")
        for handle in sorted(unmatched_csv):
            row = csv_by_handle[handle]
            print(f"    @{handle} ({row['channel_name']})")

    if unmatched_firebase:
        print(f"\n  Firebase channels with no CSV match ({len(unmatched_firebase)}):")
        for title in sorted(unmatched_firebase):
            print(f"    {title}")

    if dry_run:
        print("\n  DRY RUN — no changes written to Firebase")


def main():
    parser = argparse.ArgumentParser(description="Sync channel analyze flags and categories from CSV to Firebase")
    parser.add_argument("--csv", required=True, help="Path to the CSV file with channel flags")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be updated without writing to Firebase")
    args = parser.parse_args()

    # Validate and initialize
    print("\n" + "=" * 50)
    print("  Sync Channel Flags from CSV")
    print("=" * 50 + "\n")

    if not validate_config():
        sys.exit(1)
    Config.load()

    initialize_firebase()
    print("Firebase connected\n")

    sync_flags(args.csv, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
