"""Local (non-LLM) feature extraction for title + description analysis.

Computes deterministic fields that don't require semantic understanding:
character counts, emoji detection, URL/link patterns, hashtag parsing,
bracket detection, CTA keyword matching, monetization signals, etc.

These fields are merged with Gemini's semantic analysis to form the
complete title_description analysis document.
"""

import re
import unicodedata
from typing import Dict, Any, List


# ── Unicode range patterns ──────────────────────────────────────────────────

_TELUGU_RE = re.compile(r'[\u0C00-\u0C7F]')
_DEVANAGARI_RE = re.compile(r'[\u0900-\u097F]')
_LATIN_RE = re.compile(r'[a-zA-Z]')

# Comprehensive emoji regex (emoji presentation sequences, modifiers, ZWJ sequences)
_EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # misc symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U0001F900-\U0001F9FF"  # supplemental symbols
    "\U0001FA00-\U0001FA6F"  # chess symbols
    "\U0001FA70-\U0001FAFF"  # symbols extended-A
    "\U00002702-\U000027B0"  # dingbats
    "\U000024C2-\U0001F251"  # enclosed chars
    "\U0000200D"             # ZWJ
    "\U0000FE0F"             # variation selector
    "]+",
    flags=re.UNICODE
)

# ── Title patterns ──────────────────────────────────────────────────────────

_BRACKET_RE = re.compile(r'[\(\)\[\]\{\}]')
_ROUND_BRACKET_RE = re.compile(r'\(([^)]*)\)')
_SQUARE_BRACKET_RE = re.compile(r'\[([^\]]*)\]')
_CURLY_BRACKET_RE = re.compile(r'\{([^}]*)\}')

_YEAR_RE = re.compile(r'\b((?:19|20)\d{2})\b')
_HASHTAG_RE = re.compile(r'#[\w\u0C00-\u0C7F]+', re.UNICODE)
_NUMBER_RE = re.compile(r'\d+')
_SPECIAL_CHAR_RE = re.compile(r'[^\w\s\u0C00-\u0C7F\u0900-\u097F]', re.UNICODE)
_QUESTION_RE = re.compile(r'[?？]')

# ── Description patterns ────────────────────────────────────────────────────

_TIMESTAMP_RE = re.compile(r'\d{1,2}:\d{2}')
_URL_RE = re.compile(r'https?://[^\s<>"\']+', re.IGNORECASE)

_SOCIAL_DOMAINS = {
    'instagram.com', 'twitter.com', 'x.com', 'facebook.com', 'fb.com',
    'tiktok.com', 'snapchat.com', 'threads.net', 'linkedin.com',
}
_AFFILIATE_DOMAINS = {
    'amzn.to', 'bit.ly', 'tinyurl.com', 'goo.gl', 'shorte.st',
    'adf.ly', 'linktr.ee', 'shrinkme.io',
}
_AFFILIATE_PATTERNS = {'tag=', 'ref=', 'affiliate', '/dp/', '/gp/'}

_SUBSCRIBE_RE = re.compile(r'\bsub(?:scribe|scribed)?\b', re.IGNORECASE)
_LIKE_RE = re.compile(r'\b(?:like|liked|👍)\b', re.IGNORECASE)
_COMMENT_RE = re.compile(r'\bcomment(?:s|ed)?\b', re.IGNORECASE)

