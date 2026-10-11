"""Thumbnail analysis using Gemini Vision."""

from typing import Dict, Any, Optional

import requests

from ..gemini_client import analyze_image, GeminiResponseError
from ..firebase_client import download_thumbnail, save_analysis, has_analysis
from ..prompts import THUMBNAIL_ANALYSIS_PROMPT
from ..analysis_metadata import stamp_analysis_metadata


class ThumbnailAnalyzer:
    """Analyzer for YouTube video thumbnails."""

    ANALYSIS_TYPE = "thumbnail"

    def analyze(
        self, channel_id: str, video_id: str, thumbnail_path: str, force: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze a video thumbnail.

        Args:
            channel_id: The channel ID
            video_id: The video ID
            thumbnail_path: Path to thumbnail in Firebase Storage
            force: Force re-analysis even if already exists

        Returns:
            Analysis results, or None when the video is already analyzed or has no thumbnail path.
            Operational failures are raised to the caller.
        """
        # Check if already analyzed
        if not force and has_analysis(channel_id, video_id, self.ANALYSIS_TYPE):
            return None

        if not thumbnail_path:
            return None

        # Download thumbnail from storage
        image_data = download_thumbnail(thumbnail_path)

        # Analyze with Gemini Vision (uses response_schema when available)
        result = analyze_image(
            THUMBNAIL_ANALYSIS_PROMPT,
            image_data,
            analysis_type=self.ANALYSIS_TYPE,
        )

        if not result:
            raise GeminiResponseError(f"Empty result from Gemini for thumbnail {video_id}")

        # Add provenance metadata
        stamp_analysis_metadata(result)

        # Save to Firestore
        save_analysis(channel_id, video_id, self.ANALYSIS_TYPE, result)

        return result

    def analyze_from_url(
        self, channel_id: str, video_id: str, thumbnail_url: str, force: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze a thumbnail from URL (for testing without storage).

        Args:
            channel_id: The channel ID
            video_id: The video ID
            thumbnail_url: URL to the thumbnail image
            force: Force re-analysis even if already exists

        Returns:
            Analysis results, or None when the video is already analyzed.
            Operational failures are raised to the caller.
        """
        # Check if already analyzed
        if not force and has_analysis(channel_id, video_id, self.ANALYSIS_TYPE):
            return None

        # Fetch image from URL using synchronous request
        response = requests.get(thumbnail_url, timeout=30)
        response.raise_for_status()
        image_data = response.content

        # Analyze with Gemini Vision (uses response_schema when available)
        result = analyze_image(
            THUMBNAIL_ANALYSIS_PROMPT,
            image_data,
            analysis_type=self.ANALYSIS_TYPE,
        )

        if not result:
            raise GeminiResponseError(f"Empty result from Gemini for thumbnail URL {video_id}")

        # Add provenance metadata
        stamp_analysis_metadata(result)

        # Save to Firestore
        save_analysis(channel_id, video_id, self.ANALYSIS_TYPE, result)

        return result
