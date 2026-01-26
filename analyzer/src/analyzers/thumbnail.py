"""Thumbnail analysis using Gemini Vision."""

from typing import Dict, Any, Optional
from datetime import datetime

from ..gemini_client import analyze_image
from ..firebase_client import download_thumbnail, save_analysis, has_analysis
from ..prompts import THUMBNAIL_ANALYSIS_PROMPT
from ..config import config


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

            # Analyze with Gemini Vision
            result = analyze_image(THUMBNAIL_ANALYSIS_PROMPT, image_data)

            # Add metadata
            result['analyzedAt'] = datetime.utcnow().isoformat()
            result['modelUsed'] = config.GEMINI_MODEL
            result['analysisVersion'] = '1.0'

            # Save to Firestore
            save_analysis(channel_id, video_id, self.ANALYSIS_TYPE, result)

            return result

        except Exception as e:
            print(f"Error analyzing thumbnail {video_id}: {e}")
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
        import requests

        try:
            # Fetch image from URL using synchronous request
            response = requests.get(thumbnail_url, timeout=30)
            response.raise_for_status()
            image_data = response.content

            # Analyze with Gemini Vision
            result = analyze_image(THUMBNAIL_ANALYSIS_PROMPT, image_data)

            # Add metadata
            result['analyzedAt'] = datetime.utcnow().isoformat()
            result['modelUsed'] = config.GEMINI_MODEL
            result['analysisVersion'] = '1.0'

            # Save to Firestore
            save_analysis(channel_id, video_id, self.ANALYSIS_TYPE, result)

            return result

        except Exception as e:
            print(f"Error analyzing thumbnail {video_id}: {e}")
            return None
