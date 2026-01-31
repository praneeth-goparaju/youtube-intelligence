# Prompts for AI analysis
from .thumbnail_prompt import THUMBNAIL_ANALYSIS_PROMPT
from .title_description_prompt import TITLE_DESCRIPTION_ANALYSIS_PROMPT

# Legacy prompts (kept for reference, no longer used in pipeline)
from .title_prompt import TITLE_ANALYSIS_PROMPT
from .description_prompt import DESCRIPTION_ANALYSIS_PROMPT

__all__ = [
    'THUMBNAIL_ANALYSIS_PROMPT',
    'TITLE_DESCRIPTION_ANALYSIS_PROMPT',
    'TITLE_ANALYSIS_PROMPT',
    'DESCRIPTION_ANALYSIS_PROMPT',
]
