"""Firebase client for insights module."""

from typing import Optional, Dict, Any, List
import firebase_admin
from firebase_admin import credentials, firestore

from shared.constants import ANALYSIS_TYPE_THUMBNAIL, ANALYSIS_TYPE_TITLE_DESCRIPTION
from .config import config

# Legacy fallback type for channels analyzed before title_description was introduced
_LEGACY_TITLE_TYPE = "title"


_app: Optional[firebase_admin.App] = None
_db: Optional[firestore.Client] = None


def initialize_firebase() -> None:
    """Initialize Firebase Admin SDK."""
    global _app, _db

    if _app is not None:
        return

    config.initialize()

    try:
        cred = credentials.Certificate(
            {
                "type": "service_account",
                "project_id": config.FIREBASE_PROJECT_ID,
                "client_email": config.FIREBASE_CLIENT_EMAIL,
                "private_key": config.FIREBASE_PRIVATE_KEY,
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        )

        _app = firebase_admin.initialize_app(cred, {"storageBucket": config.FIREBASE_STORAGE_BUCKET})

        _db = firestore.client()
    except ValueError as e:
        # Firebase already initialized in another module
        _app = firebase_admin.get_app()
        _db = firestore.client()
    except Exception as e:
        print(f"Error initializing Firebase: {e}")
        raise RuntimeError(f"Failed to initialize Firebase: {e}")


def get_db() -> firestore.Client:
    """Get Firestore client."""
    if _db is None:
        initialize_firebase()
    return _db


def get_all_channels() -> List[Dict[str, Any]]:
    """Get all channels.

    Returns:
        List of channel documents with 'id' field.

    Raises:
        RuntimeError: If fetching channels fails.
    """
    try:
        db = get_db()
        docs = db.collection("channels").stream()
        return [{"id": doc.id, **doc.to_dict()} for doc in docs]
    except Exception as e:
        raise RuntimeError(f"Failed to fetch channels from Firestore: {e}") from e


def get_channel_videos(channel_id: str) -> List[Dict[str, Any]]:
    """Get all videos for a channel.

    Args:
        channel_id: The channel ID to fetch videos for.

    Returns:
        List of video documents with 'id' field.

    Raises:
        RuntimeError: If fetching videos fails.
    """
    try:
        db = get_db()
        docs = db.collection("channels").document(channel_id).collection("videos").stream()
        return [{"id": doc.id, **doc.to_dict()} for doc in docs]
    except Exception as e:
        raise RuntimeError(f"Failed to fetch videos for channel {channel_id}: {e}") from e


def _batch_get_analyses_for_channel(
    channel_id: str,
    video_ids: List[str],
    analysis_types: List[str],
    batch_size: int = 500,
) -> Dict[str, Dict[str, Any]]:
    """Batch-fetch analysis documents for a channel's videos.

    Args:
        channel_id: The channel ID.
        video_ids: List of video IDs to fetch analyses for.
        analysis_types: List of analysis types to fetch (e.g. ['title_description', 'title', 'thumbnail']).
        batch_size: Max documents per get_all() call (Firestore limit).

    Returns:
        Dict mapping video_id -> {analysis_type: data}.
    """
    db = get_db()
    channel_ref = db.collection("channels").document(channel_id)

    # Build all document references
    refs = []
    for video_id in video_ids:
        video_ref = channel_ref.collection("videos").document(video_id)
        for atype in analysis_types:
            refs.append(video_ref.collection("analysis").document(atype))

    # Fetch in batches
    results: Dict[str, Dict[str, Any]] = {}
    for i in range(0, len(refs), batch_size):
        batch_refs = refs[i : i + batch_size]
        snapshots = db.get_all(batch_refs)

        for snapshot in snapshots:
            if not snapshot.exists:
                continue
            # Path: channels/{channelId}/videos/{videoId}/analysis/{type}
            a_type = snapshot.reference.id
            vid_id = snapshot.reference.parent.parent.id

            if vid_id not in results:
                results[vid_id] = {}
            results[vid_id][a_type] = snapshot.to_dict()

    return results


def get_all_videos_with_analyses(channel_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Load videos with both thumbnail and title analyses.

    Uses batch reads (db.get_all) instead of per-video document fetches
    for dramatically fewer Firestore reads.

    Returns videos that have at least a title analysis (needed for content type).
    Thumbnail analysis is included when available but not required.

    Args:
        channel_id: If provided, only load videos from this channel.

    Returns:
        List of video dicts with channel, video, title_analysis, and
        thumbnail_analysis (may be None).
    """
    if channel_id:
        db = get_db()
        doc = db.collection("channels").document(channel_id).get()
        if not doc.exists:
            print(f"  Channel {channel_id} not found in Firestore")
            return []
        channels = [{"id": doc.id, **doc.to_dict()}]
    else:
        channels = get_all_channels()
    print(f"  Found {len(channels)} channel{'s' if len(channels) != 1 else ''}")

    all_videos = []
    skipped_no_videos = 0
    skipped_no_analysis = 0

    for i, channel in enumerate(channels, 1):
        channel_id = channel["id"]
        channel_name = channel.get("title", channel_id)
        print(f"  [{i}/{len(channels)}] {channel_name}...", end=" ", flush=True)

        videos = get_channel_videos(channel_id)

        if not videos:
            print("no videos")
            skipped_no_videos += 1
            continue

        video_ids = [v["id"] for v in videos]
        video_map = {v["id"]: v for v in videos}

        # Batch fetch all analyses (include legacy 'title' as fallback)
        analyses = _batch_get_analyses_for_channel(
            channel_id, video_ids, [ANALYSIS_TYPE_TITLE_DESCRIPTION, _LEGACY_TITLE_TYPE, ANALYSIS_TYPE_THUMBNAIL]
        )

        channel_count = 0
        for video_id in video_ids:
            video_analyses = analyses.get(video_id, {})

            # Title/description analysis (required — provides content type)
            title_analysis = video_analyses.get(ANALYSIS_TYPE_TITLE_DESCRIPTION)
            if not title_analysis:
                title_analysis = video_analyses.get(_LEGACY_TITLE_TYPE)

            if not title_analysis:
                skipped_no_analysis += 1
                continue  # Skip videos without title analysis

            thumbnail_analysis = video_analyses.get(ANALYSIS_TYPE_THUMBNAIL)

            all_videos.append(
                {
                    "channel_id": channel_id,
                    "video_id": video_id,
                    "channel": channel,
                    "video": video_map[video_id],
                    "title_analysis": title_analysis,
                    "thumbnail_analysis": thumbnail_analysis,
                }
            )
            channel_count += 1

        print(f"{channel_count}/{len(videos)} analyzed")

    if skipped_no_videos:
        print(f"  Skipped {skipped_no_videos} channels with no videos")
    if skipped_no_analysis:
        print(f"  Skipped {skipped_no_analysis} videos with no analysis")

    return all_videos


def save_insights(insight_type: str, data: Dict[str, Any]) -> None:
    """Save insights to Firestore."""
    try:
        db = get_db()
        db.collection("insights").document(insight_type).set(data)
    except Exception as e:
        print(f"Error saving insights for {insight_type}: {e}")
        raise
