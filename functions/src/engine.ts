/**
 * Recommendation Engine
 * Generates video recommendations based on insights and AI
 */

import type {
  RecommendationRequest,
  RecommendationResponse,
  ContentType,
  Insights,
  TitleRecommendations,
  ThumbnailRecommendation,
  TagRecommendations,
  PostingRecommendation,
  PerformancePrediction,
  ContentRecommendations,
} from './types';

import { getAllInsights, getInsightsVersion } from './firebase';
import { generateWithGemini } from './gemini';
import {
  TITLE_TEMPLATES,
  POWER_WORDS,
  THUMBNAIL_SPECS,
  DEFAULT_TAGS,
  DEFAULT_POSTING,
  CONTENT_RECOMMENDATIONS,
} from './templates';

const GEMINI_MODEL = 'gemini-2.0-flash';

/**
 * Main recommendation engine class
 */
export class RecommendationEngine {
  private insights: Insights = {};
  private insightsVersion: string | null = null;

  /**
   * Generate a complete recommendation
   */
  async generateRecommendation(request: RecommendationRequest): Promise<RecommendationResponse> {
    const { topic, type = 'recipe', angle, audience = 'Telugu audience' } = request;

    // Load insights from Firestore
    this.insights = await getAllInsights();
    this.insightsVersion = await getInsightsVersion();

    const hasInsightsData = Object.keys(this.insights).length > 0;

    let recommendation: RecommendationResponse;
    let fallbackUsed = false;

    try {
      // Try AI generation first
      if (hasInsightsData) {
        recommendation = await this.generateWithAI(topic, type, angle, audience);
      } else {
        // No insights, use template-based generation
        console.log('No insights available, using template-based generation');
        recommendation = this.generateFromTemplates(topic, type, angle, audience);
        fallbackUsed = true;
      }
    } catch (error) {
      console.error('AI generation failed, falling back to templates:', error);
      recommendation = this.generateFromTemplates(topic, type, angle, audience);
      fallbackUsed = true;
    }

    // Add posting recommendation from insights if available
    recommendation.posting = this.getPostingRecommendation();

    // Add metadata
    recommendation.metadata = {
      generatedAt: new Date().toISOString(),
      modelUsed: fallbackUsed ? 'template' : GEMINI_MODEL,
      insightsVersion: this.insightsVersion,
      fallbackUsed,
    };

    return recommendation;
  }

  /**
   * Generate recommendation using Gemini AI
   */
  private async generateWithAI(
    topic: string,
    type: ContentType,
    angle: string | undefined,
    audience: string
  ): Promise<RecommendationResponse> {
    const context = this.buildContext();
    const prompt = this.buildPrompt(topic, type, angle, audience, context);

    const responseText = await generateWithGemini(prompt);

    try {
      const parsed = JSON.parse(responseText);
      return this.validateAndFillResponse(parsed, topic, type);
    } catch (error) {
      console.error('Failed to parse AI response:', error);
      throw new Error('Invalid AI response format');
    }
  }

