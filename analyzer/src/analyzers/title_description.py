"""Combined title + description analysis using Gemini.

Merges title and description into a single API call for:
- Better context (description confirms/enriches niche detection)
- Fewer API calls (2 instead of 3+ per video)
- Same output quality for title fields, plus lean description insights
"""

from typing import Dict, Any, Optional
from datetime import datetime

from ..gemini_client import analyze_text
from ..firebase_client import save_analysis, has_analysis
from ..prompts import TITLE_DESCRIPTION_ANALYSIS_PROMPT
from ..config import config, logger


class TitleDescriptionAnalyzer:
    """Combined analyzer for YouTube video titles and descriptions."""

    ANALYSIS_TYPE = 'title_description'

    # Max description length to avoid token limits
    MAX_DESCRIPTION_LENGTH = 10000

    def analyze(self, channel_id: str, video_id: str,
                title: str, description: str,
                force: bool = False) -> Optional[Dict[str, Any]]:
        """
        Analyze a video title and description together.

        Args:
            channel_id: The channel ID
            video_id: The video ID
            title: The video title text
            description: The video description text
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
            # Build combined input text
            input_text = self._build_input_text(title, description)

            # Analyze with Gemini (single API call)
            result = analyze_text(TITLE_DESCRIPTION_ANALYSIS_PROMPT, input_text)

            # Add metadata
            result['analyzedAt'] = datetime.utcnow().isoformat()
            result['modelUsed'] = config.GEMINI_MODEL
            result['analysisVersion'] = '2.0'
            result['rawTitle'] = title
            result['hasDescription'] = bool(description and description.strip())

            # Save to Firestore
            save_analysis(channel_id, video_id, self.ANALYSIS_TYPE, result)

            return result

        except Exception as e:
            logger.error(f"Error analyzing title+description for {video_id}: {e}")
            return None

    def _build_input_text(self, title: str, description: str) -> str:
        """Build the combined input text for Gemini.

        Args:
            title: The video title
            description: The video description

        Returns:
            Formatted combined text
        """
        # Truncate description if too long
        desc = description or ''
        if len(desc) > self.MAX_DESCRIPTION_LENGTH:
            desc = desc[:self.MAX_DESCRIPTION_LENGTH]

        if desc.strip():
            return f"TITLE:\n{title}\n\nDESCRIPTION:\n{desc}"
        else:
            return f"TITLE:\n{title}\n\nDESCRIPTION:\n(no description provided)"
