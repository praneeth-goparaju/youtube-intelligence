"""Description analysis prompt for Gemini."""

DESCRIPTION_ANALYSIS_PROMPT = '''Analyze this YouTube video description and return a detailed JSON analysis.

IMPORTANT: Return ONLY valid JSON, no markdown formatting or explanation text.

This is for a Telugu YouTube channel. Analyze:

1. STRUCTURE - Length, sections, organization
2. TIMESTAMPS - Chapter markers, format
3. RECIPE CONTENT - Ingredients, instructions, tips (if cooking)
4. LINKS - Social media, other videos, external
5. HASHTAGS - Tags, categories, positioning
6. CALL TO ACTIONS - Subscribe, like, comment prompts
7. SEO - Keywords, density, optimization
8. MONETIZATION - Affiliate links, sponsors, products

Return this exact JSON structure:

{
  "structure": {
    "totalLength": number,
    "lineCount": number,
    "paragraphCount": number,
    "hasSections": true/false,
    "sections": [
      {"name": "section name", "startLine": number, "endLine": number}
    ],
    "wellOrganized": true/false,
    "usesBulletPoints": true/false,
    "usesNumberedLists": true/false,
    "usesEmojis": true/false,
    "firstLine": "first line text",
    "firstLineHook": true/false,
    "first100Chars": "first 100 characters"
  },
  "timestamps": {
    "hasTimestamps": true/false,
    "timestampCount": number,
    "timestamps": [
      {"time": "0:00", "seconds": 0, "label": "label"}
    ],
    "timestampFormat": "m:ss|mm:ss|h:mm:ss",
    "chaptersEnabled": true/false
  },
  "recipeContent": {
    "hasIngredients": true/false,
    "ingredientCount": number,
    "ingredients": [
      {"item": "name", "quantity": "amount", "category": "category"}
    ],
    "hasInstructions": true/false,
    "instructionSteps": number,
    "hasServingSize": true/false,
    "servingSize": "size or null",
    "hasCookingTime": true/false,
    "prepTime": "time or null",
    "cookTime": "time or null",
    "totalTime": "time or null",
    "hasTips": true/false,
    "tipCount": number,
    "hasNutrition": true/false
  },
  "links": {
    "hasLinks": true/false,
    "linkCount": number,
    "socialMedia": {
      "instagram": {"present": true/false, "url": "url or null"},
      "facebook": {"present": true/false, "url": "url or null"},
      "twitter": {"present": true/false, "url": "url or null"},
      "telegram": {"present": true/false, "url": "url or null"}
    },
    "otherVideos": true/false,
    "otherVideoCount": number,
    "playlistLinks": true/false,
    "channelLink": true/false,
    "websiteLink": true/false,
    "websiteUrl": "url or null",
    "affiliateLinks": true/false,
    "amazonLinks": true/false,
    "merchandiseLink": true/false,
    "businessEmail": true/false,
    "email": "email or null"
  },
  "hashtags": {
    "hasHashtags": true/false,
    "hashtagCount": number,
    "hashtags": ["list of hashtags"],
    "hashtagPosition": "start|middle|end|throughout",
    "brandHashtags": ["list"],
    "topicHashtags": ["list"],
    "genericHashtags": ["list"],
    "languageHashtags": ["list"]
  },
  "callToActions": {
    "hasCTAs": true/false,
    "ctaCount": number,
    "subscribeCTA": true/false,
    "subscribePhrasing": "phrasing or null",
    "likeCTA": true/false,
    "likePhrasing": "phrasing or null",
    "commentCTA": true/false,
    "commentPhrasing": "phrasing or null",
    "commentQuestion": "question or null",
    "shareCTA": true/false,
    "notificationBellCTA": true/false,
    "asksQuestion": true/false,
    "questionAsked": "question or null",
    "otherCTAs": ["list of other CTAs"]
  },
  "seo": {
    "primaryKeywordPresent": true/false,
    "primaryKeyword": "keyword or null",
    "keywordInFirst100Chars": true/false,
    "keywordDensity": decimal,
    "keywordsFound": [
      {"keyword": "word", "count": number}
    ],
    "naturalLanguage": true/false,
    "readabilityScore": 1-10,
    "lengthOptimal": true/false,
    "hasVideoLinks": true/false,
    "internalLinking": "none|minimal|good|excellent"
  },
  "monetization": {
    "hasAffiliateLinks": true/false,
    "hasSponsorMention": true/false,
    "sponsorName": "name or null",
    "hasProductLinks": true/false,
    "hasMerchandise": true/false,
    "hasPatreon": true/false,
    "hasMembership": true/false,
    "hasDisclosure": true/false,
    "disclosureType": "type or null"
  },
  "scores": {
    "completenessScore": 1-10,
    "organizationScore": 1-10,
    "seoScore": 1-10,
    "engagementScore": 1-10,
    "professionalismScore": 1-10,
    "overallScore": 1-10,
    "suggestions": ["list of improvement suggestions"]
  }
}'''
