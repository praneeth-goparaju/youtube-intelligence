#!/usr/bin/env npx tsx
/**
 * CLI for running recommendations locally.
 *
 * Uses shared logic from recommendation-core.ts (same as the Functions engine)
 * with CLI-specific Firebase and Gemini initialization.
 *
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
} from './types';
import {
  sanitizeInput,
  buildContext,
  buildPrompt,
  validateAndFillResponse,
  generateFromTemplates,
  getPostingRecommendation,
  MAX_TOPIC_LENGTH,
  MAX_ANGLE_LENGTH,
  MAX_AUDIENCE_LENGTH,
} from './recommendation-core';

const GEMINI_MODEL = 'gemini-2.0-flash';

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
    model: GEMINI_MODEL,
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
// CLI Recommendation Engine
// Uses shared logic from recommendation-core.ts
// ============================================

class CLIRecommendationEngine {
  private insights: Insights = {};
  private insightsVersion: string | null = null;

  async generateRecommendation(request: RecommendationRequest): Promise<RecommendationResponse> {
    const { topic, type = 'recipe', angle, audience = 'Telugu audience' } = request;

    // Sanitize inputs (shared function)
    const safeTopic = sanitizeInput(topic, MAX_TOPIC_LENGTH);
    const safeAngle = sanitizeInput(angle, MAX_ANGLE_LENGTH);
    const safeAudience = sanitizeInput(audience, MAX_AUDIENCE_LENGTH);

    if (!safeTopic) {
      throw new Error('Topic is required');
    }

    console.log(`\nGenerating recommendation for: "${safeTopic}" (${type})`);

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
        recommendation = await this.generateWithAI(safeTopic, type, safeAngle, safeAudience);
        console.log('✓ AI generation complete');
      } else {
        console.log('Using template-based generation...');
        recommendation = generateFromTemplates(safeTopic, type, safeAngle, safeAudience, this.insights, this.insightsVersion);
        fallbackUsed = true;
      }
    } catch (error) {
      console.warn('AI generation failed, using templates:', error);
      recommendation = generateFromTemplates(safeTopic, type, safeAngle, safeAudience, this.insights, this.insightsVersion);
      fallbackUsed = true;
    }

    recommendation.posting = getPostingRecommendation(this.insights);
    recommendation.metadata = {
      generatedAt: new Date().toISOString(),
      modelUsed: fallbackUsed ? 'template' : GEMINI_MODEL,
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
    // Use shared context and prompt building
    const context = buildContext(this.insights);
    const prompt = buildPrompt(topic, type, angle, audience, context);
    const responseText = await generateWithGemini(prompt);

    try {
      const parsed = JSON.parse(responseText);
      return validateAndFillResponse(parsed, topic, type, this.insights, this.insightsVersion, GEMINI_MODEL);
    } catch {
      throw new Error('Invalid AI response format');
    }
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
