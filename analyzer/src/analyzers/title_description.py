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
from ..prompts import TITLE_DESCRIPTION_ANALYSIS_PROMPT, build_title_description_input
from ..config import config, logger
from .local_text_features import extract_local_features, deep_merge


class TitleDescriptionAnalyzer:
    """Combined analyzer for YouTube video titles and descriptions."""

    ANALYSIS_TYPE = 'title_description'

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
            # Build combined input text (shared with batch mode)
            input_text = build_title_description_input(title, description)

            # Analyze with Gemini (single API call, uses response_schema when available)
            gemini_result = analyze_text(
                TITLE_DESCRIPTION_ANALYSIS_PROMPT, input_text,
                analysis_type=self.ANALYSIS_TYPE,
            )

            if not gemini_result:
                logger.warning(f"Empty result from Gemini for {video_id}")
                return None

            # Compute local (deterministic) features and merge with Gemini output
            local_result = extract_local_features(title, description)
            result = deep_merge(gemini_result, local_result)

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
