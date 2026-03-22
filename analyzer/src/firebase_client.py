"""Firebase client for accessing Firestore and Storage."""

from typing import Optional, Dict, Any, List
import firebase_admin
from firebase_admin import credentials, firestore, storage
from google.cloud.firestore_v1 import FieldFilter

from .config import config

# shared module path is set up by config.py (imported above)
from shared.constants import COLLECTION_BATCH_JOBS


_app: Optional[firebase_admin.App] = None
_db: Optional[firestore.Client] = None
_bucket = None


def initialize_firebase() -> None:
    """Initialize Firebase Admin SDK."""
    global _app, _db, _bucket

    if _app is not None:
        return

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
    _bucket = storage.bucket()


def get_db() -> firestore.Client:
    """Get Firestore client."""
    if _db is None:
        initialize_firebase()
    return _db


def get_bucket():
    """Get Storage bucket."""
    if _bucket is None:
        initialize_firebase()
    return _bucket


# ===== Channel Operations =====


def get_all_channels() -> List[Dict[str, Any]]:
    """Get channels with analyzeEnabled == True from Firestore.

    Channels without the analyzeEnabled field are excluded.
    Use get_all_channels_unfiltered() for status displays.
    """
    db = get_db()
    query = db.collection("channels").where(filter=FieldFilter("analyzeEnabled", "==", True))
    return [{"id": doc.id, **doc.to_dict()} for doc in query.stream()]


def get_all_channels_unfiltered() -> List[Dict[str, Any]]:
    """Get all channels from Firestore (no analyzeEnabled filter)."""
    db = get_db()
    docs = db.collection("channels").stream()
    return [{"id": doc.id, **doc.to_dict()} for doc in docs]


def get_channel(channel_id: str) -> Optional[Dict[str, Any]]:
    """Get a single channel by ID."""
    db = get_db()
    doc = db.collection("channels").document(channel_id).get()
    if doc.exists:
        return {"id": doc.id, **doc.to_dict()}
    return None


# ===== Video Operations =====


