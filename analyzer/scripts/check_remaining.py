"""Check remaining unanalyzed videos per channel and category."""

import sys
import json
from pathlib import Path

# Set up paths exactly like src/config.py does
_this_dir = Path(__file__).parent
_analyzer_dir = _this_dir.parent
_project_root = _analyzer_dir.parent
sys.path.insert(0, str(_project_root))
sys.path.insert(0, str(_analyzer_dir))

from src.config import config
from src.firebase_client import initialize_firebase, get_db

CHANNELS_JSON = _project_root / "config" / "channels.json"


def main():
    # Force config load
    config.load()
    initialize_firebase()
    db = get_db()

    # Build handle -> category lookup from channels.json
    with open(CHANNELS_JSON) as f:
        cfg_channels = json.load(f)["channels"]
    handle_to_category = {}
    for ch in cfg_channels:
        url = ch["url"]
        if "/@" in url:
            handle = url.split("/@")[1].rstrip("/").lower()
            handle_to_category[handle] = ch["category"]

    # Get only channels with analyzeEnabled == True (same filter as analyzer)
    from google.cloud.firestore_v1 import FieldFilter

    channels = list(db.collection("channels").where(filter=FieldFilter("analyzeEnabled", "==", True)).stream())
    print(f"Found {len(channels)} analyze-enabled channels in Firestore\n")

    results = []

    for idx, ch_doc in enumerate(channels):
        ch_data = ch_doc.to_dict()
        ch_id = ch_doc.id
        ch_title = ch_data.get("title", ch_id)
        ch_handle = ch_data.get("customUrl", "").lstrip("@").lower()
        category = handle_to_category.get(ch_handle, "unknown")

        # Count total non-Short videos
        videos_ref = db.collection("channels").document(ch_id).collection("videos")
        all_videos = list(videos_ref.stream())

        non_short_ids = [v.id for v in all_videos if not v.to_dict().get("isShort", False)]
        total = len(non_short_ids)

        if total == 0:
            results.append(
                {
                    "channel": ch_title,
                    "category": category,
                    "total": 0,
                    "thumb_done": 0,
                    "thumb_left": 0,
                    "td_done": 0,
                    "td_left": 0,
                }
            )
            print(f"  [{idx + 1}/{len(channels)}] {ch_title}: 0 videos", flush=True)
            continue

        # Check thumbnail analysis
        thumb_done = 0
        thumb_refs = [videos_ref.document(vid).collection("analysis").document("thumbnail") for vid in non_short_ids]
        for i in range(0, len(thumb_refs), 500):
            batch = thumb_refs[i : i + 500]
            for snap in db.get_all(batch, field_paths=[]):
                if snap.exists:
                    thumb_done += 1

        # Check title_description analysis
        td_done = 0
        td_refs = [
            videos_ref.document(vid).collection("analysis").document("title_description") for vid in non_short_ids
        ]
        for i in range(0, len(td_refs), 500):
            batch = td_refs[i : i + 500]
            for snap in db.get_all(batch, field_paths=[]):
                if snap.exists:
                    td_done += 1

        results.append(
            {
                "channel": ch_title,
                "category": category,
                "total": total,
                "thumb_done": thumb_done,
                "thumb_left": total - thumb_done,
                "td_done": td_done,
                "td_left": total - td_done,
            }
        )
        print(
            f"  [{idx + 1}/{len(channels)}] {ch_title}: {total} vids, T:{thumb_done}/{total}, TD:{td_done}/{total}",
            flush=True,
        )

    # Sort by category then channel
    results.sort(key=lambda x: (x["category"], x["channel"]))

    # Print per-channel table
    print("\n" + "=" * 120)
    print(f"{'Channel':<35} {'Category':<20} {'Total':>6} {'Thumb':>6} {'T Left':>7} {'TD':>6} {'TD Left':>8}")
    print("=" * 120)

    current_cat = None
    cat_totals = {}

    for r in results:
        cat = r["category"]
        if cat != current_cat:
            if current_cat is not None:
                print("-" * 120)
            current_cat = cat

        if cat not in cat_totals:
            cat_totals[cat] = {"total": 0, "thumb_done": 0, "thumb_left": 0, "td_done": 0, "td_left": 0}
        for k in cat_totals[cat]:
            cat_totals[cat][k] += r[k]

        print(
            f"{r['channel']:<35} {cat:<20} {r['total']:>6} {r['thumb_done']:>6} {r['thumb_left']:>7} {r['td_done']:>6} {r['td_left']:>8}"
        )

    # Print category summary
    print("\n" + "=" * 100)
    print(f"\n{'CATEGORY SUMMARY':^100}")
    print("=" * 100)
    print(f"{'Category':<25} {'Total':>8} {'Thumb Done':>11} {'Thumb Left':>11} {'TD Done':>9} {'TD Left':>9}")
    print("-" * 100)

    grand = {"total": 0, "thumb_done": 0, "thumb_left": 0, "td_done": 0, "td_left": 0}
    for cat in sorted(cat_totals.keys()):
        t = cat_totals[cat]
        print(
            f"{cat:<25} {t['total']:>8} {t['thumb_done']:>11} {t['thumb_left']:>11} {t['td_done']:>9} {t['td_left']:>9}"
        )
        for k in grand:
            grand[k] += t[k]

    print("-" * 100)
    print(
        f"{'GRAND TOTAL':<25} {grand['total']:>8} {grand['thumb_done']:>11} {grand['thumb_left']:>11} {grand['td_done']:>9} {grand['td_left']:>9}"
    )
    print("=" * 100)


if __name__ == "__main__":
    main()
