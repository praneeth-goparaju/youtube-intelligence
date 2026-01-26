"""Firebase client for recommender module."""

import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
import firebase_admin
from firebase_admin import credentials, firestore

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.constants import INSIGHT_TYPES

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


def get_insights(insight_type: str) -> Optional[Dict[str, Any]]:
    """Get insights from Firestore."""
    db = get_db()
    doc = db.collection('insights').document(insight_type).get()
    if doc.exists:
        return doc.to_dict()
    return None


def get_all_insights() -> Dict[str, Dict[str, Any]]:
    """Get all insights from Firestore."""
    insights = {}

    for insight_type in INSIGHT_TYPES:
        data = get_insights(insight_type)
        if data:
            insights[insight_type] = data

    return insights


def get_example_videos(limit: int = 10) -> List[Dict[str, Any]]:
    """Get example high-performing videos.

    Args:
        limit: Maximum number of videos to return

    Returns:
        List of top-performing video examples
    """
    db = get_db()

    try:
        # Get channels
        channels = list(db.collection('channels').limit(20).stream())

        videos = []
        for channel_doc in channels:
            channel_id = channel_doc.id

            # Get top videos by view count
            video_docs = (db.collection('channels')
                         .document(channel_id)
                         .collection('videos')
                         .order_by('viewCount', direction=firestore.Query.DESCENDING)
                         .limit(5)
                         .stream())

            for video_doc in video_docs:
                video = video_doc.to_dict()
                videos.append({
                    'video_id': video_doc.id,
                    'channel_id': channel_id,
                    'title': video.get('title', ''),
                    'viewCount': video.get('viewCount', 0),
                    'thumbnailUrl': video.get('thumbnails', {}).get('medium', ''),
                })

        # Sort by views and return top
        videos.sort(key=lambda x: x['viewCount'], reverse=True)
        return videos[:limit]

    except Exception as e:
        print(f"Error fetching example videos: {e}")
        return []