_SPONSOR_RE = re.compile(
    r'\b(?:sponsor(?:ed|ship)?|#ad|paid\s+(?:promotion|partnership)|'
    r'brand\s+partner(?:ship)?|collab(?:oration)?\s+with)\b',
    re.IGNORECASE
)
_DISCLOSURE_RE = re.compile(
    r'(?:\bdisclosure\b|#sponsored\b|#ad\b|\bpaid\s+promotion\b|\bcontains?\s+paid\b|'
    r'\bincludes?\s+paid\b|#paidpartnership\b)',
    re.IGNORECASE
)
_DISCOUNT_RE = re.compile(
    r'\b(?:(?:use|promo|discount|coupon)\s*(?:code)?|code\s*:)\b',
    re.IGNORECASE
)
_MERCH_RE = re.compile(
    r'\b(?:merch(?:andise)?|shop\.?\s|store\.?\s|teespring|spreadshop|bonfire)\b',
    re.IGNORECASE
)
_DONATION_RE = re.compile(
    r'\b(?:patreon|ko-?fi|buymeacoffee|buy\s*me\s*a\s*coffee|'
    r'paypal\.me|venmo|cash\s*app|superchat|super\s*thanks|'
    r'member(?:ship)?s?\s*join)\b',
    re.IGNORECASE
)


# ── Helpers ─────────────────────────────────────────────────────────────────

def _count_chars(text: str, pattern: re.Pattern) -> int:
    """Count characters matching a regex pattern."""
    return len(pattern.findall(text))


def _extract_emojis(text: str) -> List[str]:
    """Extract individual emoji characters from text."""
    emojis = []
    for char in text:
        if unicodedata.category(char).startswith(('So', 'Sk')) or _EMOJI_RE.match(char):
            emojis.append(char)
    # Also catch multi-char emoji sequences
    for match in _EMOJI_RE.finditer(text):
        seq = match.group().replace('\uFE0F', '').replace('\u200D', '')
        if len(seq) > 1:
            # Multi-char sequence not already captured individually
            if match.group() not in emojis:
                emojis.append(match.group())
    # Deduplicate while preserving order
    seen = set()
    result = []
    for e in emojis:
        if e not in seen:
            seen.add(e)
            result.append(e)
    return result


def _classify_emoji_positions(text: str) -> str:
    """Classify where emojis appear: start, middle, end (comma-separated)."""
    if not text:
        return ''
    matches = list(_EMOJI_RE.finditer(text))
    if not matches:
        return ''
    positions = set()
    text_len = len(text)
    third = text_len / 3
    for m in matches:
        pos = m.start()
        if pos < third:
            positions.add('start')
        elif pos > 2 * third:
            positions.add('end')
        else:
            positions.add('middle')
    order = ['start', 'middle', 'end']
    return ', '.join(p for p in order if p in positions)


def _detect_capitalization(text: str) -> Dict[str, Any]:
    """Detect capitalization style of a title."""
    latin_chars = _LATIN_RE.findall(text)
    if not latin_chars:
        return {
            'capitalization': 'lowercase',
            'allCaps': False,
            'partialCaps': False,
            'capsWords': '',
        }
    upper = sum(1 for c in latin_chars if c.isupper())
    ratio = upper / len(latin_chars) if latin_chars else 0
    words = text.split()
    caps_words = [w for w in words if w.isascii() and w.isupper() and len(w) > 1]

    all_caps = ratio > 0.8
    partial_caps = not all_caps and len(caps_words) > 0

    if all_caps:
        style = 'all-caps'
    elif partial_caps:
        style = 'mixed'
    elif all(w[0].isupper() for w in words if w and w[0].isalpha()):
        style = 'title-case'
    else:
        style = 'lowercase'

    return {
        'capitalization': style,
        'allCaps': all_caps,
        'partialCaps': partial_caps,
        'capsWords': ', '.join(caps_words),
    }


def _detect_brackets(text: str) -> Dict[str, Any]:
    """Detect bracket usage in title."""
    has_round = bool(_ROUND_BRACKET_RE.search(text))
    has_square = bool(_SQUARE_BRACKET_RE.search(text))
    has_curly = bool(_CURLY_BRACKET_RE.search(text))
    has_any = has_round or has_square or has_curly

    if has_round:
        bracket_type = 'round'
        content = _ROUND_BRACKET_RE.findall(text)
    elif has_square:
        bracket_type = 'square'
        content = _SQUARE_BRACKET_RE.findall(text)
    elif has_curly:
        bracket_type = 'curly'
        content = _CURLY_BRACKET_RE.findall(text)
    else:
        bracket_type = 'none'
        content = []

    return {
        'hasBrackets': has_any,
        'bracketType': bracket_type,
        'bracketContent': ', '.join(content) if content else 'none',
    }


