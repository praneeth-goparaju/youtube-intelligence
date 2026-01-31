"""Thumbnail analysis prompt for Gemini Vision."""

# --- New structured prompts for response_schema mode (batch + improved sync) ---

THUMBNAIL_SYSTEM_INSTRUCTION = (
    "You are an expert YouTube thumbnail analyst specializing in Telugu cooking and food channels. "
    "Analyze thumbnails for composition, visual elements, food presentation, text overlays, "
    "graphic elements, branding, psychological triggers, and technical quality. "
    "Provide accurate, detailed analysis with specific observations."
)

THUMBNAIL_USER_PROMPT = (
    "Analyze this YouTube video thumbnail image.\n\n"
    "Evaluate:\n"
    "1. COMPOSITION - Layout type, grid structure, visual balance, focal point, depth of field\n"
    "2. HUMAN PRESENCE - Face detection, expressions, body language, eye contact, gestures\n"
    "3. TEXT ELEMENTS - Text content, language/script, styling, purpose, coverage\n"
    "4. COLORS - Dominant colors with hex codes, palette mood, contrast, saturation\n"
    "5. FOOD - Dish identification, category, presentation style, appetite appeal (1-10)\n"
    "6. GRAPHICS - Arrows, circles, borders, badges, split screens, visual effects\n"
    "7. BRANDING - Channel logo, name visibility, style consistency\n"
    "8. PSYCHOLOGY - Triggers (curiosity, social proof, urgency, etc.), emotional intensity\n"
    "9. TECHNICAL QUALITY - Resolution, sharpness, lighting, framing\n"
    "10. SCORES - Clickability, clarity, professionalism, uniqueness, emotional impact (all 1-10)"
)

# --- Original monolithic prompt (kept for backward compatibility with sync mode) ---

