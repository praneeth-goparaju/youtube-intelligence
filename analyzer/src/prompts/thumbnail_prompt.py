"""Thumbnail analysis prompt for Gemini Vision."""

# --- New structured prompts for response_schema mode (batch + improved sync) ---

THUMBNAIL_SYSTEM_INSTRUCTION = (
    "You are an expert YouTube thumbnail analyst. "
    "Analyze thumbnails across all content types — cooking, travel, vlogs, tech, education, "
    "entertainment, news, lifestyle, gaming, health, reviews, and more. "
    "Evaluate scene/setting, composition, visual elements, text overlays, "
    "graphic elements, branding, psychological triggers, and technical quality. "
    "Detect all languages and scripts present (Telugu, Hindi, English, etc.). "
    "If food is visible, analyze it in detail. If not, mark food fields as absent. "
    "Provide accurate, detailed analysis with specific observations."
)

THUMBNAIL_USER_PROMPT = (
    "Analyze this YouTube video thumbnail image.\n\n"
    "Evaluate:\n"
    "1. SCENE - Setting (indoor/outdoor), location type, background, props, content category\n"
    "2. COMPOSITION - Layout type, grid structure, visual balance, focal points, depth of field\n"
    "3. HUMAN PRESENCE - Face detection, expressions, body language, eye contact, gestures\n"
    "4. TEXT ELEMENTS - Text content, languages/scripts detected, styling, purpose, coverage\n"
    "5. COLORS - Dominant colors with hex codes, palette mood, contrast, saturation\n"
    "6. FOOD (if visible) - Dish identification, category, cuisine, presentation, appetite appeal (1-10). Set foodPresent=false if no food.\n"
    "7. GRAPHICS - Arrows, circles, borders, badges, split screens, glow/shadow effects\n"
    "8. BRANDING - Channel logo, name visibility, style consistency\n"
    "9. PSYCHOLOGY - Triggers (curiosity, social proof, urgency, aspiration, relatability, etc.), emotional intensity\n"
    "10. TECHNICAL QUALITY - Resolution, sharpness, lighting, framing\n"
    "11. SCORES - Clickability, clarity, professionalism, uniqueness, appetite appeal, emotional impact (all 1-10)"
)

# --- Original monolithic prompt (kept for backward compatibility with sync mode) ---

