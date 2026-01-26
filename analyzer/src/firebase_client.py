"""Firebase client for accessing Firestore and Storage."""

from typing import Optional, Dict, Any, List
import firebase_admin
from firebase_admin import credentials, firestore, storage
from google.cloud.firestore_v1 import FieldFilter

from .config import config


_app: Optional[firebase_admin.App] = None
_db: Optional[firestore.Client] = None
_bucket = None


def initialize_firebase() -> None:
    """Initialize Firebase Admin SDK."""
    global _app, _db, _bucket

    if _app is not None:
        return

    cred = credentials.Certificate({
        'type': 'service_account',
        'project_id': config.FIREBASE_PROJECT_ID,
        'client_email': config.FIREBASE_CLIENT_EMAIL,
        'private_key': config.FIREBASE_PRIVATE_KEY,
        'token_uri': 'https://oauth2.googleapis.com/token',
    })

    _app = firebase_admin.initialize_app(cred, {
        'storageBucket': config.FIREBASE_STORAGE_BUCKET
    })

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
    """Get all channels from Firestore."""
    db = get_db()
    docs = db.collection('channels').stream()
    return [{'id': doc.id, **doc.to_dict()} for doc in docs]


def get_channel(channel_id: str) -> Optional[Dict[str, Any]]:
    """Get a single channel by ID."""
    db = get_db()
    doc = db.collection('channels').document(channel_id).get()
    if doc.exists:
        return {'id': doc.id, **doc.to_dict()}
    return None


# ===== Video Operations =====

def get_channel_videos(channel_id: str) -> List[Dict[str, Any]]:
    """Get all videos for a channel."""
    db = get_db()
    docs = db.collection('channels').document(channel_id).collection('videos').stream()
    return [{'id': doc.id, **doc.to_dict()} for doc in docs]


def get_video(channel_id: str, video_id: str) -> Optional[Dict[str, Any]]:
    """Get a single video by ID."""
    db = get_db()
    doc = (db.collection('channels')
           .document(channel_id)
           .collection('videos')
           .document(video_id)
           .get())
    if doc.exists:
        return {'id': doc.id, **doc.to_dict()}
    return None


def get_unanalyzed_videos(channel_id: str, analysis_type: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Get videos that haven't been analyzed yet for a specific analysis type."""
    db = get_db()

    # Get all videos
    videos_ref = db.collection('channels').document(channel_id).collection('videos')
    all_videos = list(videos_ref.limit(limit * 2).stream())  # Get more to account for already analyzed

    unanalyzed = []
    for video_doc in all_videos:
        if len(unanalyzed) >= limit:
            break

        video_id = video_doc.id
        # Check if analysis exists
        analysis_doc = (videos_ref.document(video_id)
                       .collection('analysis')
                       .document(analysis_type)
                       .get())

        if not analysis_doc.exists:
            unanalyzed.append({'id': video_id, **video_doc.to_dict()})

    return unanalyzed


# ===== Analysis Operations =====

def save_analysis(channel_id: str, video_id: str, analysis_type: str, data: Dict[str, Any]) -> None:
    """Save analysis results for a video."""
    db = get_db()
    (db.collection('channels')
     .document(channel_id)
     .collection('videos')
     .document(video_id)
     .collection('analysis')
     .document(analysis_type)
     .set(data, merge=True))


def get_analysis(channel_id: str, video_id: str, analysis_type: str) -> Optional[Dict[str, Any]]:
    """Get analysis results for a video."""
    db = get_db()
    doc = (db.collection('channels')
           .document(channel_id)
           .collection('videos')
           .document(video_id)
           .collection('analysis')
           .document(analysis_type)
           .get())
    if doc.exists:
        return doc.to_dict()
    return None


def has_analysis(channel_id: str, video_id: str, analysis_type: str) -> bool:
    """Check if analysis exists for a video."""
    db = get_db()
    doc = (db.collection('channels')
           .document(channel_id)
           .collection('videos')
           .document(video_id)
           .collection('analysis')
           .document(analysis_type)
           .get())
    return doc.exists


# ===== Storage Operations =====

def get_thumbnail_url(storage_path: str) -> str:
    """Get signed URL for a thumbnail in storage."""
    bucket = get_bucket()
    blob = bucket.blob(storage_path)

    # Generate signed URL valid for 1 hour
    url = blob.generate_signed_url(expiration=3600)
    return url


def download_thumbnail(storage_path: str) -> bytes:
    """Download thumbnail from storage as bytes."""
    bucket = get_bucket()
    blob = bucket.blob(storage_path)
    return blob.download_as_bytes()


# ===== Progress Tracking =====

def save_analysis_progress(analysis_type: str, data: Dict[str, Any]) -> None:
    """Save analysis progress."""
    db = get_db()
    db.collection('analysis_progress').document(analysis_type).set(data, merge=True)


def get_analysis_progress(analysis_type: str) -> Optional[Dict[str, Any]]:
    """Get analysis progress."""
    db = get_db()
    doc = db.collection('analysis_progress').document(analysis_type).get()
    if doc.exists:
        return doc.to_dict()
    return None
