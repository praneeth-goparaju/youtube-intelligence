"""Combined title + description analysis prompt for Gemini.

Merges title and description analysis into a single API call.
Gemini handles only semantic fields (pattern recognition, language understanding,
hooks, keywords, content signals, recipe detection, SEO assessment).
Deterministic fields (formatting, counts, links, timestamps, hashtags,
monetization) are computed locally by local_text_features.py.
"""

# --- New structured prompts for response_schema mode (batch + improved sync) ---

TITLE_DESC_SYSTEM_INSTRUCTION = (
    "You are an expert YouTube title and description analyst. "
    "Analyze titles across all content types — cooking, travel, vlogs, tech, education, "
    "entertainment, news, lifestyle, gaming, health, reviews, and more. "
    "Focus on SEMANTIC analysis: language understanding, transliteration detection, "
    "code-switching patterns, power words, emotional triggers, keyword extraction, "
    "niche classification, and content type detection. "
    "The description provides context that should inform title analysis "
    "(e.g., ingredient lists confirm isRecipe, location mentions confirm travel content). "
    "Do NOT analyze formatting, character counts, emoji presence, link patterns, "
    "timestamps, hashtags, or monetization signals — those are handled separately."
)

TITLE_DESC_USER_PROMPT = (
    "Analyze this YouTube video title AND description together.\n\n"
    "TITLE ANALYSIS (semantic fields only):\n"
    "1. STRUCTURE - Pattern type (e.g., 'topic | translation | modifier'), patternType\n"
    "2. LANGUAGE - Transliteration detection, code-switching style, Telugu/English word lists "
    "(comma-separated), readability. Do NOT return scripts, languages, or ratios.\n"
    "3. HOOKS & TRIGGERS - Question type/word, number context, power words (comma-separated), "
    "emotional triggers, hook strength. Do NOT return isQuestion, hasNumber, or numbers.\n"
    "4. KEYWORDS - Primary/secondary keywords (comma-separated), search intent, niche/sub-niche, "
    "SEO optimization\n"
    "5. CONTENT SIGNALS - Content type (recipe/tutorial/review/travel/vlog/interview/educational/music/etc), "
    "series detection, collaborations, brand mentions\n\n"
    "DESCRIPTION ANALYSIS (semantic fields only):\n"
    "1. Structure quality (wellOrganized, firstLineHook)\n"
    "2. Recipe content detection (ingredients, instructions, cooking time)\n"
    "3. Comment question (the specific question asked to drive comments)\n"
    "4. SEO (keyword placement, density, internal linking quality)\n\n"
    "Do NOT analyze: formatting, character counts, emoji lists, link patterns, "
    "timestamps, hashtags, CTAs, or monetization signals."
)

# --- Original monolithic prompt (kept for backward compatibility with sync mode) ---

