/**
 * Fallback templates for recommendation generation
 * Used when AI generation fails or insights are not available
 */

import type { ContentType, ThumbnailRecommendation, TagRecommendations, ContentRecommendations } from './types';

// ============================================
// Title Templates
// ============================================

export const TITLE_TEMPLATES: Record<ContentType, string[]> = {
  recipe: [
    '{dish} Recipe | {dish_telugu} | {modifier}',
    '{modifier} {dish} | {dish_telugu} | Restaurant Style',
    'SECRET {dish} Recipe | {dish_telugu} రహస్యం',
    'How to Make {dish} | {dish_telugu} | Easy Recipe',
    '{dish} at Home | {dish_telugu} | Hotel Style',
  ],
  vlog: [
    'My {topic} Experience | {topic_telugu}',
    'A Day in {location} | {topic_telugu}',
    '{topic} Vlog | {topic_telugu} | Telugu',
    'Exploring {topic} | {topic_telugu}',
  ],
  tutorial: [
    'How to {topic} | {topic_telugu} | Complete Guide',
    '{topic} for Beginners | {topic_telugu}',
    '{topic} Tutorial | {topic_telugu} | Step by Step',
    'Learn {topic} | {topic_telugu} | Easy Method',
  ],
  review: [
    '{topic} Review | {topic_telugu} | Honest Opinion',
    'Is {topic} Worth It? | {topic_telugu}',
    '{topic} - Complete Review | {topic_telugu}',
  ],
  challenge: [
    '{topic} Challenge | {topic_telugu}',
    'I Tried {topic} | {topic_telugu} | Challenge',
    '{number} {topic} Challenge | {topic_telugu}',
  ],
};

// ============================================
// Power Words
// ============================================

export const POWER_WORDS = {
  telugu: [
    'రహస్యం',      // Secret
    'పర్ఫెక్ట్',     // Perfect
    'అసలైన',       // Authentic
    'హోటల్ స్టైల్',  // Hotel Style
    'సులభం',       // Easy
    'త్వరగా',       // Quick
    'ఆరోగ్యకరమైన',  // Healthy
    'రుచికరమైన',   // Tasty
  ],
  english: [
    'SECRET',
    'PERFECT',
    'AUTHENTIC',
    'Restaurant Style',
    'Hotel Style',
    'Easy',
    'Quick',
    'Best',
    'Ultimate',
    'Amazing',
  ],
};

// ============================================
// Thumbnail Specifications
// ============================================

export const THUMBNAIL_SPECS: Record<ContentType, ThumbnailRecommendation> = {
  recipe: {
    layout: {
      type: 'split-composition',
      description: 'Face on right third, food on left with steam effect',
    },
    elements: {
      face: {
        required: true,
        expression: 'surprised or excited',
        position: 'right-third',
        size: 'large',
        eyeContact: true,
      },
      mainVisual: {
        type: 'food-close-up',
        position: 'left-center',
        showSteam: true,
        garnished: true,
      },
      text: {
        primary: {
          content: 'RECIPE',
          position: 'top-left',
          color: '#FFFF00',
          style: 'bold-with-outline',
        },
        secondary: {
          content: 'Telugu text',
          position: 'bottom',
          color: '#FFFFFF',
          language: 'telugu',
        },
      },
      graphics: {
        addArrow: true,
        arrowPointTo: 'food',
        addBorder: true,
        borderColor: '#FFFFFF',
      },
    },
    colors: {
      background: '#FF6B35',
      accent: '#FFFF00',
      text: '#FFFFFF',
    },
  },
  vlog: {
    layout: {
      type: 'full-frame',
      description: 'Person in interesting location or situation',
    },
    elements: {
      face: {
        required: true,
        expression: 'happy or curious',
        position: 'center',
        size: 'large',
        eyeContact: true,
      },
      mainVisual: {
        type: 'location-background',
        position: 'full-frame',
      },
      text: {
        primary: {
          content: 'Topic',
          position: 'top-center',
          color: '#FFFFFF',
          style: 'bold-shadow',
        },
      },
      graphics: {
        addArrow: false,
        addBorder: true,
        borderColor: '#FFFFFF',
      },
    },
    colors: {
      background: '#3498DB',
      accent: '#FFFFFF',
      text: '#FFFFFF',
    },
  },
  tutorial: {
    layout: {
      type: 'instructional',
      description: 'Clean layout with subject matter visible',
    },
    elements: {
      face: {
        required: false,
        expression: 'focused',
        position: 'corner',
        size: 'medium',
        eyeContact: false,
      },
      mainVisual: {
        type: 'subject-matter',
        position: 'center',
      },
      text: {
        primary: {
          content: 'How To',
          position: 'top-left',
          color: '#FFFFFF',
          style: 'bold',
        },
      },
      graphics: {
        addArrow: true,
        arrowPointTo: 'subject',
        addBorder: false,
      },
    },
    colors: {
      background: '#2C3E50',
      accent: '#E74C3C',
      text: '#FFFFFF',
    },
  },
  review: {
    layout: {
      type: 'product-focus',
      description: 'Product prominently displayed with reaction face',
    },
    elements: {
      face: {
        required: true,
        expression: 'thinking or surprised',
        position: 'right-third',
        size: 'medium',
        eyeContact: true,
      },
      mainVisual: {
        type: 'product',
        position: 'left-center',
      },
      text: {
        primary: {
          content: 'REVIEW',
          position: 'top-left',
          color: '#FFFF00',
          style: 'bold',
        },
      },
      graphics: {
        addArrow: true,
        arrowPointTo: 'product',
        addBorder: true,
        borderColor: '#FFFF00',
      },
    },
    colors: {
      background: '#9B59B6',
      accent: '#FFFF00',
      text: '#FFFFFF',
    },
  },
  challenge: {
    layout: {
      type: 'dramatic',
      description: 'High-energy composition with dramatic expression',
    },
    elements: {
      face: {
        required: true,
        expression: 'shocked or excited',
        position: 'center',
        size: 'large',
        eyeContact: true,
      },
      mainVisual: {
        type: 'challenge-items',
        position: 'around-face',
      },
      text: {
        primary: {
          content: 'CHALLENGE',
          position: 'top-center',
          color: '#FF0000',
          style: 'bold-shadow',
        },
      },
      graphics: {
        addArrow: false,
        addBorder: true,
        borderColor: '#FF0000',
      },
    },
    colors: {
      background: '#E74C3C',
      accent: '#FFFF00',
      text: '#FFFFFF',
    },
  },
};