THUMBNAIL_ANALYSIS_PROMPT = '''Analyze this YouTube video thumbnail image and return a detailed JSON analysis.

IMPORTANT: Return ONLY valid JSON, no markdown formatting or explanation text.

Analyze these aspects:

1. COMPOSITION - Layout, visual balance, focal points
2. HUMAN PRESENCE - Face detection, expressions, body language
3. TEXT ELEMENTS - Any text, language, readability, colors
4. COLORS - Dominant colors, palette mood, contrast
5. FOOD (if cooking/food content) - Dish presentation, appetite appeal
6. GRAPHICS - Arrows, borders, badges, icons
7. BRANDING - Logo, channel consistency
8. PSYCHOLOGICAL TRIGGERS - Curiosity, social proof, urgency
9. TECHNICAL QUALITY - Resolution, lighting, sharpness

Return this exact JSON structure:

{
  "composition": {
    "layoutType": "split-screen|single-focus|collage|text-heavy|minimal",
    "gridStructure": "rule-of-thirds|centered|asymmetric|golden-ratio",
    "visualBalance": "balanced|left-heavy|right-heavy|top-heavy|bottom-heavy",
    "negativeSpace": "minimal|moderate|heavy",
    "complexity": "simple|medium|complex|cluttered",
    "focalPoint": "description of main focal point",
    "depthOfField": "shallow|deep|flat"
  },
  "humanPresence": {
    "facePresent": true/false,
    "faceCount": number,
    "facePosition": "position description or null",
    "faceSize": "small|medium|large|dominant|null",
    "faceCoverage": percentage or null,
    "expression": "happy|surprised|shocked|curious|neutral|excited|disgusted|thinking|null",
    "expressionIntensity": "subtle|moderate|high|extreme|null",
    "mouthOpen": true/false/null,
    "eyeContact": true/false/null,
    "eyebrowsRaised": true/false/null,
    "bodyVisible": true/false,
    "bodyPortion": "face-only|upper|half|full|null",
    "handVisible": true/false,
    "handGesture": "none|thumbs-up|pointing|holding-item|peace|ok|null",
    "pointingAt": "target or null",
    "lookingDirection": "camera|left|right|down|at-food|null"
  },
  "textElements": {
    "hasText": true/false,
    "textCount": number,
    "primaryText": {
      "content": "text content or null",
      "language": "english|telugu|hindi|other|null",
      "script": "latin|telugu|devanagari|null",
      "position": "position or null",
      "size": "small|medium|large|null",
      "color": "hex color or null",
      "backgroundColor": "hex color or null",
      "hasOutline": true/false/null,
      "fontStyle": "bold-sans|script|handwritten|decorative|null",
      "allCaps": true/false/null,
      "readable": true/false/null
    },
    "languages": ["list of languages detected"],
    "hasTeluguScript": true/false,
    "hasEnglishText": true/false,
    "hasNumbers": true/false,
    "numberValue": "value or null",
    "numberType": "view-count|list-number|price|time|quantity|null",
    "hasEmoji": true/false,
    "emojiList": ["list of emojis"],
    "textPurpose": ["title", "social-proof", "cta", "brand", "dish-name", "benefit"],
    "totalTextCoverage": percentage
  },
  "colors": {
    "dominantColors": [
      {"hex": "#XXXXXX", "name": "color name", "percentage": number}
    ],
    "palette": "warm|cool|neutral|mixed",
    "mood": "energetic|calm|appetizing|professional|playful",
    "contrast": "low|medium|high",
    "saturation": "desaturated|medium|high|vivid",
    "brightness": "dark|medium|bright",
    "backgroundType": "solid|gradient|image|blurred|transparent",
    "backgroundColor": "hex color",
    "colorHarmony": "monochromatic|complementary|triadic|analogous",
    "contrastWithYouTube": true/false
  },
  "food": {
    "foodPresent": true/false,
    "foodCount": number,
    "mainDish": "dish name or null",
    "dishCategory": "rice|curry|snack|dessert|bread|indo-chinese|breakfast|null",
    "cuisineType": "cuisine description or null",
    "presentation": "close-up|plated|cooking-process|ingredients|before-after|null",
    "platingStyle": "rustic|elegant|home-style|restaurant|null",
    "container": "plate|bowl|pot|pan|banana-leaf|hand|null",
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
    "arrowColor": "hex or null",
    "arrowStyle": "straight|curved|hand-drawn|null",
    "arrowPointingTo": "target or null",
    "hasCircles": true/false,
    "hasHighlights": true/false,
    "hasBorder": true/false,
    "borderColor": "hex or null",
    "borderStyle": "solid|dashed|glow|shadow|null",
    "hasBadge": true/false,
    "badgeType": "new|viral|view-count|trending|episode-number|null",
    "badgeText": "text or null",
    "hasLogo": true/false,
    "logoPosition": "position or null",
    "hasBeforeAfter": true/false,
    "hasVsComparison": true/false,
    "hasSplitScreen": true/false,
    "hasGlow": true/false,
    "hasShadow": true/false
  },
  "branding": {
    "channelLogoVisible": true/false,
    "logoPlacement": "position or null",
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
    "primaryEmotion": "curiosity|excitement|appetite|nostalgia|amusement|null",
    "emotionalIntensity": "low|moderate|high",
    "clickMotivation": ["reasons why someone would click"],
    "targetAudience": "description"
  },
  "technicalQuality": {
    "resolution": "low|medium|high",
    "sharpness": "blurry|acceptable|sharp",
    "lighting": "poor|natural|professional|studio",
    "noiseLevel": "high|medium|low",
    "framing": "poor|acceptable|good|excellent",
    "exposure": "underexposed|correct|overexposed"
  },
  "scores": {
    "clickability": 1-10,
    "clarity": 1-10,
    "professionalism": 1-10,
    "uniqueness": 1-10,
    "appetiteAppeal": 1-10,
    "emotionalImpact": 1-10,
    "predictedCTR": "below-average|average|above-average|exceptional",
    "improvementAreas": ["list of suggestions"]
  }
}'''
