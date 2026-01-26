"""Content structure analysis using Gemini.

This analyzer infers video content structure from descriptions and metadata,
providing transcript-like insights without needing actual transcripts.
It's a ToS-compliant alternative to transcript analysis.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime

from ..gemini_client import analyze_text
from ..firebase_client import save_analysis, has_analysis
from ..prompts import CONTENT_STRUCTURE_ANALYSIS_PROMPT
from ..config import config, logger


def format_duration(seconds: int) -> str:
    """Format seconds into human-readable duration."""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}m {secs}s"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours}h {minutes}m {secs}s"


class ContentStructureAnalyzer:
    """Analyzer for inferring video content structure from metadata."""

    ANALYSIS_TYPE = 'content_structure'

    def analyze(
        self,
        channel_id: str,
        video_id: str,
        title: str,
        description: str,
        duration_seconds: int,
        tags: List[str],
        force: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze video content structure from metadata.

        Args:
            channel_id: The channel ID
            video_id: The video ID
            title: The video title
            description: The video description text
            duration_seconds: Video duration in seconds
            tags: List of video tags
            force: Force re-analysis even if already exists

        Returns:
            Analysis results or None if failed
        """
        # Check if already analyzed
        if not force and has_analysis(channel_id, video_id, self.ANALYSIS_TYPE):
            return None

        # Need at least title or description
        if not title and not description:
            return None

        # Skip very short videos (likely shorts)
        if duration_seconds < 60:
            return None

        try:
            # Format the prompt with video metadata
            # Use replace() instead of format() to avoid KeyError on curly braces in content
            safe_title = (title or "No title").replace("{", "{{").replace("}", "}}")
            safe_description = (description[:8000] if description else "No description").replace("{", "{{").replace("}", "}}")
            safe_tags = ", ".join(tags[:20]) if tags else "No tags"

            formatted_prompt = CONTENT_STRUCTURE_ANALYSIS_PROMPT.replace(
                "{title}", safe_title
            ).replace(
                "{duration_seconds}", str(duration_seconds)
            ).replace(
                "{duration_formatted}", format_duration(duration_seconds)
            ).replace(
                "{tags}", safe_tags
            ).replace(
                "{description}", safe_description
            )

            # Analyze with Gemini
            result = analyze_text(formatted_prompt, "")

            # Add metadata
            result['analyzedAt'] = datetime.utcnow().isoformat()
            result['modelUsed'] = config.GEMINI_MODEL
            result['analysisVersion'] = '1.0'
            result['inputMetadata'] = {
                'titleLength': len(title) if title else 0,
                'descriptionLength': len(description) if description else 0,
                'durationSeconds': duration_seconds,
                'tagCount': len(tags) if tags else 0
            }

            # Save to Firestore
            save_analysis(channel_id, video_id, self.ANALYSIS_TYPE, result)

            return result

        except Exception as e:
            logger.error(f"Error analyzing content structure for {video_id}: {e}")
            return None
