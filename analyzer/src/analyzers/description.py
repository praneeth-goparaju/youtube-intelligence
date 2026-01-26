"""Description analysis using Gemini."""

from typing import Dict, Any, Optional
from datetime import datetime

from ..gemini_client import analyze_text
from ..firebase_client import save_analysis, has_analysis
from ..prompts import DESCRIPTION_ANALYSIS_PROMPT
from ..config import config


class DescriptionAnalyzer:
    """Analyzer for YouTube video descriptions."""

    ANALYSIS_TYPE = 'description'

    def analyze(self, channel_id: str, video_id: str,
                description: str, force: bool = False) -> Optional[Dict[str, Any]]:
        """
        Analyze a video description.

        Args:
            channel_id: The channel ID
            video_id: The video ID
            description: The video description text
            force: Force re-analysis even if already exists

        Returns:
            Analysis results or None if failed
        """
        # Check if already analyzed
        if not force and has_analysis(channel_id, video_id, self.ANALYSIS_TYPE):
            return None

        if not description or not description.strip():
            return None

        try:
            # Truncate very long descriptions to avoid token limits
            truncated = description[:10000] if len(description) > 10000 else description

            # Analyze with Gemini
            result = analyze_text(DESCRIPTION_ANALYSIS_PROMPT, truncated)

            # Add metadata
            result['analyzedAt'] = datetime.utcnow().isoformat()
            result['modelUsed'] = config.GEMINI_MODEL
            result['analysisVersion'] = '1.0'

            # Save to Firestore
            save_analysis(channel_id, video_id, self.ANALYSIS_TYPE, result)

            return result

        except Exception as e:
            print(f"Error analyzing description for {video_id}: {e}")
            return None