def get_unanalyzed_videos(channel_id: str, analysis_type: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Get videos that haven't been analyzed yet for a specific analysis type.

    Note: For large channels, prefer get_unanalyzed_videos_paginated() which
    uses Firestore cursors to avoid loading all videos into memory.
    """
    return get_unanalyzed_videos_paginated(channel_id, analysis_type, limit)


def get_unanalyzed_videos_paginated(
    channel_id: str,
    analysis_type: str,
    limit: int = 100,
    page_size: int = 1000,
) -> List[Dict[str, Any]]:
    """Get unanalyzed videos using paginated Firestore queries.

    Fetches videos in pages and uses batch get (db.get_all) to check
    analysis status for each page, avoiding per-video round-trips.

    Args:
        channel_id: The channel ID to fetch videos for.
        analysis_type: The analysis type to check (thumbnail, title_description).
        limit: Maximum number of unanalyzed videos to return.
        page_size: Number of videos to fetch per Firestore query page.

    Returns:
        List of unanalyzed video dicts with 'id' field.
    """
    db = get_db()
    videos_ref = db.collection("channels").document(channel_id).collection("videos")

    unanalyzed = []
    last_doc = None

    while len(unanalyzed) < limit:
        # Build paginated query
        query = videos_ref.order_by("__name__").limit(page_size)
        if last_doc is not None:
            query = query.start_after(last_doc)

        docs = list(query.stream())
        if not docs:
            break  # No more videos

        last_doc = docs[-1]

        # Filter out Shorts and build lookup
        candidates = {}
        for video_doc in docs:
            video_data = video_doc.to_dict()
            if not video_data.get("isShort", False):
                candidates[video_doc.id] = video_data

        # Batch check analysis status for all candidates in this page
        if candidates:
            refs = [videos_ref.document(vid).collection("analysis").document(analysis_type) for vid in candidates]
            analyzed_ids = set()
            for doc_snapshot in db.get_all(refs, field_paths=[]):
                if doc_snapshot.exists:
                    analyzed_ids.add(doc_snapshot.reference.parent.parent.id)

            for vid, video_data in candidates.items():
                if len(unanalyzed) >= limit:
                    break
                if vid not in analyzed_ids:
                    unanalyzed.append({"id": vid, **video_data})

        # If we got fewer docs than page_size, we've reached the end
        if len(docs) < page_size:
            break

    return unanalyzed


def get_video(channel_id: str, video_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single video document."""
    db = get_db()
    doc = db.collection("channels").document(channel_id).collection("videos").document(video_id).get()
    if doc.exists:
        return doc.to_dict()
    return None


# ===== Analysis Operations =====


def save_analysis(channel_id: str, video_id: str, analysis_type: str, data: Dict[str, Any]) -> None:
    """Save analysis results for a video."""
    db = get_db()
    (
        db.collection("channels")
        .document(channel_id)
        .collection("videos")
        .document(video_id)
        .collection("analysis")
        .document(analysis_type)
        .set(data, merge=True)
    )


def has_analysis(channel_id: str, video_id: str, analysis_type: str) -> bool:
    """Check if analysis exists for a video."""
    db = get_db()
    doc = (
        db.collection("channels")
        .document(channel_id)
        .collection("videos")
        .document(video_id)
        .collection("analysis")
        .document(analysis_type)
        .get()
    )
    return doc.exists


# ===== Storage Operations =====


def download_thumbnail(storage_path: str) -> bytes:
    """Download thumbnail from storage as bytes."""
    bucket = get_bucket()
    blob = bucket.blob(storage_path)
    return blob.download_as_bytes()


# ===== Progress Tracking =====


def save_analysis_progress(analysis_type: str, data: Dict[str, Any]) -> None:
    """Save analysis progress."""
    db = get_db()
    db.collection("analysis_progress").document(analysis_type).set(data, merge=True)


def get_analysis_progress(analysis_type: str) -> Optional[Dict[str, Any]]:
    """Get analysis progress."""
    db = get_db()
    doc = db.collection("analysis_progress").document(analysis_type).get()
    if doc.exists:
        return doc.to_dict()
    return None


# ===== Batch Job Operations =====


def save_batch_job(job_id: str, data: Dict[str, Any]) -> None:
    """Save or update a batch job record."""
    db = get_db()
    db.collection(COLLECTION_BATCH_JOBS).document(job_id).set(data, merge=True)


def get_batch_job(job_id: str) -> Optional[Dict[str, Any]]:
    """Get a batch job record by ID."""
    db = get_db()
    doc = db.collection(COLLECTION_BATCH_JOBS).document(job_id).get()
    if doc.exists:
        return {"id": doc.id, **doc.to_dict()}
    return None


def get_batch_jobs_by_state(state: str, analysis_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get batch jobs filtered by state and optionally analysis type."""
    db = get_db()
    query = db.collection(COLLECTION_BATCH_JOBS).where(filter=FieldFilter("state", "==", state))
    if analysis_type:
        query = query.where(filter=FieldFilter("analysisType", "==", analysis_type))
    query = query.order_by("createdAt", direction=firestore.Query.DESCENDING)
    docs = query.stream()
    return [{"id": doc.id, **doc.to_dict()} for doc in docs]


def get_latest_batch_job(analysis_type: str, state: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Get the most recent batch job for an analysis type."""
    db = get_db()
    query = db.collection(COLLECTION_BATCH_JOBS).where(filter=FieldFilter("analysisType", "==", analysis_type))
    if state:
        query = query.where(filter=FieldFilter("state", "==", state))
    query = query.order_by("createdAt", direction=firestore.Query.DESCENDING).limit(1)
    docs = list(query.stream())
    if docs:
        return {"id": docs[0].id, **docs[0].to_dict()}
    return None


def list_all_batch_jobs(limit: int = 20) -> List[Dict[str, Any]]:
    """List recent batch jobs."""
    db = get_db()
    query = (
        db.collection(COLLECTION_BATCH_JOBS).order_by("createdAt", direction=firestore.Query.DESCENDING).limit(limit)
    )
    docs = query.stream()
    return [{"id": doc.id, **doc.to_dict()} for doc in docs]


def update_batch_job(job_id: str, updates: Dict[str, Any]) -> None:
    """Update specific fields on a batch job record."""
    db = get_db()
    db.collection(COLLECTION_BATCH_JOBS).document(job_id).update(updates)


def get_all_channel_videos_for_batch(channel_id: str) -> List[Dict[str, Any]]:
    """Get all videos for a channel (used during batch prepare to check analysis status).

    Returns minimal video data needed for batch preparation.
    Excludes Shorts (isShort=true).
    """
    db = get_db()
    docs = db.collection("channels").document(channel_id).collection("videos").stream()
    videos = []
    for doc in docs:
        data = doc.to_dict()
        if not data.get("isShort", False):
            videos.append({"id": doc.id, **data})
    return videos


def get_analyzed_video_ids(channel_id: str, analysis_type: str, video_ids: List[str]) -> set:
    """Get the set of video IDs that already have a given analysis type.

    Uses Firestore batch get (db.get_all) to check all videos in a single
    RPC call instead of one .get() per video.

    Args:
        channel_id: The channel to check.
        analysis_type: The analysis type (thumbnail, title_description).
        video_ids: List of video IDs to check.

    Returns:
        Set of video IDs that already have the analysis.
    """
    if not video_ids:
        return set()

    db = get_db()
    videos_ref = db.collection("channels").document(channel_id).collection("videos")

    # Build refs for all analysis docs we want to check
    refs = [videos_ref.document(vid).collection("analysis").document(analysis_type) for vid in video_ids]

    # get_all fetches all refs in batched RPCs (internally batches by ~100)
    analyzed = set()
    for doc_snapshot in db.get_all(refs, field_paths=[]):
        if doc_snapshot.exists:
            # Path: channels/{ch}/videos/{vid}/analysis/{type} — video ID is 4th segment from end
            analyzed.add(doc_snapshot.reference.parent.parent.id)

    return analyzed