TITLE_DESCRIPTION_ANALYSIS_PROMPT = '''Analyze this YouTube video title AND description together, and return a detailed JSON analysis.

IMPORTANT: Return ONLY valid JSON, no markdown formatting or explanation text.

The description provides additional context that should inform your title analysis (e.g., ingredient lists confirm a recipe, location mentions confirm travel content).

Focus on SEMANTIC analysis only. Do NOT analyze: formatting (capitalization, emojis, brackets, special chars), character/word counts, link patterns, timestamps, hashtags, CTAs (subscribe/like/comment), or monetization signals — those are computed separately.

For word lists (powerWords, transliteratedWords, etc.), return as comma-separated strings, NOT arrays.

## TITLE ANALYSIS

Analyze the title for:
1. STRUCTURE - Pattern type only (e.g., "topic | translation | modifier")
2. LANGUAGE - Code-switching, transliteration, Telugu/English word lists and counts, readability
3. HOOKS & TRIGGERS - Question type/word, number context, power words, emotional triggers, hook strength
4. KEYWORDS - Primary/secondary keywords, search intent, niche/sub-niche, SEO
5. CONTENT SIGNALS - Content type, format indicators (use description to confirm/enrich)

## DESCRIPTION ANALYSIS

Analyze the description for (semantic fields only):
1. STRUCTURE QUALITY - Is it well organized? Does the first line hook the reader?
2. RECIPE CONTENT - Ingredients, instructions, cooking time (if applicable)
3. COMMENT QUESTION - The specific question asked to drive comments
4. SEO - Keyword placement, density, internal linking quality

Return this exact JSON structure:

{
  "structure": {
    "pattern": "pattern description like 'topic | translation | modifier'",
    "patternType": "single|segmented|question|list|statement"
  },
  "language": {
    "hasTransliteration": true/false,
    "transliteratedWords": "comma-separated list",
    "codeSwitch": true/false,
    "codeSwitchStyle": "translation|mixed|parallel|none",
    "teluguWords": "comma-separated Telugu words",
    "teluguWordCount": number,
    "teluguReadability": "easy|medium|difficult",
    "englishWords": "comma-separated English words",
    "englishWordCount": number
  },
  "hooks": {
    "questionType": "how|why|what|which|can|should|none",
    "questionWord": "word or none",
    "numberContext": "list|time|money|quantity|ranking|year|none",
    "hasPowerWord": true/false,
    "powerWords": "comma-separated power words",
    "powerWordCategories": "comma-separated from: exclusivity, urgency, curiosity, quality, emotion",
    "triggers": {
      "curiosityGap": true/false,
      "socialProof": true/false,
      "urgency": true/false,
      "exclusivity": true/false,
      "controversy": true/false,
      "transformation": true/false,
      "challenge": true/false,
      "comparison": true/false,
      "personal": true/false,
      "storytelling": true/false
    },
    "hookStrength": "weak|moderate|strong|viral",
    "primaryHook": "description of main hook"
  },
  "keywords": {
    "primaryKeyword": "main keyword",
    "primaryKeywordPosition": "start|middle|end",
    "secondaryKeywords": "comma-separated keywords",
    "searchIntent": "how-to|review|comparison|information|entertainment|travel|shopping|news",
    "niche": "cooking|travel|entertainment|tech|vlog|education|news|lifestyle|gaming|health|agriculture|devotional|food-review|street-food|fitness|comedy|music|other",
    "subNiche": "description",
    "microNiche": "description or none",
    "evergreen": true/false,
    "seasonal": true/false,
    "trendingPotential": "low|medium|high",
    "keywordCompetition": "low|medium|high|extreme",
    "seoOptimized": true/false,
    "keywordInFirst3Words": true/false,
    "naturalLanguage": true/false
  },
  "contentSignals": {
    "contentType": "recipe|tutorial|review|vlog|challenge|reaction|comparison|list|storytime|unboxing|explainer|news|travel|interview|comedy|music|other",
    "isRecipe": true/false,
    "isTutorial": true/false,
    "isReview": true/false,
    "isVlog": true/false,
    "isChallenge": true/false,
    "isReaction": true/false,
    "isComparison": true/false,
    "isList": true/false,
    "isStorytime": true/false,
    "isTravel": true/false,
    "isInterview": true/false,
    "isEducational": true/false,
    "isMusicRelated": true/false,
    "isPartOfSeries": true/false,
    "seriesName": "name or none",
    "episodeNumber": "number or none",
    "hasCollaboration": true/false,
    "collaboratorMentioned": "name or none",
    "hasBrandMention": true/false,
    "brandMentioned": "name or none",
    "brandPosition": "start|middle|end|none"
  },
  "descriptionAnalysis": {
    "structure": {
      "wellOrganized": true/false,
      "firstLineHook": true/false
    },
    "recipeContent": {
      "hasIngredients": true/false,
      "ingredientCount": number,
      "hasInstructions": true/false,
      "instructionSteps": number,
      "hasCookingTime": true/false
    },
    "ctas": {
      "commentQuestion": "question text or none"
    },
    "seo": {
      "keywordInFirst100Chars": true/false,
      "keywordDensity": decimal,
      "internalLinking": "none|minimal|good|excellent"
    }
  }
}'''
