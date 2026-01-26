"""Content structure analysis prompt for Gemini.

This analyzer infers video content structure from descriptions and metadata,
providing transcript-like insights without needing actual transcripts.
"""

CONTENT_STRUCTURE_ANALYSIS_PROMPT = '''Analyze this YouTube video description and metadata to infer the video's content structure and talking points.

IMPORTANT: Return ONLY valid JSON, no markdown formatting or explanation text.

This is for a Telugu cooking/food YouTube channel. Your goal is to infer what the video covers based on the description, timestamps, and metadata - similar to what a transcript analysis would reveal.

VIDEO METADATA:
- Title: {title}
- Duration: {duration_seconds} seconds ({duration_formatted})
- Tags: {tags}

DESCRIPTION:
{description}

Analyze and infer:

1. VIDEO STRUCTURE - Infer the content flow and segments
2. TALKING POINTS - Key topics likely discussed in the video
3. CONTENT OUTLINE - Detailed breakdown of what's covered
4. PACING ANALYSIS - How time is distributed across segments
5. CONTENT TYPE - Classification of the video format
6. INFERRED SCRIPT ELEMENTS - What the creator likely says/shows
7. AUDIENCE ENGAGEMENT POINTS - Where viewer attention is captured

Return this exact JSON structure:

{
  "videoStructure": {
    "format": "tutorial|recipe|vlog|review|tips|compilation|challenge|other",
    "hasIntro": true/false,
    "estimatedIntroDuration": number_in_seconds,
    "hasOutro": true/false,
    "estimatedOutroDuration": number_in_seconds,
    "mainContentDuration": number_in_seconds,
    "segments": [
      {
        "segmentNumber": number,
        "title": "segment title",
        "startTime": "0:00",
        "startSeconds": number,
        "endTime": "0:00",
        "endSeconds": number,
        "duration": number_in_seconds,
        "type": "intro|setup|demonstration|explanation|tips|cta|outro|other",
        "description": "what happens in this segment"
      }
    ],
    "totalSegments": number,
    "averageSegmentDuration": number_in_seconds
  },
  "talkingPoints": {
    "mainTopic": "primary topic of the video",
    "subTopics": ["list", "of", "subtopics"],
    "keyPoints": [
      {
        "point": "key point discussed",
        "importance": "high|medium|low",
        "likelyTimestamp": "approximate time"
      }
    ],
    "questionsAddressed": ["questions the video likely answers"],
    "problemsSolved": ["problems/pain points addressed"]
  },
  "contentOutline": {
    "opening": {
      "hook": "likely opening hook/statement",
      "introduction": "how the video introduces itself"
    },
    "body": [
      {
        "section": "section name",
        "content": "what is covered",
        "keyTakeaway": "main learning/insight"
      }
    ],
    "closing": {
      "summary": "likely conclusion/summary",
      "callToAction": "ending CTA if any"
    }
  },
  "recipeStructure": {
    "isRecipeVideo": true/false,
    "dishName": "name of dish or null",
    "cuisineType": "Telugu|South Indian|North Indian|Fusion|Other|null",
    "mealType": "breakfast|lunch|dinner|snack|dessert|beverage|null",
    "difficultyLevel": "easy|medium|hard|null",
    "estimatedSteps": [
      {
        "stepNumber": number,
        "action": "what is done",
        "duration": "estimated time for this step",
        "keyIngredient": "main ingredient used"
      }
    ],
    "cookingTechniques": ["techniques used"],
    "equipmentMentioned": ["kitchen equipment"],
    "servingStyle": "how the dish is served"
  },
  "pacingAnalysis": {
    "overallPace": "slow|moderate|fast",
    "introToContentRatio": decimal,
    "contentToOutroRatio": decimal,
    "longestSegment": {
      "name": "segment name",
      "duration": number,
      "percentage": decimal
    },
    "shortestSegment": {
      "name": "segment name",
      "duration": number,
      "percentage": decimal
    },
    "paceVariation": "consistent|varied|highly-varied",
    "suggestedImprovements": ["pacing improvement suggestions"]
  },
  "inferredScriptElements": {
    "likelyPhrases": ["phrases the creator probably uses"],
    "teluguPhrases": ["Telugu phrases likely used"],
    "catchphrases": ["recurring phrases or taglines"],
    "technicalTerms": ["cooking/topic-specific terms"],
    "audienceAddressing": "how they address viewers (e.g., 'friends', 'everyone')"
  },
  "engagementPoints": {
    "hookMoment": {
      "timestamp": "when the hook happens",
      "type": "visual|verbal|both",
      "description": "what grabs attention"
    },
    "peakInterestPoints": [
      {
        "timestamp": "when",
        "reason": "why this is engaging"
      }
    ],
    "potentialDropoffPoints": [
      {
        "timestamp": "when",
        "reason": "why viewers might leave"
      }
    ],
    "retentionStrategies": ["strategies used to keep viewers"]
  },
  "contentClassification": {
    "primaryCategory": "main category",
    "secondaryCategories": ["additional categories"],
    "targetAudience": "who this is for",
    "skillLevel": "beginner|intermediate|advanced|all-levels",
    "contentDepth": "overview|moderate|detailed|comprehensive",
    "productionStyle": "casual|semi-professional|professional",
    "uniqueSellingPoint": "what makes this video stand out"
  },
  "seoFromContent": {
    "inferredKeywords": ["keywords from content analysis"],
    "searchQueries": ["queries this video could rank for"],
    "relatedTopics": ["related content suggestions"],
    "contentGaps": ["topics that could be added"]
  },
  "scores": {
    "structureClarity": 1-10,
    "contentCompleteness": 1-10,
    "pacingEffectiveness": 1-10,
    "engagementPotential": 1-10,
    "informationDensity": 1-10,
    "overallContentQuality": 1-10
  },
  "insights": {
    "strengths": ["what the content does well"],
    "improvements": ["suggestions for better content"],
    "transcriptWouldReveal": ["additional insights a transcript would provide"]
  }
}'''