// ============================================
// Default Tags by Content Type
// ============================================

export const DEFAULT_TAGS: Record<ContentType, Partial<TagRecommendations>> = {
  recipe: {
    primary: ['recipe', 'cooking', 'food'],
    secondary: ['homemade', 'easy recipe', 'how to cook'],
    telugu: ['వంటకం', 'తెలుగు వంట', 'రెసిపీ'],
    longtail: ['easy recipe at home', 'step by step recipe'],
  },
  vlog: {
    primary: ['vlog', 'telugu vlog', 'daily vlog'],
    secondary: ['lifestyle', 'day in my life'],
    telugu: ['వ్లాగ్', 'తెలుగు వ్లాగ్', 'రోజువారీ'],
    longtail: ['telugu vlogger', 'indian vlogger'],
  },
  tutorial: {
    primary: ['tutorial', 'how to', 'guide'],
    secondary: ['learn', 'tips', 'beginner'],
    telugu: ['ట్యుటోరియల్', 'నేర్చుకోండి', 'గైడ్'],
    longtail: ['complete guide', 'step by step tutorial'],
  },
  review: {
    primary: ['review', 'honest review', 'opinion'],
    secondary: ['unboxing', 'first look', 'worth it'],
    telugu: ['రివ్యూ', 'అభిప్రాయం'],
    longtail: ['honest opinion', 'should you buy'],
  },
  challenge: {
    primary: ['challenge', 'fun', 'entertainment'],
    secondary: ['trying', 'first time', 'experiment'],
    telugu: ['ఛాలెంజ్', 'వినోదం'],
    longtail: ['challenge video', 'funny challenge'],
  },
};

// ============================================
// Default Posting Times
// ============================================

export const DEFAULT_POSTING = {
  bestDay: 'Saturday',
  bestTime: '18:00 IST',
  alternativeTimes: ['Sunday 12:00 IST', 'Friday 19:00 IST'],
  reasoning: 'Weekend evenings typically have highest Telugu audience engagement',
};

// ============================================
// Content Recommendations by Type
// ============================================

export const CONTENT_RECOMMENDATIONS: Record<ContentType, ContentRecommendations> = {
  recipe: {
    optimalDuration: '10-15 minutes',
    mustInclude: [
      'Ingredient list with measurements',
      'Step-by-step cooking process',
      'Final dish reveal with garnish',
      'Taste test or serving suggestion',
    ],
    hooks: [
      'Start with the final dish reveal',
      'Mention "secret" or "restaurant trick" in first 30 seconds',
      'Show the most appetizing shot early',
    ],
    description: {
      template: 'Recipe description with ingredients and timestamps',
      mustInclude: ['timestamps', 'full ingredient list', 'cooking tips', 'social links'],
    },
  },
  vlog: {
    optimalDuration: '12-20 minutes',
    mustInclude: [
      'Engaging intro hook',
      'Story arc with beginning, middle, end',
      'Personal moments and reactions',
      'Call to action for engagement',
    ],
    hooks: [
      'Start with most exciting moment',
      'Pose a question to be answered',
      'Show unexpected situation',
    ],
    description: {
      template: 'Vlog description with context and timestamps',
      mustInclude: ['context', 'location details', 'timestamps', 'social links'],
    },
  },
  tutorial: {
    optimalDuration: '8-15 minutes',
    mustInclude: [
      'Clear problem statement',
      'Step-by-step instructions',
      'Common mistakes to avoid',
      'Final result demonstration',
    ],
    hooks: [
      'Show the end result first',
      'Mention how easy/fast it is',
      'Address common pain point',
    ],
    description: {
      template: 'Tutorial description with steps and resources',
      mustInclude: ['timestamps', 'resources/links', 'prerequisites', 'summary'],
    },
  },
  review: {
    optimalDuration: '10-15 minutes',
    mustInclude: [
      'Product overview',
      'Pros and cons',
      'Real-world usage demonstration',
      'Final verdict and recommendation',
    ],
    hooks: [
      'Give verdict hint in first 30 seconds',
      'Show the product in action',
      'Mention surprising finding',
    ],
    description: {
      template: 'Review description with specs and verdict',
      mustInclude: ['product specs', 'price', 'where to buy', 'timestamps'],
    },
  },
  challenge: {
    optimalDuration: '10-18 minutes',
    mustInclude: [
      'Clear challenge explanation',
      'Rules and stakes',
      'Genuine reactions throughout',
      'Final outcome and reflection',
    ],
    hooks: [
      'Show dramatic moment from challenge',
      'Mention what\'s at stake',
      'Tease the outcome',
    ],
    description: {
      template: 'Challenge description with rules and outcome',
      mustInclude: ['challenge rules', 'participants', 'timestamps', 'outcome tease'],
    },
  },
};
