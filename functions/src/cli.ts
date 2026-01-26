#!/usr/bin/env npx tsx
/**
 * CLI for running recommendations locally
 * Usage: npx tsx src/cli.ts --topic "Biryani" --type recipe
 */

import * as admin from 'firebase-admin';
import { GoogleGenerativeAI } from '@google/generative-ai';
import * as fs from 'fs';
import * as path from 'path';
import type {
  RecommendationRequest,
  RecommendationResponse,
  ContentType,
  Insights,
  ThumbnailInsights,
  TitleInsights,
  TimingInsights,
  ContentGapInsights,
  TagRecommendations,
  PostingRecommendation,
  PerformancePrediction,
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
// Environment Setup
// ============================================

function loadEnv(): void {
  // Try to load .env from project root
  const envPaths = [
    path.join(__dirname, '../../.env'),
    path.join(__dirname, '../../../.env'),
    path.join(process.cwd(), '.env'),
  ];

  for (const envPath of envPaths) {
    if (fs.existsSync(envPath)) {
      const content = fs.readFileSync(envPath, 'utf-8');
      for (const line of content.split('\n')) {
        const trimmed = line.trim();
        if (trimmed && !trimmed.startsWith('#')) {
          const [key, ...valueParts] = trimmed.split('=');
          const value = valueParts.join('=').replace(/^["']|["']$/g, '');
          if (key && value && !process.env[key]) {
            process.env[key] = value;
          }
        }
      }
      break;
    }
  }
}

loadEnv();

// ============================================
// Firebase Setup (for CLI)
// ============================================

function initFirebase(): admin.firestore.Firestore {
  if (!admin.apps.length) {
    const projectId = process.env.FIREBASE_PROJECT_ID;
    const clientEmail = process.env.FIREBASE_CLIENT_EMAIL;
    const privateKey = process.env.FIREBASE_PRIVATE_KEY?.replace(/\\n/g, '\n');

    if (!projectId || !clientEmail || !privateKey) {
      console.warn('Firebase credentials not found. Running without insights data.');
      console.warn('Set FIREBASE_PROJECT_ID, FIREBASE_CLIENT_EMAIL, and FIREBASE_PRIVATE_KEY in .env');
      // Initialize without credentials - Firestore calls will be handled gracefully
      admin.initializeApp({ projectId: projectId || 'offline-mode' });
    } else {
      admin.initializeApp({
        credential: admin.credential.cert({
          projectId,
          clientEmail,
          privateKey,
        }),
      });
    }
  }
  return admin.firestore();
}

const db = initFirebase();

async function getAllInsights(): Promise<Insights> {
  const insights: Insights = {};

  try {
    const [thumbnails, titles, timing, contentGaps] = await Promise.all([
      getInsightDocument<ThumbnailInsights>('thumbnails'),
      getInsightDocument<TitleInsights>('titles'),
      getInsightDocument<TimingInsights>('timing'),
      getInsightDocument<ContentGapInsights>('contentGaps'),
    ]);

    if (thumbnails) insights.thumbnails = thumbnails;
    if (titles) insights.titles = titles;
    if (timing) insights.timing = timing;
    if (contentGaps) insights.contentGaps = contentGaps;
  } catch (error) {
    console.warn('Could not fetch insights from Firestore:', error);
  }

  return insights;
}

async function getInsightDocument<T>(type: string): Promise<T | null> {
  try {
    const doc = await db.collection('insights').doc(type).get();
    if (doc.exists) {
      return doc.data() as T;
    }
    return null;
  } catch {
    return null;
  }
}

async function getInsightsVersion(): Promise<string | null> {
  try {
    const doc = await db.collection('insights').doc('thumbnails').get();
    if (doc.exists) {
      const data = doc.data();
      return data?.generatedAt || null;
    }
    return null;
  } catch {
    return null;
  }
}

// ============================================
// Gemini Setup (for CLI)
// ============================================

function getGeminiModel() {
  const apiKey = process.env.GOOGLE_API_KEY;
  if (!apiKey) {
    throw new Error('GOOGLE_API_KEY not found in environment variables');
  }
  const genAI = new GoogleGenerativeAI(apiKey);
  return genAI.getGenerativeModel({
    model: 'gemini-2.0-flash',
    generationConfig: {
      temperature: 0.7,
      topP: 0.95,
      maxOutputTokens: 4096,
    },
  });
}

async function generateWithGemini(prompt: string): Promise<string> {
  const model = getGeminiModel();
  const result = await model.generateContent(prompt);
  const text = result.response.text();

  // Clean markdown formatting
  let cleaned = text.trim();
  if (cleaned.startsWith('```json')) cleaned = cleaned.slice(7);
  else if (cleaned.startsWith('```')) cleaned = cleaned.slice(3);
  if (cleaned.endsWith('```')) cleaned = cleaned.slice(0, -3);

  return cleaned.trim();
}

// ============================================
// Recommendation Engine (simplified for CLI)
// ============================================

class CLIRecommendationEngine {
  private insights: Insights = {};
  private insightsVersion: string | null = null;

  async generateRecommendation(request: RecommendationRequest): Promise<RecommendationResponse> {
    const { topic, type = 'recipe', angle, audience = 'Telugu audience' } = request;

    console.log(`\nGenerating recommendation for: "${topic}" (${type})`);

    // Load insights
    console.log('Loading insights from Firestore...');
    this.insights = await getAllInsights();
    this.insightsVersion = await getInsightsVersion();

    const hasInsightsData = Object.keys(this.insights).length > 0;
    console.log(hasInsightsData ? `✓ Loaded insights (version: ${this.insightsVersion})` : '⚠ No insights available');

    let recommendation: RecommendationResponse;
    let fallbackUsed = false;

    try {
      if (hasInsightsData) {
        console.log('Generating with Gemini AI...');
        recommendation = await this.generateWithAI(topic, type, angle, audience);
        console.log('✓ AI generation complete');
      } else {
        console.log('Using template-based generation...');
        recommendation = this.generateFromTemplates(topic, type, angle, audience);
        fallbackUsed = true;
      }
    } catch (error) {
      console.warn('AI generation failed, using templates:', error);
      recommendation = this.generateFromTemplates(topic, type, angle, audience);
      fallbackUsed = true;
    }

    recommendation.posting = this.getPostingRecommendation();
    recommendation.metadata = {
      generatedAt: new Date().toISOString(),
      modelUsed: fallbackUsed ? 'template' : 'gemini-2.0-flash',
      insightsVersion: this.insightsVersion,
      fallbackUsed,
    };

    return recommendation;
  }

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
    } catch {
      throw new Error('Invalid AI response format');
    }
  }

  private buildContext(): string {
    const parts: string[] = [];

    if (this.insights.thumbnails?.topPerformingElements) {
      parts.push('TOP PERFORMING THUMBNAIL ELEMENTS:');
      const elements = this.insights.thumbnails.topPerformingElements;
      for (const [category, items] of Object.entries(elements)) {
        if (items && items.length > 0) {
          for (const item of items.slice(0, 3)) {
            parts.push(`  - ${category}: ${item.element} (${item.lift.toFixed(1)}x performance)`);
          }
        }
      }
    }

    if (this.insights.titles?.powerWords?.highImpact) {
      parts.push('\nTOP POWER WORDS:');
      for (const pw of this.insights.titles.powerWords.highImpact.slice(0, 5)) {
        const telugu = pw.telugu ? ` / ${pw.telugu}` : '';
        parts.push(`  - ${pw.word}${telugu} (${pw.multiplier.toFixed(1)}x)`);
      }
    }

    if (this.insights.titles?.winningPatterns) {
      parts.push('\nWINNING TITLE PATTERNS:');
      for (const pattern of this.insights.titles.winningPatterns.slice(0, 3)) {
        parts.push(`  - ${pattern.pattern}`);
        if (pattern.examples.length > 0) {
          parts.push(`    Example: "${pattern.examples[0]}"`);
        }
      }
    }

    if (this.insights.timing?.bestTimes?.optimal) {
      const optimal = this.insights.timing.bestTimes.optimal;
      parts.push(`\nOPTIMAL POSTING: ${optimal.day} at ${optimal.hourIST}:00 IST (${optimal.multiplier.toFixed(1)}x performance)`);
    }

    if (this.insights.contentGaps?.highOpportunity) {
      parts.push('\nHIGH OPPORTUNITY TOPICS:');
      for (const gap of this.insights.contentGaps.highOpportunity.slice(0, 3)) {
        parts.push(`  - ${gap.topic} (opportunity score: ${gap.opportunityScore.toFixed(0)})`);
      }
    }

    return parts.join('\n');
  }

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
    "alternatives": [{ "combined": "Alternative title", "predictedCTR": "rating", "reasoning": "Why" }]
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
    "brand": []
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

Important: Use bilingual titles, include Telugu script (not transliteration). Respond ONLY with JSON.`;
  }

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

  generateFromTemplates(
    topic: string,
    type: ContentType,
    angle: string | undefined,
    _audience: string
  ): RecommendationResponse {
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

    const spec = { ...THUMBNAIL_SPECS[type] };
    if (spec.elements.text.primary) {
      spec.elements.text.primary = {
        ...spec.elements.text.primary,
        content: topic.toUpperCase().split(' ')[0],
      };
    }

    const defaults = DEFAULT_TAGS[type];
    const topicLower = topic.toLowerCase();
    const tagPrimary = [topicLower, `${topicLower} ${type === 'recipe' ? 'recipe' : 'video'}`, ...(defaults.primary || [])];
    const tagSecondary = [`${topicLower} telugu`, `how to ${topicLower}`, ...(defaults.secondary || [])];
    const tagTelugu = defaults.telugu || [];
    const tagLongtail = [`${topicLower} in telugu`, `${topicLower} for beginners`, ...(defaults.longtail || [])];
    const allTags = [...tagPrimary, ...tagSecondary, ...tagTelugu, ...tagLongtail];
    const fullTagString = allTags.join(', ');

    return {
      titles: {
        primary: {
          english: `${topic} | ${modifier}`,
          telugu: `${topic} | ${teluguWord}`,
          combined: primary,
          predictedCTR: 'above-average',
          reasoning: 'Combines high-search keyword with power word and bilingual format',
        },
        alternatives,
      },
      thumbnail: spec,
      tags: {
        primary: tagPrimary,
        secondary: tagSecondary,
        telugu: tagTelugu,
        longtail: tagLongtail,
        brand: [],
        fullTagString,
        characterCount: fullTagString.length,
        utilizationPercent: Math.min(100, (fullTagString.length / 500) * 100),
      },
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
        reasoning: `Based on analysis of ${this.insights.timing?.basedOnVideos} videos`,
      };
    }
    return DEFAULT_POSTING;
  }

  private generatePrediction(topic: string, type: ContentType): PerformancePrediction {
    const basePredictions: Record<ContentType, { low: number; medium: number; high: number }> = {
      recipe: { low: 10000, medium: 50000, high: 200000 },
      vlog: { low: 5000, medium: 25000, high: 100000 },
      tutorial: { low: 8000, medium: 40000, high: 150000 },
      review: { low: 5000, medium: 30000, high: 120000 },
      challenge: { low: 15000, medium: 75000, high: 300000 },
    };

    const isSaturated = this.insights.contentGaps?.saturatedTopics?.some(
      (t) => topic.toLowerCase().includes(t.topic.toLowerCase())
    );
    const isHighOpportunity = this.insights.contentGaps?.highOpportunity?.some(
      (t) => topic.toLowerCase().includes(t.topic.toLowerCase())
    );

    const positiveFactors: string[] = [];
    const riskFactors: string[] = [];

    if (isHighOpportunity) positiveFactors.push('Topic has high opportunity score');
    if (isSaturated) riskFactors.push('Topic is saturated - need unique angle');
    positiveFactors.push('Bilingual title format reaches wider audience');
    positiveFactors.push('Thumbnail follows high-performing patterns');

    return {
      expectedViewRange: basePredictions[type],
      confidence: this.insightsVersion ? 'medium' : 'low',
      positiveFactors,
      riskFactors,
    };
  }
}

// ============================================
// CLI Argument Parsing
// ============================================

function parseArgs(): RecommendationRequest & { output?: string; help?: boolean } {
  const args = process.argv.slice(2);
  const result: RecommendationRequest & { output?: string; help?: boolean } = {
    topic: '',
  };

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    const nextArg = args[i + 1];

    switch (arg) {
      case '--topic':
      case '-t':
        result.topic = nextArg || '';
        i++;
        break;
      case '--type':
        result.type = nextArg as ContentType;
        i++;
        break;
      case '--angle':
      case '-a':
        result.angle = nextArg;
        i++;
        break;
      case '--audience':
        result.audience = nextArg;
        i++;
        break;
      case '--output':
      case '-o':
        result.output = nextArg;
        i++;
        break;
      case '--help':
      case '-h':
        result.help = true;
        break;
    }
  }

  return result;
}

function printHelp(): void {
  console.log(`
YouTube Intelligence - Recommendation CLI

Usage:
  npx tsx src/cli.ts --topic "Topic" [options]

Options:
  --topic, -t     Video topic (required)
  --type          Content type: recipe, vlog, tutorial, review, challenge (default: recipe)
  --angle, -a     Unique positioning angle
  --audience      Target audience (default: Telugu audience)
  --output, -o    Output file path (JSON)
  --help, -h      Show this help message

Examples:
  npx tsx src/cli.ts --topic "Biryani" --type recipe
  npx tsx src/cli.ts --topic "Village Cooking" --type vlog --angle "Traditional methods"
  npx tsx src/cli.ts --topic "Phone Review" --type review --output recommendation.json

Environment Variables (in .env):
  GOOGLE_API_KEY          Gemini API key (required)
  FIREBASE_PROJECT_ID     Firebase project ID
  FIREBASE_CLIENT_EMAIL   Firebase service account email
  FIREBASE_PRIVATE_KEY    Firebase service account private key
`);
}

// ============================================
// Main Entry Point
// ============================================

async function main(): Promise<void> {
  const args = parseArgs();

  if (args.help) {
    printHelp();
    process.exit(0);
  }

  if (!args.topic) {
    console.error('Error: --topic is required\n');
    printHelp();
    process.exit(1);
  }

  const engine = new CLIRecommendationEngine();

  try {
    const recommendation = await engine.generateRecommendation({
      topic: args.topic,
      type: args.type,
      angle: args.angle,
      audience: args.audience,
    });

    const output = JSON.stringify(recommendation, null, 2);

    if (args.output) {
      fs.writeFileSync(args.output, output);
      console.log(`\n✓ Recommendation saved to: ${args.output}`);
    } else {
      console.log('\n' + '='.repeat(60));
      console.log('RECOMMENDATION');
      console.log('='.repeat(60));
      console.log(output);
    }
  } catch (error) {
    console.error('Error generating recommendation:', error);
    process.exit(1);
  }
}

main();