def _detect_special_chars(text: str) -> Dict[str, Any]:
    """Detect special characters (non-alphanumeric, non-space, non-script chars)."""
    # Remove emojis first to avoid counting them as special chars
    no_emoji = _EMOJI_RE.sub('', text)
    # Find special chars excluding common punctuation-like separators
    chars = set(_SPECIAL_CHAR_RE.findall(no_emoji))
    # Remove common harmless chars
    chars -= {',', '.', '!', '?', "'", '"', '-', ':', ';', '|', '/', '(', ')', '[', ']', '{', '}', '#', '@', '&', '+', '=', '*'}
    filtered = sorted(chars)
    return {
        'hasSpecialChars': len(filtered) > 0,
        'specialChars': ', '.join(filtered) if filtered else '',
    }


def _detect_punctuation(text: str) -> Dict[str, Any]:
    """Detect ending punctuation type."""
    text = text.rstrip()
    if not text:
        return {
            'endsWithPunctuation': False,
            'punctuationType': 'none',
            'hasExclamation': False,
            'hasQuestion': False,
        }
    last = text[-1]
    has_excl = '!' in text
    has_q = bool(_QUESTION_RE.search(text))
    ends_punct = last in '.!?。！？'
    if last in '!！':
        ptype = 'exclamation'
    elif last in '?？':
        ptype = 'question'
    elif last in '.。':
        ptype = 'period'
    else:
        ptype = 'none'
        ends_punct = False
    return {
        'endsWithPunctuation': ends_punct,
        'punctuationType': ptype,
        'hasExclamation': has_excl,
        'hasQuestion': has_q,
    }


def _classify_url(url: str) -> Dict[str, bool]:
    """Classify a URL into categories."""
    url_lower = url.lower()
    result = {
        'social': False,
        'affiliate': False,
        'youtube_video': False,
        'playlist': False,
        'website': False,
    }
    # Extract domain
    domain_match = re.search(r'https?://(?:www\.)?([^/]+)', url_lower)
    domain = domain_match.group(1) if domain_match else ''

    if any(sd in domain for sd in _SOCIAL_DOMAINS):
        result['social'] = True
    elif any(ad in domain for ad in _AFFILIATE_DOMAINS):
        result['affiliate'] = True
    elif any(p in url_lower for p in _AFFILIATE_PATTERNS):
        result['affiliate'] = True
    elif 'youtube.com' in domain or 'youtu.be' in domain:
        if 'playlist' in url_lower or 'list=' in url_lower:
            result['playlist'] = True
        else:
            result['youtube_video'] = True
    else:
        result['website'] = True
    return result


def _detect_hashtag_position(description: str) -> str:
    """Detect where hashtags appear in description."""
    if not description:
        return 'none'
    lines = description.strip().split('\n')
    total = len(lines)
    if total == 0:
        return 'none'

    hashtag_lines = []
    for i, line in enumerate(lines):
        if _HASHTAG_RE.search(line):
            hashtag_lines.append(i)

    if not hashtag_lines:
        return 'none'

    third = total / 3
    positions = set()
    for idx in hashtag_lines:
        if idx < third:
            positions.add('start')
        elif idx >= 2 * third:
            positions.add('end')
        else:
            positions.add('middle')

    if len(positions) >= 2:
        return 'throughout'
    return positions.pop()


def _detect_scripts(text: str) -> List[str]:
    """Detect which scripts are present in text."""
    scripts = []
    if _LATIN_RE.search(text):
        scripts.append('latin')
    if _TELUGU_RE.search(text):
        scripts.append('telugu')
    if _DEVANAGARI_RE.search(text):
        scripts.append('devanagari')
    return scripts


