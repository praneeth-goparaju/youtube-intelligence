"""Templates for generating recommendations."""

from typing import Dict, Any, List, Optional


# Title templates based on common patterns
TITLE_TEMPLATES = {
    'recipe': [
        "{dish} Recipe | {dish_telugu} | {modifier}",
        "{modifier} {dish} | {dish_telugu} | Restaurant Style",
        "How to Make {dish} at Home | {dish_telugu}",
        "{dish} {modifier} | {dish_telugu} | Full Recipe",
        "SECRET {dish} Recipe | {dish_telugu} రహస్యం",
    ],
    'vlog': [
        "My {topic} Experience | {topic_telugu}",
        "A Day in {location} | {topic_telugu}",
        "{topic} Vlog | {topic_telugu} | Full Tour",
        "Exploring {location} | {topic_telugu}",
    ],
    'tutorial': [
        "How to {action} | {topic_telugu} | Complete Guide",
        "{topic} Tutorial for Beginners | {topic_telugu}",
        "Learn {topic} in {time} | {topic_telugu}",
        "{topic} Tips & Tricks | {topic_telugu}",
    ],
    'review': [
        "{product} Review | {product_telugu} | Worth It?",
        "Honest {product} Review | {product_telugu}",
        "{product} vs {competitor} | Which is Better?",
        "My Experience with {product} | {product_telugu}",
    ],
    'challenge': [
        "{number}x {dish} Challenge | {dish_telugu}",
        "{time} {topic} Challenge | {topic_telugu}",
        "Can I {action}? | {topic_telugu}",
        "{topic} Challenge GONE WRONG?!",
    ],
}

# Thumbnail specifications based on patterns
THUMBNAIL_SPECS = {
    'recipe': {
        'layout': 'split-composition',
        'face': {
            'required': True,
            'position': 'right-third',
            'expression': 'surprised or excited',
            'size': 'large',
        },
        'food': {
            'required': True,
            'position': 'left-center',
            'style': 'close-up with steam',
        },
        'text': {
            'primary': {
                'position': 'top-left',
                'style': 'bold with outline',
                'color': '#FFFF00',
            },
            'secondary': {
                'position': 'bottom',
                'language': 'telugu',
                'color': '#FFFFFF',
            },
        },
        'colors': {
            'background': '#FF6B35',
            'accent': '#FFFF00',
            'text': '#FFFFFF',
        },
    },
    'vlog': {
        'layout': 'single-focus',
        'face': {
            'required': True,
            'position': 'center',
            'expression': 'happy or curious',
            'size': 'large',
        },
        'background': {
            'type': 'location-based',
            'blur': False,
        },
        'text': {
            'primary': {
                'position': 'bottom',
                'style': 'bold with shadow',
            },
        },
    },
    'challenge': {
        'layout': 'split-screen',
        'face': {
            'required': True,
            'expression': 'shocked or extreme',
            'size': 'dominant',
        },
        'graphics': {
            'arrows': True,
            'badges': True,
            'numbers': True,
        },
        'colors': {
            'high_contrast': True,
            'primary': '#FF0000',
            'secondary': '#FFFF00',
        },
    },
}

# Power words by category
POWER_WORDS = {
    'telugu': {
        'quality': ['రహస్యం', 'పర్ఫెక్ట్', 'అసలైన', 'హోటల్ స్టైల్'],
        'emotion': ['అద్భుతం', 'అమేజింగ్', 'షాకింగ్'],
        'action': ['ట్రై చేయండి', 'తప్పక చూడండి'],
    },
    'english': {
        'quality': ['SECRET', 'PERFECT', 'AUTHENTIC', 'Restaurant Style', 'BEST'],
        'urgency': ['NOW', 'TODAY', 'LIMITED', 'MUST TRY'],
        'curiosity': ['REVEALED', 'TRUTH', 'Actually', 'Hidden'],
        'emotion': ['AMAZING', 'INCREDIBLE', 'SHOCKING'],
    },
}


def get_title_templates(content_type: str) -> List[str]:
    """Get title templates for a content type."""
    return TITLE_TEMPLATES.get(content_type, TITLE_TEMPLATES['recipe'])


def get_thumbnail_spec(content_type: str) -> Dict[str, Any]:
    """Get thumbnail specification for a content type."""
    return THUMBNAIL_SPECS.get(content_type, THUMBNAIL_SPECS['recipe'])


def get_power_words(language: str = 'both') -> Dict[str, List[str]]:
    """Get power words for a language."""
    if language == 'telugu':
        return POWER_WORDS['telugu']
    elif language == 'english':
        return POWER_WORDS['english']
    else:
        # Combine both
        combined = {}
        for category in set(list(POWER_WORDS['telugu'].keys()) + list(POWER_WORDS['english'].keys())):
            combined[category] = (
                POWER_WORDS['telugu'].get(category, []) +
                POWER_WORDS['english'].get(category, [])
            )
        return combined
