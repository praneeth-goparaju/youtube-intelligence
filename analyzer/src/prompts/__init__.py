# Prompts for AI analysis
from .thumbnail_prompt import (
    THUMBNAIL_ANALYSIS_PROMPT,
    THUMBNAIL_SYSTEM_INSTRUCTION,
    THUMBNAIL_USER_PROMPT,
)
from .title_description_prompt import (
    TITLE_DESCRIPTION_ANALYSIS_PROMPT,
    TITLE_DESC_SYSTEM_INSTRUCTION,
    TITLE_DESC_USER_PROMPT,
)

# Max description length to avoid token limits (shared between sync and batch)
MAX_DESCRIPTION_LENGTH = 10000


def build_title_description_input(title: str, description: str) -> str:
    """Build combined title+description input text for Gemini analysis.

    Shared between sync mode (TitleDescriptionAnalyzer) and batch mode (prepare.py)
    to ensure consistent formatting.

    Args:
        title: The video title
        description: The video description (may be empty/None)

    Returns:
        Formatted combined text with TITLE: and DESCRIPTION: sections
    """
    desc = description or ""
    if len(desc) > MAX_DESCRIPTION_LENGTH:
        desc = desc[:MAX_DESCRIPTION_LENGTH]

    if desc.strip():
        return f"TITLE:\n{title}\n\nDESCRIPTION:\n{desc}"
    else:
        return f"TITLE:\n{title}\n\nDESCRIPTION:\n(no description provided)"


__all__ = [
    "THUMBNAIL_ANALYSIS_PROMPT",
    "THUMBNAIL_SYSTEM_INSTRUCTION",
    "THUMBNAIL_USER_PROMPT",
    "TITLE_DESCRIPTION_ANALYSIS_PROMPT",
    "TITLE_DESC_SYSTEM_INSTRUCTION",
    "TITLE_DESC_USER_PROMPT",
    "MAX_DESCRIPTION_LENGTH",
    "build_title_description_input",
]
