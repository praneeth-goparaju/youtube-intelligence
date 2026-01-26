"""Firebase client for insights module."""

from typing import Optional, Dict, Any, List
import firebase_admin
from firebase_admin import credentials, firestore

from .config import config


_app: Optional[firebase_admin.App] = None
_db: Optional[firestore.Client] = None


def initialize_firebase() -> None:
    """Initialize Firebase Admin SDK."""
    global _app, _db

    if _app is not None:
        return

    try:
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
        docs = db.collection('channels').stream()
        return [{'id': doc.id, **doc.to_dict()} for doc in docs]
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
        docs = db.collection('channels').document(channel_id).collection('videos').stream()
        return [{'id': doc.id, **doc.to_dict()} for doc in docs]
    except Exception as e:
        raise RuntimeError(f"Failed to fetch videos for channel {channel_id}: {e}") from e


def get_video_analysis(channel_id: str, video_id: str, analysis_type: str) -> Optional[Dict[str, Any]]:
    """Get analysis for a video.

    Args:
        channel_id: The channel ID.
        video_id: The video ID.
        analysis_type: The type of analysis (thumbnail, title, etc.).

    Returns:
        Analysis document data or None if not found.

    Note:
        Returns None if analysis doesn't exist (not an error).
        Raises RuntimeError for actual Firestore errors.
    """
    try:
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
    except Exception as e:
        # Log but don't fail - analysis may not exist yet
        print(f"Warning: Error fetching analysis for video {video_id}: {e}")
        return None


def get_all_videos_with_analysis(analysis_type: str) -> List[Dict[str, Any]]:
    """Get all videos with a specific analysis type."""
    db = get_db()
    channels = get_all_channels()

    all_videos = []
    for channel in channels:
        channel_id = channel['id']
        videos = get_channel_videos(channel_id)

        for video in videos:
            video_id = video['id']
            analysis = get_video_analysis(channel_id, video_id, analysis_type)

            if analysis:
                all_videos.append({
                    'channel_id': channel_id,
                    'video_id': video_id,
                    'channel': channel,
                    'video': video,
                    'analysis': analysis,
                })

    return all_videos


def save_insights(insight_type: str, data: Dict[str, Any]) -> None:
    """Save insights to Firestore."""
    try:
        db = get_db()
        db.collection('insights').document(insight_type).set(data, merge=True)
    except Exception as e:
        print(f"Error saving insights for {insight_type}: {e}")
        raise


def get_insights(insight_type: str) -> Optional[Dict[str, Any]]:
    """Get insights from Firestore.

    Args:
        insight_type: The type of insights to fetch.

    Returns:
        Insights document data or None if not found.

    Raises:
        RuntimeError: If fetching insights fails due to Firestore error.
    """
    try:
        db = get_db()
        doc = db.collection('insights').document(insight_type).get()
        if doc.exists:
            return doc.to_dict()
        return None
    except Exception as e:
        raise RuntimeError(f"Failed to fetch insights for {insight_type}: {e}") from e
