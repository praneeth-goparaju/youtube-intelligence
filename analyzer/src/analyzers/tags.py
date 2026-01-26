"""Tags analysis using Gemini."""

from typing import Dict, Any, Optional, List
from datetime import datetime

from ..gemini_client import analyze_text
from ..firebase_client import save_analysis, has_analysis
from ..prompts import TAGS_ANALYSIS_PROMPT
from ..config import config, logger


class TagsAnalyzer:
    """Analyzer for YouTube video tags."""

    ANALYSIS_TYPE = 'tags'

    def analyze(self, channel_id: str, video_id: str,
                tags: List[str], force: bool = False) -> Optional[Dict[str, Any]]:
        """
        Analyze video tags.

        Args:
            channel_id: The channel ID
            video_id: The video ID
            tags: List of video tags
            force: Force re-analysis even if already exists

        Returns:
            Analysis results or None if failed
        """
        # Check if already analyzed
        if not force and has_analysis(channel_id, video_id, self.ANALYSIS_TYPE):
            return None

        if not tags or len(tags) == 0:
            return None

        try:
            # Format tags for prompt with sanitization to prevent prompt injection
            # Remove any curly braces that could interfere with template processing
            sanitized_tags = [tag.replace('{', '').replace('}', '') for tag in tags]
            tags_text = '\n'.join(f'- {tag}' for tag in sanitized_tags)

            # Replace placeholder in prompt
            prompt = TAGS_ANALYSIS_PROMPT.replace('{tags}', tags_text)

            # Analyze with Gemini
            result = analyze_text(prompt, '')  # Empty text since tags are in prompt

            # Add metadata
            result['analyzedAt'] = datetime.utcnow().isoformat()
            result['modelUsed'] = config.GEMINI_MODEL
            result['analysisVersion'] = '1.0'

            # Save to Firestore
            save_analysis(channel_id, video_id, self.ANALYSIS_TYPE, result)

            return result

        except Exception as e:
            logger.error(f"Error analyzing tags for {video_id}: {e}")
            return None
