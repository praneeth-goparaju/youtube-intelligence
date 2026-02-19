/**
 * Shared recommendation logic used by both the Functions engine and CLI.
 *
 * Contains pure functions that don't depend on Firebase Functions context,
 * making them usable in any TypeScript environment.
 */

import type {
  ContentType,
  Insights,
  TagRecommendations,
  PostingRecommendation,
  PerformancePrediction,
  ThumbnailRecommendation,
  TitleRecommendations,
  RecommendationResponse,
  ContentRecommendations,
} from './types';

import {
  TITLE_TEMPLATES,
  POWER_WORDS,
  THUMBNAIL_SPECS,
  DEFAULT_TAGS,
  DEFAULT_POSTING,
  CONTENT_RECOMMENDATIONS,
} from './templates';

// ============================================
// Input Sanitization
// ============================================

export const MAX_TOPIC_LENGTH = 200;
export const MAX_ANGLE_LENGTH = 500;
export const MAX_AUDIENCE_LENGTH = 200;

/**
 * Sanitize user input: remove control characters, normalize whitespace, truncate.
 */
export function sanitizeInput(input: string | undefined, maxLength: number): string {
  if (!input) return '';

  let sanitized = input
    .replace(/[\x00-\x1F\x7F]/g, '')
    .replace(/\s+/g, ' ')
    .trim();

  if (sanitized.length > maxLength) {
    sanitized = sanitized.slice(0, maxLength);
  }

  return sanitized;
}

/**
 * Escape user input to prevent prompt injection.
 */
