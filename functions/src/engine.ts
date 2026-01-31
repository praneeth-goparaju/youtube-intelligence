/**
 * Recommendation Engine
 * Generates video recommendations based on insights and AI.
 *
 * Core logic (context building, prompt generation, template fallbacks) is
 * in recommendation-core.ts so it can be shared with the CLI.
 */

import type {
  RecommendationRequest,
  RecommendationResponse,
  ContentType,
  Insights,
} from './types';

import { getAllInsights, getInsightsVersion } from './firebase';
import { generateWithGemini } from './gemini';
import {
  buildContext,
  buildPrompt,
  validateAndFillResponse,
  generateFromTemplates,
  getPostingRecommendation,
} from './recommendation-core';

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
        recommendation = generateFromTemplates(topic, type, angle, audience, this.insights, this.insightsVersion);
        fallbackUsed = true;
      }
    } catch (error) {
      console.error('AI generation failed, falling back to templates:', error);
      recommendation = generateFromTemplates(topic, type, angle, audience, this.insights, this.insightsVersion);
      fallbackUsed = true;
    }

    // Add posting recommendation from insights if available
    recommendation.posting = getPostingRecommendation(this.insights);

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
    const context = buildContext(this.insights);
    const prompt = buildPrompt(topic, type, angle, audience, context);

    const responseText = await generateWithGemini(prompt);

    try {
      const parsed = JSON.parse(responseText);
      return validateAndFillResponse(parsed, topic, type, this.insights, this.insightsVersion, GEMINI_MODEL);
    } catch (error) {
      console.error('Failed to parse AI response:', error);
      throw new Error('Invalid AI response format');
    }
  }
}