THUMBNAIL_ANALYSIS_PROMPT = '''Analyze this YouTube video thumbnail image and return a detailed JSON analysis.

IMPORTANT: Return ONLY valid JSON, no markdown formatting or explanation text.

Analyze these aspects:

1. SCENE - Setting (indoor/outdoor), location type, background elements, visible props, content category
2. COMPOSITION - Layout, visual balance, focal points, depth of field
3. HUMAN PRESENCE - Face detection, expressions, body language, eye contact, gestures
4. TEXT ELEMENTS - Any text, language/scripts (Telugu, Hindi, English, etc.), readability, colors
5. COLORS - Dominant colors with hex, palette mood, contrast, saturation
6. FOOD (if visible, otherwise set foodPresent=false) - Dish identification, presentation, appetite appeal
7. GRAPHICS - Arrows, circles, borders, badges, split screens, glow/shadow effects
8. BRANDING - Logo, channel name visibility, style consistency
9. PSYCHOLOGICAL TRIGGERS - Curiosity, social proof, urgency, aspiration, relatability, etc.
10. TECHNICAL QUALITY - Resolution, sharpness, lighting, framing

Return this exact JSON structure:

{
  "scene": {
    "settingType": "indoor|outdoor|studio|mixed",
    "location": "kitchen|restaurant|street|market|nature|city|home|studio|vehicle|landmark|office|gym|temple|farm|beach|hotel|other",
    "backgroundElements": ["mountains", "kitchen-counter", "skyline"],
    "timeOfDay": "day|night|golden-hour|not-visible",
    "props": ["camera", "phone", "cooking-utensil", "backpack"],
    "thumbnailStyle": "photographic|graphic-design|screenshot|mixed-media|illustration|cinematic",
    "contentCategory": "cooking|travel|vlog|tech|education|entertainment|news|lifestyle|review|gaming|health|agriculture|devotional|interview|food-review|street-food|fitness|comedy|music|other"
  },
  "composition": {
    "layoutType": "split-screen|single-focus|collage|text-heavy|minimal",
    "gridStructure": "rule-of-thirds|centered|asymmetric|golden-ratio",
    "visualBalance": "balanced|left-heavy|right-heavy|top-heavy|bottom-heavy",
    "negativeSpace": "minimal|moderate|heavy",
    "complexity": "simple|medium|complex|cluttered",
    "focalPoint": ["person-face", "food-dish", "text-overlay", "product", "landscape"],
    "depthOfField": "shallow|deep|flat"
  },
  "humanPresence": {
    "facePresent": true/false,
    "faceCount": number,
    "facePosition": "center|left|right|top|bottom|top-left|top-right|bottom-left|bottom-right|none",
    "faceSize": "small|medium|large|dominant|none",
    "faceCoverage": percentage or 0,
    "expression": "happy|surprised|shocked|curious|neutral|excited|disgusted|thinking|sad|angry|proud|none",
    "expressionIntensity": "subtle|moderate|high|extreme|none",
    "mouthOpen": true/false,
    "eyeContact": true/false,
    "eyebrowsRaised": true/false,
    "bodyVisible": true/false,
    "bodyPortion": "face-only|upper|half|full|none",
    "handVisible": true/false,
    "handGesture": "none|thumbs-up|pointing|holding-item|peace|ok|namaste|waving",
    "pointingAt": "food|text|product|person|camera|off-screen|nothing|none",
    "lookingDirection": "camera|left|right|down|up|at-food|at-object|at-scenery|none"
  },
  "textElements": {
    "hasText": true/false,
    "textCount": number,
    "primaryText": {
      "content": "text content or none",
      "language": "english|telugu|hindi|other|none",
      "script": "latin|telugu|devanagari|none",
      "position": "top|bottom|center|left|right|top-left|top-right|bottom-left|bottom-right|none",
      "size": "small|medium|large|none",
      "color": "white|black|red|yellow|green|blue|orange|pink|purple|gold|brown|none",
      "backgroundColor": "white|black|red|yellow|green|blue|orange|pink|purple|gold|brown|none|transparent",
      "hasOutline": true/false,
      "fontStyle": "bold-sans|script|handwritten|decorative|none",
      "allCaps": true/false,
      "readable": true/false
    },
    "languages": ["list of languages detected"],
    "hasTeluguScript": true/false,
    "hasEnglishText": true/false,
    "hasNumbers": true/false,
    "numberValue": "value or none",
    "numberType": "view-count|list-number|price|time|quantity|none",
    "hasEmoji": true/false,
    "emojiList": ["list of emojis"],
    "textPurpose": ["title", "social-proof", "cta", "brand", "dish-name", "benefit", "price", "location"],
    "totalTextCoverage": percentage
  },
  "colors": {
    "dominantColors": [
      {"hex": "#XXXXXX", "name": "color name", "percentage": number}
    ],
    "palette": "warm|cool|neutral|mixed",
    "mood": "energetic|calm|appetizing|professional|playful|dramatic|mysterious|warm|luxurious|adventurous|informative",
    "contrast": "low|medium|high",
    "saturation": "desaturated|medium|high|vivid",
    "brightness": "dark|medium|bright",
    "backgroundType": "solid|gradient|image|blurred|transparent",
    "backgroundColor": "white|black|red|yellow|green|blue|orange|pink|purple|gold|brown|grey|multi-color",
    "colorHarmony": "monochromatic|complementary|triadic|analogous",
    "contrastWithYouTube": true/false
  },
  "food": {
    "foodPresent": true/false,
    "foodCount": number,
    "mainDish": "dish name or none",
    "dishCategory": "rice|curry|snack|dessert|bread|indo-chinese|breakfast|beverage|biryani|chutney|pickle|sweet|other|none",
    "cuisineType": "south-indian|north-indian|hyderabadi|andhra|telangana|indo-chinese|street-food|continental|fusion|other|none",
    "presentation": "close-up|plated|cooking-process|ingredients|before-after|none",
    "platingStyle": "rustic|elegant|home-style|restaurant|none",
    "container": "plate|bowl|pot|pan|banana-leaf|hand|glass|tray|other|none",
    "steam": true/false,
    "sizzle": true/false,
    "garnished": true/false,
    "garnishes": ["list"],
    "freshness": "low|medium|high",
    "appetiteAppeal": 1-10,
    "colorVibrancy": "low|medium|high",
    "textureVisible": true/false,
    "portionSize": "small|medium|generous|huge",
    "cookingStage": "raw|in-progress|finished"
  },
  "graphics": {
    "hasArrows": true/false,
    "arrowCount": number,
    "arrowColor": "white|black|red|yellow|green|blue|orange|pink|purple|gold|none",
    "arrowStyle": "straight|curved|hand-drawn|none",
    "arrowPointingTo": "food|text|person|product|price|comparison-item|off-screen|none",
    "hasCircles": true/false,
    "hasHighlights": true/false,
    "hasBorder": true/false,
    "borderColor": "white|black|red|yellow|green|blue|orange|pink|purple|gold|none",
    "borderStyle": "solid|dashed|glow|shadow|none",
    "hasBadge": true/false,
    "badgeType": "new|viral|view-count|trending|episode-number|none",
    "badgeText": "text or none",
    "hasLogo": true/false,
    "logoPosition": "top-left|top-right|bottom-left|bottom-right|center|none",
    "hasBeforeAfter": true/false,
    "hasVsComparison": true/false,
    "hasSplitScreen": true/false,
    "hasGlow": true/false,
    "hasShadow": true/false
  },
  "branding": {
    "channelLogoVisible": true/false,
    "logoPlacement": "top-left|top-right|bottom-left|bottom-right|center|none",
    "channelNameVisible": true/false,
    "recognizableStyle": true/false,
    "professionalQuality": "amateur|medium|high|professional"
  },
  "psychology": {
    "curiosityGap": true/false,
    "socialProof": true/false,
    "urgency": true/false,
    "scarcity": true/false,
    "authority": true/false,
    "controversy": true/false,
    "transformation": true/false,
    "luxury": true/false,
    "nostalgia": true/false,
    "shock": true/false,
    "humor": true/false,
    "fear": true/false,
    "aspiration": true/false,
    "relatability": true/false,
    "primaryEmotion": "curiosity|excitement|appetite|nostalgia|amusement|awe|inspiration|fear|anger|surprise|wanderlust|satisfaction|empathy|pride|disgust|none",
    "emotionalIntensity": "low|moderate|high",
    "clickMotivation": ["reasons why someone would click"],
    "targetAudience": ["home-cooks", "health-conscious", "young-adults", "travelers", "tech-enthusiasts"]
  },
  "technicalQuality": {
    "resolution": "low|medium|high",
    "sharpness": "blurry|acceptable|sharp",
    "lighting": "poor|natural|professional|studio",
    "noiseLevel": "high|medium|low",
    "framing": "poor|acceptable|good|excellent",
    "exposure": "underexposed|correct|overexposed"
  }
}'''
