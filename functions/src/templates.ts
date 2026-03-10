/**
 * Fallback templates for recommendation generation
 * Used when AI generation fails or insights are not available
 */

import type { ContentType, ThumbnailRecommendation, TagRecommendations, ProductionToolkit } from './types';

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
// Production Toolkit Templates by Type
// ============================================

export const PRODUCTION_TOOLKIT_TEMPLATES: Record<ContentType, ProductionToolkit> = {
  recipe: {
    optimalDuration: '10-15 minutes',
    hookScript: [
      { visual: '[Close-up of sizzling pan with oil shimmering]', dialogue: '"ఈ recipe చూస్తే మీరు షాక్ అవుతారు!"', duration: '0:00-0:05' },
      { visual: '[Quick cuts: raw ingredients → finished dish]', dialogue: '"Restaurant secret ఇదే — ఇంట్లోనే perfect గా!"', duration: '0:05-0:10' },
      { visual: '[Host takes first bite, reacts]', dialogue: '"ఈ రోజు step-by-step చూపిస్తా, miss అవ్వకండి!"', duration: '0:10-0:15' },
    ],
    segments: [
      { startTime: '0:00', endTime: '0:15', title: 'Hook', description: 'Final dish reveal + promise', tips: 'Show steam and garnish for appetite appeal' },
      { startTime: '0:15', endTime: '1:30', title: 'Ingredients', description: 'Full ingredient display with measurements', tips: 'Use text overlays for quantities' },
      { startTime: '1:30', endTime: '3:00', title: 'Preparation', description: 'Washing, cutting, marinating', tips: 'Speed up repetitive steps with 2x' },
      { startTime: '3:00', endTime: '7:00', title: 'Cooking', description: 'Main cooking process step by step', tips: 'Close-up on color changes and sizzling' },
      { startTime: '7:00', endTime: '9:00', title: 'Plating', description: 'Garnishing and presentation', tips: 'Use slow-motion for garnish drops' },
      { startTime: '9:00', endTime: '10:00', title: 'Taste Test', description: 'Host tastes and reacts', tips: 'Genuine reaction builds trust' },
      { startTime: '10:00', endTime: '10:30', title: 'Tips & Variations', description: 'Quick tips and possible variations' },
      { startTime: '10:30', endTime: '11:00', title: 'End Screen', description: 'Subscribe CTA + related video suggestion' },
    ],
    shotList: [
      { type: 'close-up', description: 'Raw spices arranged on dark surface', timing: 'Ingredients' },
      { type: 'close-up', description: 'Oil shimmering in hot pan', timing: 'Cooking' },
      { type: 'overhead', description: 'All ingredients laid out (flat lay)', timing: 'Ingredients' },
      { type: 'close-up', description: 'Spice tempering with mustard seeds popping', timing: 'Cooking' },
      { type: 'medium', description: 'Host stirring with visible steam', timing: 'Cooking' },
      { type: 'close-up', description: 'Gravy bubbling with color change', timing: 'Cooking' },
      { type: 'slow-motion', description: 'Garnish (cilantro/ghee) falling onto dish', timing: 'Plating' },
      { type: 'hero', description: 'Final dish with steam, garnish, and props', timing: 'Plating' },
      { type: 'reaction', description: 'Host first bite with genuine expression', timing: 'Taste Test' },
      { type: 'detail', description: 'Cross-section or inside texture reveal', timing: 'Taste Test' },
    ],
    pinnedComment: '📌 ఈ recipe try చేసారా? Comment లో చెప్పండి! 👇\nDid you try this recipe? Tell me how it turned out!\n\n⏱️ Timestamps:\n0:00 Hook\n0:15 Ingredients\n1:30 Preparation\n3:00 Cooking\n7:00 Plating\n9:00 Taste Test',
    seoDescription: `[DISH NAME] Recipe in Telugu | [DISH NAME తెలుగులో] | Restaurant Style at Home

ఈ video లో [DISH NAME] ఎలా చేయాలో step-by-step చూపిస్తా. Restaurant style secret tips తో ఇంట్లోనే perfect గా!

⏱️ Timestamps:
0:00 Final Dish Reveal
0:15 Ingredients List
1:30 Preparation
3:00 Cooking Process
7:00 Plating & Garnish
9:00 Taste Test
10:00 Tips & Variations

📝 Ingredients:
[LIST YOUR INGREDIENTS HERE]

🔗 Follow Me:
Instagram: [YOUR_INSTAGRAM]
Facebook: [YOUR_FACEBOOK]

#[DishName] #TeluguRecipe #[DishName]Recipe #CookingInTelugu #HomeCooking`,
    endScreenScript: '[Host facing camera] "ఈ recipe నచ్చితే like చేయండి, subscribe చేయండి! 🔔 bell icon కొట్టండి! Next video లో [RELATED_DISH] చేద్దాం — ఆ video ఇక్కడ click చేయండి!" [Points to end screen card]',
  },
  vlog: {
    optimalDuration: '12-20 minutes',
    hookScript: [
      { visual: '[Drone shot or wide establishing shot of location]', dialogue: '"ఈ place చూస్తే మీరు నమ్మరు!"', duration: '0:00-0:05' },
      { visual: '[Quick montage: 3-4 best moments from the vlog]', dialogue: '"ఇవాళ ఏం జరిగిందో చూడండి..."', duration: '0:05-0:10' },
      { visual: '[Host walking toward camera, energetic]', dialogue: '"Namaskaram! ఈ రోజు [LOCATION] కి వచ్చాం — full vlog చూడండి!"', duration: '0:10-0:15' },
    ],
    segments: [
      { startTime: '0:00', endTime: '0:15', title: 'Hook', description: 'Most exciting moment teaser', tips: 'Use your best footage upfront' },
      { startTime: '0:15', endTime: '2:00', title: 'Intro & Context', description: 'Where, why, and what to expect', tips: 'Keep energy high, set expectations' },
      { startTime: '2:00', endTime: '6:00', title: 'Exploration Part 1', description: 'First major location/activity', tips: 'Mix wide shots with personal reactions' },
      { startTime: '6:00', endTime: '10:00', title: 'Exploration Part 2', description: 'Second location or key experience', tips: 'Include local interactions for authenticity' },
      { startTime: '10:00', endTime: '14:00', title: 'Highlight / Climax', description: 'The main event or best experience', tips: 'This is your money shot — capture everything' },
      { startTime: '14:00', endTime: '16:00', title: 'Reflection', description: 'Personal thoughts and takeaways', tips: 'Sit-down or walking talk works well' },
      { startTime: '16:00', endTime: '17:00', title: 'End Screen', description: 'Subscribe CTA + next vlog preview' },
    ],
    shotList: [
      { type: 'drone/wide', description: 'Establishing shot of location from above', timing: 'Intro' },
      { type: 'walking', description: 'Host walking through location, talking to camera', timing: 'Exploration Part 1' },
      { type: 'close-up', description: 'Local food or interesting detail', timing: 'Exploration Part 1' },
      { type: 'reaction', description: 'Genuine surprise or delight moment', timing: 'Exploration Part 2' },
      { type: 'timelapse', description: 'Crowd or sunset timelapse', timing: 'Highlight' },
      { type: 'interaction', description: 'Talking with locals or vendors', timing: 'Exploration Part 2' },
      { type: 'selfie', description: 'Selfie-mode personal moment', timing: 'Reflection' },
      { type: 'b-roll', description: 'Atmospheric shots (lights, textures, movement)', timing: 'Throughout' },
      { type: 'hero', description: 'Best single frame of the trip', timing: 'Highlight' },
    ],
    pinnedComment: '📌 ఈ place కి వెళ్ళారా? మీ experience comment లో share చేయండి! 👇\nHave you been here? Share your experience!\n\n📍 Location: [LOCATION_NAME]\n💰 Budget: [APPROX_BUDGET]',
    seoDescription: `[LOCATION/TOPIC] Vlog in Telugu | [తెలుగులో TOPIC] | Telugu Vlogs

ఈ video లో [LOCATION] explore చేసాం! [1-2 sentence summary of what happens].

⏱️ Timestamps:
0:00 Sneak Peek
0:15 Intro
2:00 [First Activity]
6:00 [Second Activity]
10:00 [Main Highlight]
14:00 My Thoughts
16:00 What's Next

📍 Location: [LOCATION_NAME]
💰 Approx Budget: [BUDGET]
🗓️ Best Time to Visit: [SEASON]

🔗 Follow Me:
Instagram: [YOUR_INSTAGRAM]
Facebook: [YOUR_FACEBOOK]

#TeluguVlog #[Location] #[Topic] #TeluguVlogger #Travel`,
    endScreenScript: '[Host facing camera at scenic spot] "ఈ vlog నచ్చితే like చేయండి! Next week [NEXT_DESTINATION] vlog వస్తుంది — subscribe చేసి bell icon కొట్టండి! ఆ video ఇక్కడ!" [Points to end screen card]',
  },
  tutorial: {
    optimalDuration: '8-15 minutes',
    hookScript: [
      { visual: '[Screen recording or demo of the end result]', dialogue: '"ఈ trick తెలిస్తే 10 minutes లో అయిపోతుంది!"', duration: '0:00-0:05' },
      { visual: '[Split screen: before vs after]', dialogue: '"చాలా మంది ఇక్కడ mistake చేస్తారు — correct way ఇదే!"', duration: '0:05-0:10' },
      { visual: '[Host at desk/setup, confident]', dialogue: '"Step-by-step చూపిస్తా, beginners కూడా easy గా చేయొచ్చు!"', duration: '0:10-0:15' },
    ],
    segments: [
      { startTime: '0:00', endTime: '0:15', title: 'Hook', description: 'Show end result + promise', tips: 'Demonstrate the value immediately' },
      { startTime: '0:15', endTime: '1:30', title: 'What You Need', description: 'Prerequisites and tools', tips: 'Add links in description for tools' },
      { startTime: '1:30', endTime: '4:00', title: 'Step 1-3', description: 'First set of steps', tips: 'Number each step with text overlay' },
      { startTime: '4:00', endTime: '7:00', title: 'Step 4-6', description: 'Middle steps with common mistakes', tips: 'Highlight mistakes with red X overlay' },
      { startTime: '7:00', endTime: '9:00', title: 'Step 7-8', description: 'Final steps and polish', tips: 'Slow down for critical steps' },
      { startTime: '9:00', endTime: '10:00', title: 'Final Result', description: 'Complete demonstration', tips: 'Compare with the hook preview' },
      { startTime: '10:00', endTime: '10:30', title: 'Common Mistakes', description: 'Top 3 mistakes to avoid' },
      { startTime: '10:30', endTime: '11:00', title: 'End Screen', description: 'CTA + related tutorial' },
    ],
    shotList: [
      { type: 'screen-record', description: 'End result demo or before/after', timing: 'Hook' },
      { type: 'overhead', description: 'Tools/materials laid out', timing: 'What You Need' },
      { type: 'close-up', description: 'Hands performing key action', timing: 'Steps' },
      { type: 'screen-record', description: 'Step-by-step with cursor highlights', timing: 'Steps' },
      { type: 'split-screen', description: 'Wrong way vs right way comparison', timing: 'Common Mistakes' },
      { type: 'medium', description: 'Host explaining at whiteboard/screen', timing: 'Steps' },
      { type: 'detail', description: 'Zoomed-in on critical detail', timing: 'Steps' },
      { type: 'hero', description: 'Completed result with annotations', timing: 'Final Result' },
    ],
    pinnedComment: '📌 Doubt ఉంటే comment చేయండి — reply ఇస్తా! 👇\nHave questions? Drop a comment!\n\n⏱️ Timestamps:\n0:00 What We\'re Building\n0:15 Prerequisites\n1:30 Step-by-Step\n9:00 Final Result\n10:00 Common Mistakes',
    seoDescription: `[TOPIC] Tutorial in Telugu | [TOPIC తెలుగులో] | Step by Step Guide

ఈ video లో [TOPIC] ఎలా చేయాలో complete tutorial. Beginners కూడా easy గా follow చేయొచ్చు!

⏱️ Timestamps:
0:00 End Result Preview
0:15 What You Need
1:30 Step 1-3
4:00 Step 4-6
7:00 Step 7-8
9:00 Final Result
10:00 Common Mistakes

🔧 Tools/Resources:
[LIST TOOLS AND LINKS]

🔗 Follow Me:
Instagram: [YOUR_INSTAGRAM]
Facebook: [YOUR_FACEBOOK]

#[Topic]Tutorial #TeluguTutorial #HowTo #LearnInTelugu #StepByStep`,
    endScreenScript: '[Host with completed result visible] "ఇది help అయ్యిందా? Like చేయండి, subscribe చేయండి! Next tutorial లో [RELATED_TOPIC] చేద్దాం — click చేయండి!" [Points to end screen card]',
  },
  review: {
    optimalDuration: '10-15 minutes',
    hookScript: [
      { visual: '[Product hero shot with dramatic lighting]', dialogue: '"ఈ product ₹[PRICE] worth ఉందా? నిజం చెప్తా!"', duration: '0:00-0:05' },
      { visual: '[Quick cuts: unboxing → using → reacting]', dialogue: '"1 week use చేసాక నా honest opinion ఇదే..."', duration: '0:05-0:10' },
      { visual: '[Host holding product, serious expression]', dialogue: '"Buy చేయాలా వద్దా? End వరకు చూడండి!"', duration: '0:10-0:15' },
    ],
    segments: [
      { startTime: '0:00', endTime: '0:15', title: 'Hook', description: 'Verdict tease + product reveal', tips: 'Create curiosity about the final verdict' },
      { startTime: '0:15', endTime: '2:00', title: 'Unboxing', description: 'First impressions and what\'s in the box', tips: 'Show everything that comes in the package' },
      { startTime: '2:00', endTime: '4:00', title: 'Design & Build', description: 'Look, feel, materials, build quality', tips: 'Use macro lens for material details' },
      { startTime: '4:00', endTime: '7:00', title: 'Features & Performance', description: 'Key features tested in real scenarios', tips: 'Show real-world usage, not just specs' },
      { startTime: '7:00', endTime: '9:00', title: 'Pros & Cons', description: 'Honest positives and negatives', tips: 'Use split-screen or list overlay' },
      { startTime: '9:00', endTime: '10:00', title: 'Verdict', description: 'Final recommendation with score', tips: 'Be definitive — avoid wishy-washy conclusions' },
      { startTime: '10:00', endTime: '10:30', title: 'End Screen', description: 'CTA + related review' },
    ],
    shotList: [
      { type: 'hero', description: 'Product on clean background with dramatic lighting', timing: 'Hook' },
      { type: 'unboxing', description: 'Hands opening package, revealing contents', timing: 'Unboxing' },
      { type: 'macro', description: 'Material texture, buttons, ports close-up', timing: 'Design & Build' },
      { type: 'in-use', description: 'Product being used in real scenario', timing: 'Features' },
      { type: 'comparison', description: 'Side-by-side with competitor (if applicable)', timing: 'Features' },
      { type: 'screen-record', description: 'UI/software walkthrough', timing: 'Features' },
      { type: 'reaction', description: 'Host genuine reaction to standout feature', timing: 'Pros & Cons' },
      { type: 'verdict', description: 'Host with product, delivering final opinion', timing: 'Verdict' },
    ],
    pinnedComment: '📌 ఈ product మీ దగ్గర ఉందా? మీ experience share చేయండి! 👇\nOwn this product? Share your experience!\n\n⭐ My Rating: [X]/10\n💰 Price: ₹[PRICE]\n🛒 Buy: [LINK]',
    seoDescription: `[PRODUCT] Review in Telugu | [PRODUCT తెలుగులో] | Honest Opinion

[PRODUCT] 1 week use చేసాక honest review. Worth ఉందా లేదా? Full details ఈ video లో!

⏱️ Timestamps:
0:00 First Impression
0:15 Unboxing
2:00 Design & Build Quality
4:00 Features & Performance
7:00 Pros & Cons
9:00 Final Verdict

📱 Specs:
[KEY SPECS HERE]

💰 Price: ₹[PRICE]
🛒 Buy Here: [AFFILIATE_LINK]

🔗 Follow Me:
Instagram: [YOUR_INSTAGRAM]
Facebook: [YOUR_FACEBOOK]

#[Product]Review #TeluguReview #HonestReview #TechTelugu #Unboxing`,
    endScreenScript: '[Host holding product] "ఈ review helpful అయ్యిందా? Like చేయండి, subscribe చేయండి! [RELATED_PRODUCT] review కూడా చూడండి — ఇక్కడ click చేయండి!" [Points to end screen card]',
  },
  challenge: {
    optimalDuration: '10-18 minutes',
    hookScript: [
      { visual: '[Dramatic shot of challenge setup]', dialogue: '"ఇది చేయగలనా? 😱"', duration: '0:00-0:05' },
      { visual: '[Flash-forward to most intense moment]', dialogue: '"ఏం జరిగిందో చూడండి..."', duration: '0:05-0:10' },
      { visual: '[Host facing camera, pumped up]', dialogue: '"ఈ రోజు [CHALLENGE NAME] try చేస్తున్నా — rules ఇవి!"', duration: '0:10-0:15' },
    ],
    segments: [
      { startTime: '0:00', endTime: '0:15', title: 'Hook', description: 'Most dramatic moment teaser', tips: 'Pick the highest-energy clip' },
      { startTime: '0:15', endTime: '1:30', title: 'Rules & Setup', description: 'Explain the challenge and stakes', tips: 'Make stakes clear — what happens if fail?' },
      { startTime: '1:30', endTime: '5:00', title: 'Challenge Part 1', description: 'First phase of the challenge', tips: 'React genuinely — audience reads fake energy' },
      { startTime: '5:00', endTime: '10:00', title: 'Challenge Part 2', description: 'Escalation and key moments', tips: 'Build tension — music and editing matter' },
      { startTime: '10:00', endTime: '13:00', title: 'Climax', description: 'Final attempt or biggest moment', tips: 'Multiple camera angles if possible' },
      { startTime: '13:00', endTime: '14:00', title: 'Result & Reaction', description: 'Outcome reveal and genuine reaction', tips: 'Let the moment breathe — don\'t rush' },
      { startTime: '14:00', endTime: '15:00', title: 'End Screen', description: 'CTA + dare viewers to try' },
    ],
    shotList: [
      { type: 'wide', description: 'Full challenge setup visible', timing: 'Rules & Setup' },
      { type: 'close-up', description: 'Challenge items or food in detail', timing: 'Rules & Setup' },
      { type: 'reaction', description: 'Host genuine struggle/surprise face', timing: 'Challenge Part 1' },
      { type: 'slow-motion', description: 'Key action moment in slow-mo', timing: 'Challenge Part 2' },
      { type: 'multi-angle', description: 'Same moment from 2 angles', timing: 'Climax' },
      { type: 'close-up', description: 'Sweat, shaking hands, or intensity detail', timing: 'Climax' },
      { type: 'reaction', description: 'Victory/defeat celebration or despair', timing: 'Result' },
      { type: 'selfie', description: 'Post-challenge exhausted selfie shot', timing: 'Result' },
      { type: 'b-roll', description: 'Aftermath — mess, empty plates, etc.', timing: 'Result' },
    ],
    pinnedComment: '📌 ఈ challenge మీరు try చేస్తారా? Comment లో చెప్పండి! 👇\nWould YOU try this challenge? Let me know!\n\n🏆 Result: [WIN/LOSE]\n⏱️ Time: [DURATION]\n\nDare a friend — tag them! 👀',
    seoDescription: `[CHALLENGE NAME] Challenge in Telugu | [తెలుగులో CHALLENGE] | Telugu Challenge

[CHALLENGE NAME] challenge try చేసాను! ఏం జరిగిందో చూడండి 😱

⏱️ Timestamps:
0:00 Sneak Peek
0:15 Rules & Setup
1:30 Challenge Begins
5:00 Things Get Intense
10:00 Final Attempt
13:00 Result Reveal

📋 Challenge Rules:
[LIST RULES]

🔗 Follow Me:
Instagram: [YOUR_INSTAGRAM]
Facebook: [YOUR_FACEBOOK]

#[Challenge]Challenge #TeluguChallenge #ChallengeAccepted #TeluguYouTuber #FunChallenge`,
    endScreenScript: '[Host exhausted but smiling] "ఇది నచ్చితే like చేయండి! మీరు కూడా try చేసి video చేయండి! Next challenge ఇంకా crazy గా ఉంటుంది — subscribe చేయండి!" [Points to end screen card]',
  },
};
