"""Combined title + description analysis prompt for Gemini.

Merges title and description analysis into a single API call.
Title analysis retains all fields. Description analysis is lean (~20 fields).
The description context helps Gemini make better niche/content-type decisions.
"""

# --- New structured prompts for response_schema mode (batch + improved sync) ---

TITLE_DESC_SYSTEM_INSTRUCTION = (
    "You are an expert YouTube title and description analyst specializing in Telugu content. "
    "The description provides context that should inform title analysis "
    "(e.g., ingredient lists confirm isRecipe, timestamps reveal structure). "
    "Analyze both together in a single pass for accurate niche and content-type detection."
)

TITLE_DESC_USER_PROMPT = (
    "Analyze this YouTube video title AND description together.\n\n"
    "TITLE ANALYSIS:\n"
    "1. STRUCTURE - Pattern, segments, separators, character/word counts by language\n"
    "2. LANGUAGE - Telugu/English mix, code-switching style, transliteration, script detection\n"
    "3. HOOKS & TRIGGERS - Power words, emotional triggers, question hooks, hook strength\n"
    "4. KEYWORDS - Primary/secondary keywords, search intent, niche/sub-niche, SEO optimization\n"
    "5. FORMATTING - Capitalization, emojis, brackets, special chars, hashtags\n"
    "6. CONTENT SIGNALS - Content type (recipe/tutorial/review/etc), series detection, collaborations\n"
    "7. TELUGU-SPECIFIC - Register, dialect hints, honorifics, food term accuracy\n"
    "8. COMPETITIVE - Uniqueness score (1-10), niche pattern adherence, standout factors\n"
    "9. SCORES - SEO, clickability, clarity, emotional, uniqueness, length, overall (all 1-10)\n\n"
    "DESCRIPTION ANALYSIS (lean):\n"
    "1. Structure, timestamps, recipe content, hashtags, CTAs, SEO keyword density"
)

# --- Original monolithic prompt (kept for backward compatibility with sync mode) ---

