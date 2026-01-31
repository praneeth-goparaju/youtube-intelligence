"""Shared Firebase utilities for YouTube Intelligence System.

This module provides common Firebase initialization and access patterns
used across all phases.
"""

import threading
from typing import Optional, Dict, Any, List
import firebase_admin
from firebase_admin import credentials, firestore


# Global state for Firebase singleton
_app: Optional[firebase_admin.App] = None
_db: Optional[firestore.Client] = None
_init_lock = threading.Lock()


def get_firebase_credentials(config) -> credentials.Certificate:
    """Create Firebase credentials from config.

    Args:
        config: Configuration object with Firebase attributes

    Returns:
        Firebase Certificate credentials
    """
    return credentials.Certificate({
        'type': 'service_account',
        'project_id': config.FIREBASE_PROJECT_ID,
        'client_email': config.FIREBASE_CLIENT_EMAIL,
        'private_key': config.FIREBASE_PRIVATE_KEY,
        'token_uri': 'https://oauth2.googleapis.com/token',
    })


def initialize_firebase_app(config, options: Optional[Dict[str, Any]] = None) -> firebase_admin.App:
    """Initialize Firebase Admin SDK.

    Thread-safe singleton: uses double-checked locking to ensure only one
    initialization occurs even under concurrent access.

    Args:
        config: Configuration object with Firebase attributes
        options: Additional Firebase initialization options

    Returns:
        Firebase App instance
    """
    global _app, _db

    # Fast path: already initialized
    if _app is not None:
        return _app

    with _init_lock:
        # Double-check after acquiring lock
        if _app is not None:
            return _app

        try:
            cred = get_firebase_credentials(config)
            init_options = options or {}

            if hasattr(config, 'FIREBASE_STORAGE_BUCKET') and config.FIREBASE_STORAGE_BUCKET:
                init_options.setdefault('storageBucket', config.FIREBASE_STORAGE_BUCKET)

            _app = firebase_admin.initialize_app(cred, init_options)
            _db = firestore.client()

        except ValueError:
            # Firebase already initialized in another module
            _app = firebase_admin.get_app()
            _db = firestore.client()
        except Exception as e:
            print(f"Error initializing Firebase: {e}")
            raise RuntimeError(f"Failed to initialize Firebase: {e}")

    return _app


def get_firestore_client() -> firestore.Client:
    """Get Firestore client instance.

    Returns:
        Firestore Client

    Raises:
        RuntimeError: If Firebase not initialized
    """
    if _db is None:
        raise RuntimeError("Firebase not initialized. Call initialize_firebase_app() first.")
    return _db


def fetch_document(collection: str, doc_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single document from Firestore.

    Args:
        collection: Collection name
        doc_id: Document ID

    Returns:
        Document data with 'id' field, or None if not found
    """
    try:
        db = get_firestore_client()
        doc = db.collection(collection).document(doc_id).get()
        if doc.exists:
            return {'id': doc.id, **doc.to_dict()}
        return None
    except Exception as e:
        print(f"Error fetching document {collection}/{doc_id}: {e}")
        return None


def fetch_collection(collection: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Fetch all documents from a collection.

    Args:
        collection: Collection name
        limit: Optional limit on number of documents

    Returns:
        List of document data with 'id' field
    """
    try:
        db = get_firestore_client()
        query = db.collection(collection)
        if limit:
            query = query.limit(limit)
        docs = query.stream()
        return [{'id': doc.id, **doc.to_dict()} for doc in docs]
    except Exception as e:
        print(f"Error fetching collection {collection}: {e}")
        return []


def fetch_subcollection(
    parent_collection: str,
    parent_id: str,
    subcollection: str,
    limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Fetch documents from a subcollection.

    Args:
        parent_collection: Parent collection name
        parent_id: Parent document ID
        subcollection: Subcollection name
        limit: Optional limit on number of documents

    Returns:
        List of document data with 'id' field
    """
    try:
        db = get_firestore_client()
        query = (db.collection(parent_collection)
                 .document(parent_id)
                 .collection(subcollection))
        if limit:
            query = query.limit(limit)
        docs = query.stream()
        return [{'id': doc.id, **doc.to_dict()} for doc in docs]
    except Exception as e:
        print(f"Error fetching subcollection {parent_collection}/{parent_id}/{subcollection}: {e}")
        return []


def save_document(
    collection: str,
    doc_id: str,
    data: Dict[str, Any],
    merge: bool = True
) -> bool:
    """Save a document to Firestore.

    Args:
        collection: Collection name
        doc_id: Document ID
        data: Document data
        merge: Whether to merge with existing data

    Returns:
        True if successful, False otherwise
    """
    try:
        db = get_firestore_client()
        db.collection(collection).document(doc_id).set(data, merge=merge)
        return True
    except Exception as e:
        print(f"Error saving document {collection}/{doc_id}: {e}")
        return False
