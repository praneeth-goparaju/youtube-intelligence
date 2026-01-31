"""Shared constants and utilities for YouTube Intelligence System.

Constants are always available. Utilities (config, gemini_utils, firebase_utils)
should be imported directly from their submodules to avoid dependency issues:

    from shared.constants import GEMINI_MODEL
    from shared.config import get_env, load_env_file
    from shared.gemini_utils import parse_json_response
    from shared.firebase_utils import initialize_firebase_app
"""

from .constants import (
    # Collection names
    COLLECTION_CHANNELS,
    COLLECTION_VIDEOS,
    COLLECTION_ANALYSIS,
    COLLECTION_INSIGHTS,
    COLLECTION_SCRAPE_PROGRESS,
    COLLECTION_ANALYSIS_PROGRESS,
    # Analysis types
    ANALYSIS_TYPE_THUMBNAIL,
    ANALYSIS_TYPE_TITLE_DESCRIPTION,
    ANALYSIS_TYPE_TITLE,
    ANALYSIS_TYPE_DESCRIPTION,
    ANALYSIS_TYPE_TAGS,
    ANALYSIS_TYPE_CONTENT_STRUCTURE,
    ANALYSIS_TYPES,
    # Insight types
    INSIGHT_TYPE_THUMBNAILS,
    INSIGHT_TYPE_TITLES,
    INSIGHT_TYPE_TIMING,
    INSIGHT_TYPE_CONTENT_GAPS,
    INSIGHT_TYPES,
    # Model
    GEMINI_MODEL,
    # Timestamp
    TIMESTAMP_FORMAT,
    # Video fields
    VIDEO_REQUIRED_FIELDS,
    VIDEO_CALCULATED_FIELDS,
)

__all__ = [
    # Constants
    'COLLECTION_CHANNELS',
    'COLLECTION_VIDEOS',
    'COLLECTION_ANALYSIS',
    'COLLECTION_INSIGHTS',
    'COLLECTION_SCRAPE_PROGRESS',
    'COLLECTION_ANALYSIS_PROGRESS',
    'ANALYSIS_TYPE_THUMBNAIL',
    'ANALYSIS_TYPE_TITLE_DESCRIPTION',
    'ANALYSIS_TYPE_TITLE',
    'ANALYSIS_TYPE_DESCRIPTION',
    'ANALYSIS_TYPE_TAGS',
    'ANALYSIS_TYPE_CONTENT_STRUCTURE',
    'ANALYSIS_TYPES',
    'INSIGHT_TYPE_THUMBNAILS',
    'INSIGHT_TYPE_TITLES',
    'INSIGHT_TYPE_TIMING',
    'INSIGHT_TYPE_CONTENT_GAPS',
    'INSIGHT_TYPES',
    'GEMINI_MODEL',
    'TIMESTAMP_FORMAT',
    'VIDEO_REQUIRED_FIELDS',
    'VIDEO_CALCULATED_FIELDS',
]