  /**
   * Build context string from insights
   */
  private buildContext(): string {
    const parts: string[] = [];

    // Top thumbnail elements
    if (this.insights.thumbnails?.topPerformingElements) {
      parts.push('TOP PERFORMING THUMBNAIL ELEMENTS:');
      const elements = this.insights.thumbnails.topPerformingElements;

      for (const [category, items] of Object.entries(elements)) {
        if (items && items.length > 0) {
          const topItems = items.slice(0, 3);
          for (const item of topItems) {
            parts.push(`  - ${category}: ${item.element} (${item.lift.toFixed(1)}x performance)`);
          }
        }
      }
    }

    // Power words
    if (this.insights.titles?.powerWords?.highImpact) {
      parts.push('\nTOP POWER WORDS:');
      for (const pw of this.insights.titles.powerWords.highImpact.slice(0, 5)) {
        const telugu = pw.telugu ? ` / ${pw.telugu}` : '';
        parts.push(`  - ${pw.word}${telugu} (${pw.multiplier.toFixed(1)}x)`);
      }
    }

    // Winning patterns
    if (this.insights.titles?.winningPatterns) {
      parts.push('\nWINNING TITLE PATTERNS:');
      for (const pattern of this.insights.titles.winningPatterns.slice(0, 3)) {
        parts.push(`  - ${pattern.pattern}`);
        if (pattern.examples.length > 0) {
          parts.push(`    Example: "${pattern.examples[0]}"`);
        }
      }
    }

    // Optimal timing
    if (this.insights.timing?.bestTimes?.optimal) {
      const optimal = this.insights.timing.bestTimes.optimal;
      parts.push(`\nOPTIMAL POSTING: ${optimal.day} at ${optimal.hourIST}:00 IST (${optimal.multiplier.toFixed(1)}x performance)`);
    }

    // Content gaps (opportunities)
    if (this.insights.contentGaps?.highOpportunity) {
      parts.push('\nHIGH OPPORTUNITY TOPICS:');
      for (const gap of this.insights.contentGaps.highOpportunity.slice(0, 3)) {
        parts.push(`  - ${gap.topic} (opportunity score: ${gap.opportunityScore.toFixed(0)})`);
      }
    }

    // Saturated topics (avoid)
    if (this.insights.contentGaps?.saturatedTopics) {
      parts.push('\nSATURATED TOPICS (need unique angle):');
      for (const topic of this.insights.contentGaps.saturatedTopics.slice(0, 3)) {
        parts.push(`  - ${topic.topic} (${topic.competition} competition)`);
      }
    }

    return parts.join('\n');
  }