def _detect_languages(text: str) -> List[str]:
    """Detect which languages are likely present based on scripts."""
    languages = []
    if _LATIN_RE.search(text):
        languages.append('english')
    if _TELUGU_RE.search(text):
        languages.append('telugu')
    if _DEVANAGARI_RE.search(text):
        languages.append('hindi')
    return languages or ['english']  # Default to english


# ── Main extraction ─────────────────────────────────────────────────────────

def extract_local_features(title: str, description: str) -> Dict[str, Any]:
    """Extract all deterministic (non-LLM) features from title and description.

    Returns a nested dict matching the analysis document structure, ready
    to be deep-merged with Gemini's semantic analysis output.

    Args:
        title: Video title text
        description: Video description text (may be empty/None)

    Returns:
        Dict with keys: structure, language, hooks, formatting, descriptionAnalysis
    """
    title = title or ''
    description = description or ''

    return {
        'structure': _extract_title_structure(title),
        'language': _extract_title_language(title),
        'hooks': _extract_title_hooks(title),
        'formatting': _extract_title_formatting(title),
        'descriptionAnalysis': _extract_description_features(description),
    }


def _extract_title_structure(title: str) -> Dict[str, Any]:
    """Extract deterministic structure fields from title."""
    # Segment detection: common separators
    separators = ['|', ' - ', ' – ', ' — ', ':', ' / ']
    sep_found = 'none'
    segments = [title]
    for sep in separators:
        if sep in title:
            parts = title.split(sep)
            if len(parts) > 1:
                sep_found = sep.strip()
                segments = parts
                break

    telugu_count = _count_chars(title, _TELUGU_RE)
    english_count = _count_chars(title, _LATIN_RE)

    return {
        'segmentCount': len(segments),
        'separator': sep_found,
        'separatorConsistent': True,  # Single separator type = consistent
        'characterCount': len(title),
        'characterCountNoSpaces': len(title.replace(' ', '')),
        'wordCount': len(title.split()),
        'teluguCharacterCount': telugu_count,
        'englishCharacterCount': english_count,
    }


def _extract_title_language(title: str) -> Dict[str, Any]:
    """Extract deterministic language fields from title."""
    telugu_count = _count_chars(title, _TELUGU_RE)
    english_count = _count_chars(title, _LATIN_RE)
    total_script = telugu_count + english_count
    telugu_ratio = telugu_count / total_script if total_script > 0 else 0.0
    english_ratio = english_count / total_script if total_script > 0 else 0.0

    scripts = _detect_scripts(title)
    languages = _detect_languages(title)

    has_telugu = 'telugu' in scripts
    has_latin = 'latin' in scripts

    primary = 'telugu' if telugu_ratio > 0.5 else 'english'
    secondary = 'none'
    if len(languages) > 1:
        secondary = [l for l in languages if l != primary][0]

    return {
        'languages': languages,
        'primaryLanguage': primary,
        'secondaryLanguage': secondary,
        'scripts': scripts,
        'hasTeluguScript': has_telugu,
        'hasLatinScript': has_latin,
        'teluguRatio': round(telugu_ratio, 2),
        'englishRatio': round(english_ratio, 2),
    }


def _extract_title_hooks(title: str) -> Dict[str, Any]:
    """Extract deterministic hook fields from title."""
    is_question = bool(_QUESTION_RE.search(title))
    numbers = _NUMBER_RE.findall(title)
    return {
        'isQuestion': is_question,
        'hasNumber': len(numbers) > 0,
        'numbers': ', '.join(numbers) if numbers else '',
    }


