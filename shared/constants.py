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
COLLECTION_BATCH_JOBS = 'batch_jobs'

# =============================================================================
# Analysis Types (Phase 2 output)
# =============================================================================

ANALYSIS_TYPE_THUMBNAIL = 'thumbnail'
ANALYSIS_TYPE_TITLE_DESCRIPTION = 'title_description'

ANALYSIS_TYPES = [
    ANALYSIS_TYPE_THUMBNAIL,
    ANALYSIS_TYPE_TITLE_DESCRIPTION,
]

# =============================================================================
# Insight Types (Phase 3 output)
# Per-content-type profiles are stored as insights/{contentType}
# =============================================================================

INSIGHT_TYPE_CONTENT_GAPS = 'contentGaps'
INSIGHT_TYPE_SUMMARY = 'summary'

# =============================================================================
# AI Model Configuration
# =============================================================================

GEMINI_MODEL = 'gemini-2.5-flash'

# Batch API Analysis Version (tracks schema changes for batch mode)
BATCH_ANALYSIS_VERSION = '2.0'

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
