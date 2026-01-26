"""Recommendation engine for generating video suggestions."""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
import google.generativeai as genai

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.gemini_utils import parse_json_response, validate_gemini_response
from shared.constants import (
    INSIGHT_TYPE_THUMBNAILS,
    INSIGHT_TYPE_TITLES,
    INSIGHT_TYPE_TIMING,
    INSIGHT_TYPE_CONTENT_GAPS,
)

from .config import config
from .firebase_client import get_all_insights, get_example_videos
from .templates import get_title_templates, get_thumbnail_spec, get_power_words


# Initialize Gemini
genai.configure(api_key=config.GOOGLE_API_KEY)


class RecommendationEngine:
    """Generate video recommendations based on insights."""

    def __init__(self):
        """Initialize the engine."""
        self.insights = get_all_insights()
        self.model = genai.GenerativeModel(
            model_name=config.GEMINI_MODEL,
            generation_config={
                'temperature': 0.7,
                'top_p': 0.95,
                'max_output_tokens': 4096,
            }
        )

    def generate_recommendation(self, topic: str,
                               content_type: str = 'recipe',
                               unique_angle: Optional[str] = None,
                               target_audience: str = 'telugu-audience') -> Dict[str, Any]:
        """
        Generate a complete video recommendation.

        Args:
            topic: The video topic (e.g., "biryani", "Germany travel")
            content_type: Type of content (recipe, vlog, tutorial, etc.)
            unique_angle: Unique positioning (e.g., "Germany kitchen")
            target_audience: Target audience description

        Returns:
            Complete recommendation with titles, thumbnail, tags, timing
        """
        # Build context from insights
        context = self._build_context()

        # Generate recommendations
        prompt = self._build_prompt(topic, content_type, unique_angle, target_audience, context)

        try:
            response = self.model.generate_content(prompt)
            response_text = validate_gemini_response(response)
            recommendation = parse_json_response(response_text)

        except Exception as e:
            print(f"AI generation failed, using templates: {e}")
            recommendation = self._generate_from_templates(
                topic, content_type, unique_angle, target_audience
            )

        # Add posting recommendation from insights
        recommendation['posting'] = self._get_posting_recommendation()

        # Add reference examples
        recommendation['examples'] = get_example_videos(limit=5)

        return recommendation

    def _build_context(self) -> str:
        """Build context string from insights."""
        context_parts = []

        # Thumbnail insights
        if INSIGHT_TYPE_THUMBNAILS in self.insights and self.insights[INSIGHT_TYPE_THUMBNAILS]:
            top_elements = self.insights[INSIGHT_TYPE_THUMBNAILS].get('topPerformingElements', [])[:5]
            if top_elements:
                context_parts.append("Top performing thumbnail elements:")
                for elem in top_elements:
                    elem_name = elem.get('element', 'unknown')
                    elem_lift = elem.get('lift', 1.0)
                    context_parts.append(f"  - {elem_name} ({elem_lift}x performance)")

        # Title insights
        if INSIGHT_TYPE_TITLES in self.insights and self.insights[INSIGHT_TYPE_TITLES]:
            power_words = self.insights[INSIGHT_TYPE_TITLES].get('topPowerWords', [])[:10]
            if power_words:
                context_parts.append("\nTop power words:")
                for pw in power_words:
                    word = pw.get('word', '')
                    count = pw.get('count', 0)
                    if word:
                        context_parts.append(f"  - {word} (used in {count} top videos)")

        # Timing insights
        if INSIGHT_TYPE_TIMING in self.insights and self.insights[INSIGHT_TYPE_TIMING]:
            optimal = self.insights[INSIGHT_TYPE_TIMING].get('bestTimes', {}).get('optimal', {})
            if optimal and optimal.get('day') and optimal.get('hourIST') is not None:
                context_parts.append(f"\nOptimal posting: {optimal.get('day')} at {optimal.get('hourIST')}:00 IST")

        # Content gaps
        if INSIGHT_TYPE_CONTENT_GAPS in self.insights and self.insights[INSIGHT_TYPE_CONTENT_GAPS]:
            gaps = self.insights[INSIGHT_TYPE_CONTENT_GAPS].get('contentGaps', {})
            opportunities = gaps.get('highOpportunity', [])[:3]
            if opportunities:
                context_parts.append("\nContent opportunities:")
                for opp in opportunities:
                    opp_topic = opp.get('topic', 'unknown')
                    avg_views = opp.get('avgViews', 0)
                    context_parts.append(f"  - {opp_topic} (avg {avg_views} views)")

        return '\n'.join(context_parts)

    def _build_prompt(self, topic: str, content_type: str,
                     unique_angle: Optional[str], target_audience: str,
                     context: str) -> str:
        """Build the recommendation prompt."""
        return f'''Generate a complete YouTube video recommendation for a Telugu channel.

TOPIC: {topic}
CONTENT TYPE: {content_type}
UNIQUE ANGLE: {unique_angle or "None specified"}
TARGET AUDIENCE: {target_audience}

INSIGHTS FROM ANALYSIS:
{context}

Generate a JSON response with this structure:
{{
  "titles": {{
    "primary": {{
      "english": "Primary title in English",
      "telugu": "Same in Telugu script",
      "combined": "Mixed language version with separators"
    }},
    "alternatives": [
      {{"title": "Alternative 1", "reasoning": "Why this works"}}
    ]
  }},
  "thumbnail": {{
    "layout": "Layout description",
    "elements": {{
      "face": {{"position": "...", "expression": "...", "required": true}},
      "mainVisual": {{"type": "...", "position": "...", "style": "..."}},
      "text": {{
        "primary": {{"content": "...", "position": "...", "color": "..."}},
        "secondary": {{"content": "...", "language": "telugu", "position": "..."}}
      }},
      "graphics": {{"arrows": true/false, "badges": true/false, "borderColor": "..."}}
    }},
    "colors": {{"background": "#HEX", "accent": "#HEX", "text": "#HEX"}}
  }},
  "tags": {{
    "primary": ["main keywords"],
    "secondary": ["supporting keywords"],
    "telugu": ["Telugu script tags"],
    "longtail": ["long tail phrases"],
    "brand": ["channel specific"]
  }},
  "content": {{
    "optimalDuration": "X-Y minutes",
    "mustInclude": ["key elements"],
    "hooks": ["opening hooks"],
    "structureSuggestion": "Content structure advice"
  }},
  "prediction": {{
    "expectedViewRange": {{"low": N, "medium": N, "high": N}},
    "positiveFactors": ["reasons for success"],
    "riskFactors": ["potential challenges"]
  }}
}}

IMPORTANT: Return only valid JSON, no markdown or explanation.'''

    def _generate_from_templates(self, topic: str, content_type: str,
                                unique_angle: Optional[str],
                                target_audience: str) -> Dict[str, Any]:
        """Generate recommendation from templates (fallback)."""
        templates = get_title_templates(content_type)
        thumbnail_spec = get_thumbnail_spec(content_type)

        # Generate titles with error handling for missing template placeholders
        titles = []
        template_vars = {
            'dish': topic,
            'dish_telugu': topic,
            'topic': topic,
            'topic_telugu': topic,
            'modifier': "Restaurant Style",
            'location': unique_angle or "Home",
            'action': "make",
            'product': topic,
            'product_telugu': topic,
            'number': "10",
            'time': "5 minutes",
            'competitor': "Alternative",
            'chef_name': "Chef",
            'style': "Traditional",
            'cuisine': "Food",
        }
        for template in templates[:3]:
            try:
                title = template.format(**template_vars)
                titles.append(title)
            except KeyError as e:
                # Template has a placeholder we don't have - use fallback
                print(f"Warning: Template missing key {e}, using fallback title")
                titles.append(f"{topic} - {content_type.title()}")

        return {
            'titles': {
                'primary': {
                    'english': titles[0] if titles else f"{topic} Recipe",
                    'telugu': topic,
                    'combined': titles[0] if titles else f"{topic} Recipe",
                },
                'alternatives': [
                    {'title': t, 'reasoning': 'Template-based'}
                    for t in titles[1:]
                ],
            },
            'thumbnail': thumbnail_spec,
            'tags': {
                'primary': [topic.lower(), f"{topic.lower()} recipe"],
                'secondary': ['telugu', 'cooking', 'food'],
                'telugu': [],
                'longtail': [f"how to make {topic.lower()}"],
                'brand': [],
            },
            'content': {
                'optimalDuration': '10-15 minutes',
                'mustInclude': ['introduction', 'ingredients', 'steps', 'final result'],
                'hooks': ['Show final result first'],
                'structureSuggestion': 'Start with appetizing visuals',
            },
            'prediction': {
                'expectedViewRange': {'low': 5000, 'medium': 20000, 'high': 100000},
                'positiveFactors': ['Popular topic'],
                'riskFactors': ['High competition'],
            },
        }

    def _get_posting_recommendation(self) -> Dict[str, Any]:
        """Get posting time recommendation from insights."""
        default_recommendation = {
            'bestDay': 'Saturday',
            'bestTime': '18:00 IST',
            'alternativeTimes': ['Sunday 12:00 IST'],
            'reasoning': 'Default recommendation (no insights available)',
        }

        if INSIGHT_TYPE_TIMING not in self.insights or not self.insights.get(INSIGHT_TYPE_TIMING):
            return default_recommendation

        timing = self.insights[INSIGHT_TYPE_TIMING].get('bestTimes', {})
        if not timing:
            return default_recommendation

        optimal = timing.get('optimal', {})

        by_day = timing.get('byDayOfWeek', [])
        by_hour = timing.get('byHourIST', [])

        # Get top 2 alternative times with safe access
        alternatives = []
        if by_day and by_hour:
            sorted_days = sorted(by_day, key=lambda x: x.get('multiplier', 0), reverse=True)
            sorted_hours = sorted(by_hour, key=lambda x: x.get('multiplier', 0), reverse=True)

            # Skip first day (already used as best) and take next 2
            for day in sorted_days[1:3]:
                day_name = day.get('day')
                if not day_name:
                    continue
                for hour in sorted_hours[:1]:
                    hour_val = hour.get('hour')
                    if hour_val is not None:
                        alternatives.append(f"{day_name} {hour_val}:00 IST")

        return {
            'bestDay': optimal.get('day', 'Saturday'),
            'bestTime': f"{optimal.get('hourIST', 18)}:00 IST",
            'alternativeTimes': alternatives[:3] if alternatives else ['Sunday 12:00 IST'],
            'reasoning': 'Based on analysis of top-performing videos in your niche',
        }
