"""Title analysis using Gemini."""

from typing import Dict, Any, Optional
from datetime import datetime

from ..gemini_client import analyze_text
from ..firebase_client import save_analysis, has_analysis
from ..prompts import TITLE_ANALYSIS_PROMPT
from ..config import config


class TitleAnalyzer:
    """Analyzer for YouTube video titles."""

    ANALYSIS_TYPE = 'title'

    def analyze(self, channel_id: str, video_id: str,
                title: str, force: bool = False) -> Optional[Dict[str, Any]]:
        """
        Analyze a video title.

        Args:
            channel_id: The channel ID
            video_id: The video ID
            title: The video title text
            force: Force re-analysis even if already exists

        Returns:
            Analysis results or None if failed
        """
        # Check if already analyzed
        if not force and has_analysis(channel_id, video_id, self.ANALYSIS_TYPE):
            return None

        if not title or not title.strip():
            return None

        try:
            # Analyze with Gemini
            result = analyze_text(TITLE_ANALYSIS_PROMPT, title)

            # Add metadata
            result['analyzedAt'] = datetime.utcnow().isoformat()
            result['modelUsed'] = config.GEMINI_MODEL
            result['analysisVersion'] = '1.0'
            result['rawTitle'] = title

            # Save to Firestore
            save_analysis(channel_id, video_id, self.ANALYSIS_TYPE, result)

            return result

        except Exception as e:
            print(f"Error analyzing title for {video_id}: {e}")
            return None
