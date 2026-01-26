"""Tags analysis prompt for Gemini."""

TAGS_ANALYSIS_PROMPT = '''Analyze these YouTube video tags and return a detailed JSON analysis.

IMPORTANT: Return ONLY valid JSON, no markdown formatting or explanation text.

This is for a Telugu YouTube channel. Analyze:

1. CATEGORIZATION - Brand, primary, modifier, language, Telugu tags
2. STRATEGY - Diversity, coverage, optimization
3. SEARCH ANALYSIS - Volume estimates, intent coverage
4. COMPETITIVE - Common tags, unique tags, missing opportunities

Tags to analyze:

{tags}

Return this exact JSON structure:

{
  "rawTags": ["list of all tags"],
  "tagCount": number,
  "totalCharacters": number,
  "characterLimit": 500,
  "utilizationPercent": decimal,
  "categories": {
    "brandTags": [
      {"tag": "tag text", "purpose": "channel-discovery|series-discovery"}
    ],
    "brandTagCount": number,
    "primaryTags": [
      {"tag": "tag text", "searchVolume": "low|medium|high|very-high", "competition": "low|medium|high"}
    ],
    "primaryTagCount": number,
    "modifierTags": [
      {"tag": "tag text", "modifier": "quality|difficulty|authenticity|style"}
    ],
    "modifierTagCount": number,
    "ingredientTags": [
      {"tag": "tag text", "ingredient": "ingredient type"}
    ],
    "ingredientTagCount": number,
    "languageTags": [
      {"tag": "tag text", "language": "telugu|english|hindi"}
    ],
    "languageTagCount": number,
    "teluguScriptTags": [
      {"tag": "tag in Telugu", "meaning": "meaning in English"}
    ],
    "teluguTagCount": number,
    "genericTags": [
      {"tag": "tag text", "specificity": "low|medium|high"}
    ],
    "genericTagCount": number,
    "longTailTags": [
      {"tag": "tag text", "words": number, "intent": "tutorial|home-cooking|etc"}
    ],
    "longTailTagCount": number,
    "misspellingTags": ["list of intentional misspellings"],
    "misspellingTagCount": number
  },
  "strategy": {
    "diversityScore": 1-10,
    "hasChannelName": true/false,
    "hasMainKeyword": true/false,
    "hasTeluguTags": true/false,
    "hasLongTail": true/false,
    "hasModifiers": true/false,
    "includesMisspellings": true/false,
    "includesCompetitorNames": true/false,
    "includesTrendingTags": true/false,
    "broadVsSpecific": {
      "broadPercent": number,
      "specificPercent": number,
      "longTailPercent": number
    },
    "languageBalance": {
      "englishPercent": number,
      "teluguPercent": number
    },
    "wellOptimized": true/false,
    "issues": ["list of issues found"]
  },
  "searchAnalysis": {
    "highVolumeCount": number,
    "mediumVolumeCount": number,
    "lowVolumeCount": number,
    "howToIntent": true/false,
    "recipeIntent": true/false,
    "reviewIntent": true/false,
    "comparisonIntent": true/false,
    "rankingPotential": {
      "highPotential": ["tags easy to rank for"],
      "mediumPotential": ["tags with moderate competition"],
      "lowPotential": ["highly competitive tags"]
    }
  },
  "competitive": {
    "commonWithTopVideos": ["tags likely shared with top videos"],
    "uniqueTags": ["tags unique to this video"],
    "missingHighValueTags": ["suggested tags that are missing"],
    "competitorPatterns": ["observed patterns from competitors"]
  },
  "scores": {
    "relevanceScore": 1-10,
    "diversityScore": 1-10,
    "searchVolumeScore": 1-10,
    "competitionScore": 1-10,
    "languageCoverageScore": 1-10,
    "utilizationScore": 1-10,
    "overallScore": 1-10,
    "suggestions": ["list of improvement suggestions"]
  }
}'''
