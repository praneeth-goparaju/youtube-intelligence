"""Shared constants and utilities for YouTube Intelligence System.

Constants are always available. Utilities (config, gemini_utils, firebase_utils)
should be imported directly from their submodules to avoid dependency issues:

    from shared.constants import GEMINI_MODEL
    from shared.config import get_env, load_env_file
    from shared.gemini_utils import parse_json_response
    from shared.firebase_utils import initialize_firebase_app
"""

from .constants import (
    # Analysis types
    ANALYSIS_TYPE_THUMBNAIL,
    ANALYSIS_TYPE_TITLE_DESCRIPTION,
    ANALYSIS_TYPES,
    COLLECTION_ANALYSIS,
    COLLECTION_ANALYSIS_PROGRESS,
    # Collection names
    COLLECTION_CHANNELS,
    COLLECTION_INSIGHTS,
    COLLECTION_SCRAPE_PROGRESS,
    COLLECTION_VIDEOS,
    # Model
    GEMINI_MODEL,
    # Insight types
    INSIGHT_TYPE_CONTENT_GAPS,
    INSIGHT_TYPE_SUMMARY,
    # Timestamp
    TIMESTAMP_FORMAT,
    VIDEO_CALCULATED_FIELDS,
    # Video fields
    VIDEO_REQUIRED_FIELDS,
)

__all__ = [
    # Constants
    "COLLECTION_CHANNELS",
    "COLLECTION_VIDEOS",
    "COLLECTION_ANALYSIS",
    "COLLECTION_INSIGHTS",
    "COLLECTION_SCRAPE_PROGRESS",
    "COLLECTION_ANALYSIS_PROGRESS",
    "ANALYSIS_TYPE_THUMBNAIL",
    "ANALYSIS_TYPE_TITLE_DESCRIPTION",
    "ANALYSIS_TYPES",
    "INSIGHT_TYPE_CONTENT_GAPS",
    "INSIGHT_TYPE_SUMMARY",
    "GEMINI_MODEL",
    "TIMESTAMP_FORMAT",
    "VIDEO_REQUIRED_FIELDS",
    "VIDEO_CALCULATED_FIELDS",
]