export function escapeForPrompt(input: string): string {
  return input
    .replace(/```/g, '')
    .replace(/\n{3,}/g, '\n\n')
    .replace(/[<>]/g, '')
    .slice(0, 500);
}

// ============================================
// Context & Prompt Building
// ============================================

/**
 * Build context string from insights data for the Gemini prompt.
 */
export function buildContext(insights: Insights): string {
  const parts: string[] = [];

  if (insights.thumbnails?.topPerformingElements) {
    parts.push('TOP PERFORMING THUMBNAIL ELEMENTS:');
    const elements = insights.thumbnails.topPerformingElements;
    for (const [category, items] of Object.entries(elements)) {
      if (items && items.length > 0) {
        for (const item of items.slice(0, 3)) {
          parts.push(`  - ${category}: ${item.element} (${item.lift.toFixed(1)}x performance)`);
        }
      }
    }
  }

  if (insights.titles?.powerWords?.highImpact) {
    parts.push('\nTOP POWER WORDS:');
    for (const pw of insights.titles.powerWords.highImpact.slice(0, 5)) {
      const telugu = pw.telugu ? ` / ${pw.telugu}` : '';
      parts.push(`  - ${pw.word}${telugu} (${pw.multiplier.toFixed(1)}x)`);
    }
  }

  if (insights.titles?.winningPatterns) {
    parts.push('\nWINNING TITLE PATTERNS:');
    for (const pattern of insights.titles.winningPatterns.slice(0, 3)) {
      parts.push(`  - ${pattern.pattern}`);
      if (pattern.examples.length > 0) {
        parts.push(`    Example: "${pattern.examples[0]}"`);
      }
    }
  }

  if (insights.timing?.bestTimes?.optimal) {
    const optimal = insights.timing.bestTimes.optimal;
    parts.push(`\nOPTIMAL POSTING: ${optimal.day} at ${optimal.hourIST}:00 IST (${optimal.multiplier.toFixed(1)}x performance)`);
  }

  if (insights.contentGaps?.highOpportunity) {
    parts.push('\nHIGH OPPORTUNITY TOPICS:');
    for (const gap of insights.contentGaps.highOpportunity.slice(0, 3)) {
      parts.push(`  - ${gap.topic} (opportunity score: ${gap.opportunityScore.toFixed(0)})`);
    }
  }

  if (insights.contentGaps?.saturatedTopics) {
    parts.push('\nSATURATED TOPICS (need unique angle):');
    for (const topic of insights.contentGaps.saturatedTopics.slice(0, 3)) {
      parts.push(`  - ${topic.topic} (${topic.competition} competition)`);
    }
  }

  return parts.join('\n');
}

/**
 * Build the Gemini prompt for recommendation generation.
 */
export function buildPrompt(
  topic: string,
  type: ContentType,
  angle: string | undefined,
  audience: string,
  context: string
): string {
  const safeTopic = escapeForPrompt(topic);
  const safeAngle = angle ? escapeForPrompt(angle) : 'Not specified';
  const safeAudience = escapeForPrompt(audience);

  return `You are a YouTube video optimization expert specializing in Telugu content.

Based on the following performance patterns discovered from analyzing 50,000+ successful Telugu videos:

${context}

Generate a complete recommendation for a new video with these details:
- Topic: ${safeTopic}
- Content Type: ${type}
- Unique Angle: ${safeAngle}
- Target Audience: ${safeAudience}

Provide recommendations in the following JSON format:
{
  "titles": {
    "primary": {
      "english": "English title",
      "telugu": "Telugu title",
      "combined": "Combined bilingual title",
      "predictedCTR": "below-average|average|above-average|high",
      "reasoning": "Why this title works"
    },
    "alternatives": [
      {
        "combined": "Alternative title",
        "predictedCTR": "rating",
        "reasoning": "Why this works"
      }
    ]
  },
  "thumbnail": {
    "layout": { "type": "layout type", "description": "Detailed layout description" },
    "elements": {
      "face": { "required": true/false, "expression": "type", "position": "pos", "size": "size", "eyeContact": true/false },
      "mainVisual": { "type": "type", "position": "pos", "showSteam": true/false, "garnished": true/false },
      "text": { "primary": { "content": "TEXT", "position": "pos", "color": "#HEX", "style": "style" } },
      "graphics": { "addArrow": true/false, "addBorder": true/false }
    },
    "colors": { "background": "#HEX", "accent": "#HEX", "text": "#HEX" }
  },
  "tags": {
    "primary": ["main", "keywords"],
    "secondary": ["supporting", "keywords"],
    "telugu": ["తెలుగు", "కీవర్డ్స్"],
    "longtail": ["long tail keywords"],
    "brand": ["channel", "brand", "tags"]
  },
  "prediction": {
    "expectedViewRange": { "low": number, "medium": number, "high": number },
    "confidence": "low|medium|high",
    "positiveFactors": ["factor 1"],
    "riskFactors": ["risk 1"]
  },
  "content": {
    "optimalDuration": "X-Y minutes",
    "mustInclude": ["element 1"],
    "hooks": ["hook 1"],
    "description": { "template": "Description template", "mustInclude": ["element 1"] }
  }
}

Important guidelines:
1. Use bilingual titles (English + Telugu) for maximum reach
2. Include power words that have proven to increase views
3. Design thumbnails based on top-performing elements
4. Suggest realistic view predictions based on the topic and competition
5. All Telugu text should use Telugu script (not transliteration)

Respond ONLY with the JSON object, no additional text.`;
}

// ============================================
// Tag & Prediction Helpers
// ============================================

/**
 * Validate and complete tag recommendations, filling missing fields with defaults.
 */
export function validateTags(tags: Partial<TagRecommendations> | undefined, type: ContentType): TagRecommendations {
  const defaults = DEFAULT_TAGS[type];

  const primary = tags?.primary || defaults.primary || [];
  const secondary = tags?.secondary || defaults.secondary || [];
  const telugu = tags?.telugu || defaults.telugu || [];
  const longtail = tags?.longtail || defaults.longtail || [];
  const brand = tags?.brand || [];

  const allTags = [...primary, ...secondary, ...telugu, ...longtail, ...brand];
  const fullTagString = allTags.join(', ');

  return {
    primary,
    secondary,
    telugu,
    longtail,
    brand,
    fullTagString,
    characterCount: fullTagString.length,
    utilizationPercent: Math.min(100, (fullTagString.length / 500) * 100),
  };
}

/**
 * Get posting recommendation from insights or defaults.
 */
export function getPostingRecommendation(insights: Insights): PostingRecommendation {
  if (insights.timing?.bestTimes?.optimal) {
    const optimal = insights.timing.bestTimes.optimal;
    const byDay = insights.timing.bestTimes.byDayOfWeek || [];

    return {
      bestDay: optimal.day,
      bestTime: `${optimal.hourIST}:00 IST`,
      alternativeTimes: byDay
        .filter((d) => d.day !== optimal.day)
        .slice(0, 2)
        .map((d) => `${d.day} ${optimal.hourIST}:00 IST`),
      reasoning: `Based on analysis of ${insights.timing?.basedOnVideos} videos, ${optimal.day} at ${optimal.hourIST}:00 IST has ${optimal.multiplier.toFixed(1)}x average performance`,
    };
  }

  return DEFAULT_POSTING;
}

/**
 * Generate performance prediction based on content type and insights.
 */
export function generatePrediction(
  topic: string,
  type: ContentType,
  insights: Insights,
  insightsVersion: string | null
): PerformancePrediction {
  const basePredictions: Record<ContentType, { low: number; medium: number; high: number }> = {
    recipe: { low: 10000, medium: 50000, high: 200000 },
    vlog: { low: 5000, medium: 25000, high: 100000 },
    tutorial: { low: 8000, medium: 40000, high: 150000 },
    review: { low: 5000, medium: 30000, high: 120000 },
    challenge: { low: 15000, medium: 75000, high: 300000 },
  };

  const isSaturated = insights.contentGaps?.saturatedTopics?.some(
    (t) => topic.toLowerCase().includes(t.topic.toLowerCase())
  );

  const isHighOpportunity = insights.contentGaps?.highOpportunity?.some(
    (t) => topic.toLowerCase().includes(t.topic.toLowerCase())
  );

  const positiveFactors: string[] = [];
  const riskFactors: string[] = [];

  if (isHighOpportunity) {
    positiveFactors.push('Topic has high opportunity score (low competition, good views)');
  }
  if (isSaturated) {
    riskFactors.push('Topic is saturated - need unique angle to stand out');
  }

  positiveFactors.push('Bilingual title format reaches wider audience');
  positiveFactors.push('Thumbnail follows high-performing patterns');

  if (type === 'recipe') {
    positiveFactors.push('Recipe content has consistent audience demand');
  }

  return {
    expectedViewRange: basePredictions[type],
    confidence: insightsVersion ? 'medium' : 'low',
    positiveFactors,
    riskFactors,
  };
}

// ============================================
// Template-Based Generation
// ============================================

/**
 * Generate title recommendations from templates.
 */
export function generateTitlesFromTemplates(
  topic: string,
  type: ContentType,
  angle: string | undefined
): TitleRecommendations {
  const templates = TITLE_TEMPLATES[type];
  const modifier = angle || POWER_WORDS.english[0];
  const teluguWord = POWER_WORDS.telugu[0];

  const fillTemplate = (template: string): string => {
    return template
      .replace('{dish}', topic)
      .replace('{dish_telugu}', `${topic} (తెలుగు)`)
      .replace('{topic}', topic)
      .replace('{topic_telugu}', `${topic} తెలుగు`)
      .replace('{modifier}', modifier)
      .replace('{location}', topic)
      .replace('{number}', '10');
  };

  const primary = fillTemplate(templates[0]);
  const alternatives = templates.slice(1, 3).map((t) => ({
    combined: fillTemplate(t),
    predictedCTR: 'average' as const,
    reasoning: 'Uses proven title pattern for Telugu content',
  }));

  return {
    primary: {
      english: `${topic} | ${modifier}`,
      telugu: `${topic} | ${teluguWord}`,
      combined: primary,
      predictedCTR: 'above-average',
      reasoning: 'Combines high-search keyword with power word and bilingual format',
    },
    alternatives,
  };
}

/**
 * Generate thumbnail recommendation from templates.
 */
export function generateThumbnailFromTemplates(topic: string, type: ContentType): ThumbnailRecommendation {
  const spec: ThumbnailRecommendation = JSON.parse(JSON.stringify(THUMBNAIL_SPECS[type]));

  if (spec.elements.text.primary) {
    spec.elements.text.primary.content = topic.toUpperCase().split(' ')[0];
  }

  return spec;
}

/**
 * Generate tags from templates.
 */
export function generateTagsFromTemplates(topic: string, type: ContentType): TagRecommendations {
  const defaults = DEFAULT_TAGS[type];
  const topicLower = topic.toLowerCase();

  const primary = [
    topicLower,
    `${topicLower} ${type === 'recipe' ? 'recipe' : 'video'}`,
    ...(defaults.primary || []),
  ];
  const secondary = [
    `${topicLower} telugu`,
    `how to ${topicLower}`,
    ...(defaults.secondary || []),
  ];
  const telugu = defaults.telugu || [];
  const longtail = [
    `${topicLower} in telugu`,
    `${topicLower} for beginners`,
    ...(defaults.longtail || []),
  ];

  const allTags = [...primary, ...secondary, ...telugu, ...longtail];
  const fullTagString = allTags.join(', ');

  return {
    primary,
    secondary,
    telugu,
    longtail,
    brand: [],
    fullTagString,
    characterCount: fullTagString.length,
    utilizationPercent: Math.min(100, (fullTagString.length / 500) * 100),
  };
}

/**
 * Generate a complete recommendation from templates (fallback).
 */
export function generateFromTemplates(
  topic: string,
  type: ContentType,
  angle: string | undefined,
  audience: string,
  insights: Insights,
  insightsVersion: string | null
): RecommendationResponse {
  return {
    titles: generateTitlesFromTemplates(topic, type, angle),
    thumbnail: generateThumbnailFromTemplates(topic, type),
    tags: generateTagsFromTemplates(topic, type),
    posting: getPostingRecommendation(insights),
    prediction: generatePrediction(topic, type, insights, insightsVersion),
    content: CONTENT_RECOMMENDATIONS[type],
    metadata: {
      generatedAt: new Date().toISOString(),
      modelUsed: 'template',
      insightsVersion,
      fallbackUsed: true,
    },
  };
}

/**
 * Validate and fill missing fields from an AI-parsed response using template defaults.
 */
export function validateAndFillResponse(
  parsed: Partial<RecommendationResponse>,
  topic: string,
  type: ContentType,
  insights: Insights,
  insightsVersion: string | null,
  modelUsed: string
): RecommendationResponse {
  const template = generateFromTemplates(topic, type, undefined, 'Telugu audience', insights, insightsVersion);

  return {
    titles: parsed.titles || template.titles,
    thumbnail: parsed.thumbnail || template.thumbnail,
    tags: validateTags(parsed.tags, type),
    posting: parsed.posting || template.posting,
    prediction: parsed.prediction || template.prediction,
    content: parsed.content || template.content,
    metadata: {
      generatedAt: new Date().toISOString(),
      modelUsed,
      insightsVersion,
      fallbackUsed: false,
    },
  };
}