TITLE_DESCRIPTION_ANALYSIS_PROMPT = '''Analyze this YouTube video title AND description together, and return a detailed JSON analysis.

IMPORTANT: Return ONLY valid JSON, no markdown formatting or explanation text.

This is for a Telugu YouTube channel. The description provides additional context that should inform your title analysis (e.g., ingredient lists confirm a recipe, timestamps reveal structure).

## TITLE ANALYSIS

Analyze the title for:
1. STRUCTURE - Pattern, segments, separators, length
2. LANGUAGE - Telugu/English mix, code-switching, scripts
3. HOOKS & TRIGGERS - Power words, emotional triggers, question hooks
4. KEYWORDS - Primary/secondary keywords, search intent, SEO
5. FORMATTING - Capitalization, emojis, special characters
6. CONTENT SIGNALS - Content type, format indicators (use description to confirm/enrich)
7. TELUGU-SPECIFIC - Register, dialect, food terms
8. COMPETITIVE - Uniqueness, differentiation

## DESCRIPTION ANALYSIS

Analyze the description for (lean analysis only):
1. STRUCTURE - Length, organization, first line hook
2. TIMESTAMPS - Chapter markers
3. RECIPE CONTENT - Ingredients, instructions, cooking time (if applicable)
4. HASHTAGS - Count and position
5. CALL TO ACTIONS - Subscribe, like, comment prompts
6. SEO - Keyword placement, density, internal linking

Return this exact JSON structure:

{
  "structure": {
    "pattern": "pattern description like 'dish-name | translation | modifier'",
    "patternType": "single|segmented|question|list|statement",
    "segments": [
      {"text": "segment text", "type": "dish-name|translation|modifier|channel-name|hook", "language": "english|telugu"}
    ],
    "segmentCount": number,
    "separator": "separator character or null",
    "separatorConsistent": true/false,
    "characterCount": number,
    "characterCountNoSpaces": number,
    "wordCount": number,
    "teluguCharacterCount": number,
    "englishCharacterCount": number
  },
  "language": {
    "languages": ["english", "telugu"],
    "primaryLanguage": "english|telugu",
    "secondaryLanguage": "english|telugu|null",
    "scripts": ["latin", "telugu"],
    "hasTeluguScript": true/false,
    "hasLatinScript": true/false,
    "hasTransliteration": true/false,
    "transliteratedWords": ["list"],
    "codeSwitch": true/false,
    "codeSwitchStyle": "translation|mixed|parallel|null",
    "teluguWords": ["list of Telugu words"],
    "teluguWordCount": number,
    "teluguReadability": "easy|medium|difficult",
    "englishWords": ["list of English words"],
    "englishWordCount": number,
    "teluguRatio": decimal 0-1,
    "englishRatio": decimal 0-1
  },
  "hooks": {
    "isQuestion": true/false,
    "questionType": "how|why|what|which|can|should|null",
    "questionWord": "word or null",
    "hasNumber": true/false,
    "numbers": ["list of numbers"],
    "numberContext": "list|time|money|quantity|ranking|year|null",
    "hasPowerWord": true/false,
    "powerWords": ["list"],
    "powerWordCategories": ["exclusivity", "urgency", "curiosity", "quality", "emotion"],
    "exclusivityWords": ["list"],
    "urgencyWords": ["list"],
    "curiosityWords": ["list"],
    "qualityWords": ["list"],
    "emotionWords": ["list"],
    "teluguPowerWords": ["list"],
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
    "secondaryKeywords": ["list"],
    "allKeywords": [
      {"word": "keyword", "type": "dish|recipe|modifier|brand", "searchVolume": "low|medium|high"}
    ],
    "searchIntent": "how-to|review|comparison|information|entertainment",
    "niche": "cooking|travel|entertainment|tech|vlog|etc",
    "subNiche": "description",
    "microNiche": "description or null",
    "evergreen": true/false,
    "seasonal": true/false,
    "trendingPotential": "low|medium|high",
    "keywordCompetition": "low|medium|high|extreme",
    "seoOptimized": true/false,
    "keywordInFirst3Words": true/false,
    "naturalLanguage": true/false
  },
  "formatting": {
    "capitalization": "lowercase|title-case|all-caps|mixed",
    "allCaps": true/false,
    "partialCaps": true/false,
    "capsWords": ["list of all-caps words"],
    "hasEmoji": true/false,
    "emojiList": ["list"],
    "emojiPositions": ["start", "middle", "end"],
    "hasBrackets": true/false,
    "bracketType": "round|square|curly|null",
    "bracketContent": "content or null",
    "hasSpecialChars": true/false,
    "specialChars": ["list"],
    "hasYear": true/false,
    "year": "year or null",
    "hasHashtag": true/false,
    "hashtags": ["list"],
    "endsWithPunctuation": true/false,
    "punctuationType": "exclamation|question|period|null",
    "hasExclamation": true/false,
    "hasQuestion": true/false
  },
  "contentSignals": {
    "contentType": "recipe|tutorial|review|vlog|challenge|reaction|comparison|list|storytime|unboxing|explainer|news",
    "isRecipe": true/false,
    "isTutorial": true/false,
    "isReview": true/false,
    "isVlog": true/false,
    "isChallenge": true/false,
    "isReaction": true/false,
    "isComparison": true/false,
    "isList": true/false,
    "isStorytime": true/false,
    "isPartOfSeries": true/false,
    "seriesName": "name or null",
    "episodeNumber": "number or null",
    "hasCollaboration": true/false,
    "collaboratorMentioned": "name or null",
    "hasBrandMention": true/false,
    "brandMentioned": "name or null",
    "brandPosition": "start|middle|end|null"
  },
  "teluguAnalysis": {
    "formalRegister": true/false,
    "respectLevel": "casual|neutral|respectful",
    "dialectHints": "andhra|telangana|rayalaseema|neutral",
    "hasHonorifics": true/false,
    "honorificsUsed": ["list"],
    "hasColloquialisms": true/false,
    "colloquialWords": ["list"],
    "foodTermsAccurate": true/false,
    "traditionalTerms": ["list"],
    "modernTerms": ["list"],
    "targetAudienceAge": "young|middle|older|all",
    "urbanVsRural": "urban|rural|both"
  },
  "competitive": {
    "uniquenessScore": 1-10,
    "followsNichePattern": true/false,
    "deviatesFrom": ["list of norm deviations"],
    "uniqueElements": ["list"],
    "missingCommonElements": ["list"],
    "standoutFactor": "description"
  },
  "scores": {
    "seoScore": 1-10,
    "clickabilityScore": 1-10,
    "clarityScore": 1-10,
    "emotionalScore": 1-10,
    "uniquenessScore": 1-10,
    "lengthScore": 1-10,
    "clickbaitLevel": 1-10,
    "clickbaitElements": ["list"],
    "overallScore": 1-10,
    "predictedPerformance": "below-average|average|above-average|exceptional",
    "suggestions": ["list of improvement suggestions"]
  },
  "descriptionAnalysis": {
    "structure": {
      "length": number,
      "lineCount": number,
      "wellOrganized": true/false,
      "firstLineHook": true/false
    },
    "timestamps": {
      "hasTimestamps": true/false,
      "timestampCount": number
    },
    "recipeContent": {
      "hasIngredients": true/false,
      "ingredientCount": number,
      "hasInstructions": true/false,
      "instructionSteps": number,
      "hasCookingTime": true/false
    },
    "hashtags": {
      "count": number,
      "position": "start|middle|end|throughout|none"
    },
    "ctas": {
      "hasSubscribeCTA": true/false,
      "hasLikeCTA": true/false,
      "hasCommentCTA": true/false,
      "commentQuestion": "question text or null"
    },
    "seo": {
      "keywordInFirst100Chars": true/false,
      "keywordDensity": decimal,
      "internalLinking": "none|minimal|good|excellent"
    }
  }
}'''
