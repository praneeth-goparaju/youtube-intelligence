"""Thumbnail analysis using Gemini Vision."""

from typing import Dict, Any, Optional
from datetime import datetime

import requests

from ..gemini_client import analyze_image
from ..firebase_client import download_thumbnail, save_analysis, has_analysis
from ..prompts import THUMBNAIL_ANALYSIS_PROMPT
from shared.constants import BATCH_ANALYSIS_VERSION
from ..config import config, logger


class ThumbnailAnalyzer:
    """Analyzer for YouTube video thumbnails."""

    ANALYSIS_TYPE = 'thumbnail'

    def analyze(self, channel_id: str, video_id: str,
                thumbnail_path: str, force: bool = False) -> Optional[Dict[str, Any]]:
        """
        Analyze a video thumbnail.

        Args:
            channel_id: The channel ID
            video_id: The video ID
            thumbnail_path: Path to thumbnail in Firebase Storage
            force: Force re-analysis even if already exists

        Returns:
            Analysis results or None if failed
        """
        # Check if already analyzed
        if not force and has_analysis(channel_id, video_id, self.ANALYSIS_TYPE):
            return None

        if not thumbnail_path:
            return None

        try:
            # Download thumbnail from storage
            image_data = download_thumbnail(thumbnail_path)

            # Analyze with Gemini Vision (uses response_schema when available)
            result = analyze_image(
                THUMBNAIL_ANALYSIS_PROMPT, image_data,
                analysis_type=self.ANALYSIS_TYPE,
            )

            if not result:
                logger.warning(f"Empty result from Gemini for thumbnail {video_id}")
                return None

            # Add metadata
            result['analyzedAt'] = datetime.utcnow().isoformat()
            result['modelUsed'] = config.GEMINI_MODEL
            result['analysisVersion'] = BATCH_ANALYSIS_VERSION

            # Save to Firestore
            save_analysis(channel_id, video_id, self.ANALYSIS_TYPE, result)

            return result

        except Exception as e:
            logger.error(f"Error analyzing thumbnail {video_id}: {e}")
            return None

    def analyze_from_url(self, channel_id: str, video_id: str,
                        thumbnail_url: str, force: bool = False) -> Optional[Dict[str, Any]]:
        """
        Analyze a thumbnail from URL (for testing without storage).

        Args:
            channel_id: The channel ID
            video_id: The video ID
            thumbnail_url: URL to the thumbnail image
            force: Force re-analysis even if already exists

        Returns:
            Analysis results or None if failed
        """
        # Check if already analyzed
        if not force and has_analysis(channel_id, video_id, self.ANALYSIS_TYPE):
            return None

        try:
            # Fetch image from URL using synchronous request
            response = requests.get(thumbnail_url, timeout=30)
            response.raise_for_status()
            image_data = response.content

            # Analyze with Gemini Vision (uses response_schema when available)
            result = analyze_image(
                THUMBNAIL_ANALYSIS_PROMPT, image_data,
                analysis_type=self.ANALYSIS_TYPE,
            )

            if not result:
                logger.warning(f"Empty result from Gemini for thumbnail URL {video_id}")
                return None

            # Add metadata
            result['analyzedAt'] = datetime.utcnow().isoformat()
            result['modelUsed'] = config.GEMINI_MODEL
            result['analysisVersion'] = BATCH_ANALYSIS_VERSION

            # Save to Firestore
            save_analysis(channel_id, video_id, self.ANALYSIS_TYPE, result)

            return result

        except Exception as e:
            logger.error(f"Error analyzing thumbnail from URL {video_id}: {e}")
            return None