  /**
   * Build the prompt for Gemini
   */
  private buildPrompt(
    topic: string,
    type: ContentType,
    angle: string | undefined,
    audience: string,
    context: string
  ): string {
    return `You are a YouTube video optimization expert specializing in Telugu content.

Based on the following performance patterns discovered from analyzing 50,000+ successful Telugu videos:

${context}

Generate a complete recommendation for a new video with these details:
- Topic: ${topic}
- Content Type: ${type}
- Unique Angle: ${angle || 'Not specified'}
- Target Audience: ${audience}

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
    "layout": {
      "type": "layout type",
      "description": "Detailed layout description"
    },
    "elements": {
      "face": {
        "required": true/false,
        "expression": "expression type",
        "position": "position",
        "size": "small|medium|large",
        "eyeContact": true/false
      },
      "mainVisual": {
        "type": "visual type",
        "position": "position",
        "showSteam": true/false,
        "garnished": true/false
      },
      "text": {
        "primary": {
          "content": "Text content",
          "position": "position",
          "color": "#HEX",
          "style": "style"
        },
        "secondary": {
          "content": "Telugu text",
          "position": "position",
          "color": "#HEX",
          "language": "telugu"
        }
      },
      "graphics": {
        "addArrow": true/false,
        "arrowPointTo": "target",
        "addBorder": true/false,
        "borderColor": "#HEX"
      }
    },
    "colors": {
      "background": "#HEX",
      "accent": "#HEX",
      "text": "#HEX"
    }
  },
  "tags": {
    "primary": ["main", "keywords"],
    "secondary": ["supporting", "keywords"],
    "telugu": ["తెలుగు", "కీవర్డ్స్"],
    "longtail": ["long tail keywords"],
    "brand": ["channel", "brand", "tags"]
  },
  "prediction": {
    "expectedViewRange": {
      "low": number,
      "medium": number,
      "high": number
    },
    "confidence": "low|medium|high",
    "positiveFactors": ["factor 1", "factor 2"],
    "riskFactors": ["risk 1", "risk 2"]
  },
  "content": {
    "optimalDuration": "X-Y minutes",
    "mustInclude": ["element 1", "element 2"],
    "hooks": ["hook 1", "hook 2"],
    "description": {
      "template": "Description template",
      "mustInclude": ["element 1", "element 2"]
    }
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

  /**
   * Validate and fill missing fields in AI response
   */
  private validateAndFillResponse(
    parsed: Partial<RecommendationResponse>,
    topic: string,
    type: ContentType
  ): RecommendationResponse {
    const template = this.generateFromTemplates(topic, type, undefined, 'Telugu audience');

    return {
      titles: parsed.titles || template.titles,
      thumbnail: parsed.thumbnail || template.thumbnail,
      tags: this.validateTags(parsed.tags, type),
      posting: parsed.posting || template.posting,
      prediction: parsed.prediction || template.prediction,
      content: parsed.content || template.content,
      metadata: template.metadata,
    };
  }

  /**
   * Validate and complete tag recommendations
   */
  private validateTags(tags: Partial<TagRecommendations> | undefined, type: ContentType): TagRecommendations {
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
   * Generate recommendation from templates (fallback)
   */
  generateFromTemplates(
    topic: string,
    type: ContentType,
    angle: string | undefined,
    audience: string
  ): RecommendationResponse {
    return {
      titles: this.generateTitlesFromTemplates(topic, type, angle),
      thumbnail: this.generateThumbnailFromTemplates(topic, type),
      tags: this.generateTagsFromTemplates(topic, type),
      posting: this.getPostingRecommendation(),
      prediction: this.generatePrediction(topic, type),
      content: CONTENT_RECOMMENDATIONS[type],
      metadata: {
        generatedAt: new Date().toISOString(),
        modelUsed: 'template',
        insightsVersion: null,
        fallbackUsed: true,
      },
    };
  }

  /**
   * Generate titles from templates
   */
  private generateTitlesFromTemplates(
    topic: string,
    type: ContentType,
    angle: string | undefined
  ): TitleRecommendations {
    const templates = TITLE_TEMPLATES[type];
    const modifier = angle || POWER_WORDS.english[Math.floor(Math.random() * 3)];
    const teluguWord = POWER_WORDS.telugu[Math.floor(Math.random() * 3)];

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
   * Generate thumbnail from templates
   */
  private generateThumbnailFromTemplates(topic: string, type: ContentType): ThumbnailRecommendation {
    const spec = { ...THUMBNAIL_SPECS[type] };

    // Customize text content based on topic
    if (spec.elements.text.primary) {
      spec.elements.text.primary = {
        ...spec.elements.text.primary,
        content: topic.toUpperCase().split(' ')[0],
      };
    }

    return spec;
  }

  /**
   * Generate tags from templates
   */
  private generateTagsFromTemplates(topic: string, type: ContentType): TagRecommendations {
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
   * Get posting recommendation from insights or defaults
   */
  private getPostingRecommendation(): PostingRecommendation {
    if (this.insights.timing?.bestTimes?.optimal) {
      const optimal = this.insights.timing.bestTimes.optimal;
      const byDay = this.insights.timing.bestTimes.byDayOfWeek || [];

      return {
        bestDay: optimal.day,
        bestTime: `${optimal.hourIST}:00 IST`,
        alternativeTimes: byDay
          .filter((d) => d.day !== optimal.day)
          .slice(0, 2)
          .map((d) => `${d.day} ${optimal.hourIST}:00 IST`),
        reasoning: `Based on analysis of ${this.insights.timing.basedOnVideos} videos, ${optimal.day} at ${optimal.hourIST}:00 IST has ${optimal.multiplier.toFixed(1)}x average performance`,
      };
    }

    return DEFAULT_POSTING;
  }

  /**
   * Generate performance prediction
   */
  private generatePrediction(topic: string, type: ContentType): PerformancePrediction {
    // Base predictions by content type
    const basePredictions: Record<ContentType, { low: number; medium: number; high: number }> = {
      recipe: { low: 10000, medium: 50000, high: 200000 },
      vlog: { low: 5000, medium: 25000, high: 100000 },
      tutorial: { low: 8000, medium: 40000, high: 150000 },
      review: { low: 5000, medium: 30000, high: 120000 },
      challenge: { low: 15000, medium: 75000, high: 300000 },
    };

    const base = basePredictions[type];

    // Check if topic is saturated
    const isSaturated = this.insights.contentGaps?.saturatedTopics?.some(
      (t) => topic.toLowerCase().includes(t.topic.toLowerCase())
    );

    // Check if topic is high opportunity
    const isHighOpportunity = this.insights.contentGaps?.highOpportunity?.some(
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
      expectedViewRange: base,
      confidence: this.insightsVersion ? 'medium' : 'low',
      positiveFactors,
      riskFactors,
    };
  }
}
