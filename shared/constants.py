"""Shared constants for YouTube Intelligence System.

This module provides centralized constants used across all phases
to ensure consistency in collection names, analysis types, and configurations.
"""

# =============================================================================
# Firestore Collection Names
# =============================================================================

COLLECTION_CHANNELS = 'channels'
COLLECTION_VIDEOS = 'videos'
COLLECTION_ANALYSIS = 'analysis'
COLLECTION_INSIGHTS = 'insights'
COLLECTION_SCRAPE_PROGRESS = 'scrape_progress'
COLLECTION_ANALYSIS_PROGRESS = 'analysis_progress'

# =============================================================================
# Analysis Types (Phase 2 output)
# =============================================================================

ANALYSIS_TYPE_THUMBNAIL = 'thumbnail'
ANALYSIS_TYPE_TITLE_DESCRIPTION = 'title_description'

# Legacy analysis types (no longer generated, but may exist in Firestore)
ANALYSIS_TYPE_TITLE = 'title'
ANALYSIS_TYPE_DESCRIPTION = 'description'
ANALYSIS_TYPE_TAGS = 'tags'
ANALYSIS_TYPE_CONTENT_STRUCTURE = 'content_structure'

# Active analysis types used by the pipeline
ANALYSIS_TYPES = [
    ANALYSIS_TYPE_THUMBNAIL,
    ANALYSIS_TYPE_TITLE_DESCRIPTION,
]

# =============================================================================
# Insight Types (Phase 3 output)
# =============================================================================

INSIGHT_TYPE_THUMBNAILS = 'thumbnails'
INSIGHT_TYPE_TITLES = 'titles'
INSIGHT_TYPE_TIMING = 'timing'
INSIGHT_TYPE_CONTENT_GAPS = 'contentGaps'

INSIGHT_TYPES = [
    INSIGHT_TYPE_THUMBNAILS,
    INSIGHT_TYPE_TITLES,
    INSIGHT_TYPE_TIMING,
    INSIGHT_TYPE_CONTENT_GAPS,
]

# =============================================================================
# AI Model Configuration
# =============================================================================

GEMINI_MODEL = 'gemini-2.0-flash'

# =============================================================================
# Timestamp Configuration
# =============================================================================

TIMESTAMP_FORMAT = '%Y%m%d_%H%M%S'

# =============================================================================
# Video Data Structure Required Fields
# These are the expected fields for video data across phases
# =============================================================================

VIDEO_REQUIRED_FIELDS = [
    'videoId',
    'channelId',
    'title',
    'viewCount',
]

VIDEO_CALCULATED_FIELDS = [
    'engagementRate',
    'viewsPerDay',
    'viewsPerSubscriber',
    'publishDayOfWeek',
    'publishHourIST',
]