def _extract_title_formatting(title: str) -> Dict[str, Any]:
    """Extract all formatting fields from title."""
    emojis = _extract_emojis(title)
    emoji_positions = _classify_emoji_positions(title)

    caps = _detect_capitalization(title)
    brackets = _detect_brackets(title)
    special = _detect_special_chars(title)
    punct = _detect_punctuation(title)

    years = _YEAR_RE.findall(title)
    hashtags = _HASHTAG_RE.findall(title)

    result = {
        'hasEmoji': len(emojis) > 0,
        'emojiList': ', '.join(emojis) if emojis else '',
        'emojiPositions': emoji_positions,
        'hasYear': len(years) > 0,
        'year': years[0] if years else 'none',
        'hasHashtag': len(hashtags) > 0,
        'hashtags': ', '.join(hashtags) if hashtags else '',
    }
    result.update(caps)
    result.update(brackets)
    result.update(special)
    result.update(punct)
    return result


def _extract_description_features(description: str) -> Dict[str, Any]:
    """Extract all deterministic description features."""
    if not description.strip():
        return {
            'structure': {'length': 0, 'lineCount': 0},
            'timestamps': {'hasTimestamps': False, 'timestampCount': 0},
            'hashtags': {'count': 0, 'position': 'none'},
            'ctas': {
                'hasSubscribeCTA': False,
                'hasLikeCTA': False,
                'hasCommentCTA': False,
            },
            'links': {
                'hasSocialMediaLinks': False,
                'hasAffiliateLinks': False,
                'hasOtherVideoLinks': False,
                'hasPlaylistLinks': False,
                'hasWebsiteLink': False,
                'totalLinkCount': 0,
            },
            'monetization': {
                'hasSponsorMention': False,
                'hasDisclosure': False,
                'hasDiscountCode': False,
                'hasMerchLink': False,
                'hasDonationLink': False,
            },
        }

    lines = description.split('\n')
    timestamps = _TIMESTAMP_RE.findall(description)
    hashtags = _HASHTAG_RE.findall(description)
    urls = _URL_RE.findall(description)

    # Classify URLs
    has_social = False
    has_affiliate = False
    has_video = False
    has_playlist = False
    has_website = False
    for url in urls:
        cat = _classify_url(url)
        has_social = has_social or cat['social']
        has_affiliate = has_affiliate or cat['affiliate']
        has_video = has_video or cat['youtube_video']
        has_playlist = has_playlist or cat['playlist']
        has_website = has_website or cat['website']

    return {
        'structure': {
            'length': len(description),
            'lineCount': len(lines),
        },
        'timestamps': {
            'hasTimestamps': len(timestamps) > 0,
            'timestampCount': len(timestamps),
        },
        'hashtags': {
            'count': len(hashtags),
            'position': _detect_hashtag_position(description),
        },
        'ctas': {
            'hasSubscribeCTA': bool(_SUBSCRIBE_RE.search(description)),
            'hasLikeCTA': bool(_LIKE_RE.search(description)),
            'hasCommentCTA': bool(_COMMENT_RE.search(description)),
        },
        'links': {
            'hasSocialMediaLinks': has_social,
            'hasAffiliateLinks': has_affiliate,
            'hasOtherVideoLinks': has_video,
            'hasPlaylistLinks': has_playlist,
            'hasWebsiteLink': has_website,
            'totalLinkCount': len(urls),
        },
        'monetization': {
            'hasSponsorMention': bool(_SPONSOR_RE.search(description)),
            'hasDisclosure': bool(_DISCLOSURE_RE.search(description)),
            'hasDiscountCode': bool(_DISCOUNT_RE.search(description)),
            'hasMerchLink': bool(_MERCH_RE.search(description)),
            'hasDonationLink': bool(_DONATION_RE.search(description)),
        },
    }


# ── Merge utility ───────────────────────────────────────────────────────────

def deep_merge(base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge overlay dict into base dict. Overlay values win for conflicts.

    For nested dicts, merges recursively. For non-dict values, overlay wins.
    Neither input dict is modified; returns a new dict.

    Args:
        base: Base dictionary (e.g., Gemini output)
        overlay: Overlay dictionary (e.g., local features)

    Returns:
        New merged dictionary
    """
    result = dict(base)
    for key, value in overlay.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result
