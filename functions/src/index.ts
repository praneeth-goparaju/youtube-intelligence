/**
 * YouTube Intelligence System - Firebase Functions
 *
 * Provides HTTP and callable endpoints for the Recommendation API
 */

import { onRequest, onCall, HttpsError } from 'firebase-functions/v2/https';
import { setGlobalOptions } from 'firebase-functions/v2';
import { RecommendationEngine } from './engine';
import type { RecommendationRequest, RecommendationResponse, ContentType } from './types';

// Set global options for all functions
setGlobalOptions({
  region: 'us-central1',
  memory: '1GiB',
  timeoutSeconds: 60,
});

// Validate content type
const VALID_CONTENT_TYPES: ContentType[] = ['recipe', 'vlog', 'tutorial', 'review', 'challenge'];

function isValidContentType(type: string): type is ContentType {
  return VALID_CONTENT_TYPES.includes(type as ContentType);
}

// ============================================
// HTTP Endpoint (REST API)
// ============================================

/**
 * HTTP endpoint for generating recommendations
 *
 * POST /recommend
 * Body: { topic: string, type?: string, angle?: string, audience?: string }
 *
 * Example:
 * curl -X POST https://REGION-PROJECT.cloudfunctions.net/recommend \
 *   -H "Content-Type: application/json" \
 *   -d '{"topic": "Biryani", "type": "recipe"}'
 */
export const recommend = onRequest(
  {
    cors: true,  // Enable CORS for web clients
  },
  async (req, res) => {
    // Only allow POST requests
    if (req.method !== 'POST') {
      res.status(405).json({ error: 'Method not allowed. Use POST.' });
      return;
    }

    try {
      // Parse and validate request
      const { topic, type, angle, audience } = req.body as Partial<RecommendationRequest>;

      if (!topic || typeof topic !== 'string' || topic.trim().length === 0) {
        res.status(400).json({
          error: 'Invalid request',
          message: 'Topic is required and must be a non-empty string',
        });
        return;
      }

      if (type && !isValidContentType(type)) {
        res.status(400).json({
          error: 'Invalid request',
          message: `Invalid content type. Must be one of: ${VALID_CONTENT_TYPES.join(', ')}`,
        });
        return;
      }

      // Generate recommendation
      const engine = new RecommendationEngine();
      const recommendation = await engine.generateRecommendation({
        topic: topic.trim(),
        type: type as ContentType || 'recipe',
        angle: angle?.trim(),
        audience: audience?.trim() || 'Telugu audience',
      });

      res.status(200).json(recommendation);
    } catch (error) {
      console.error('Recommendation error:', error);
      res.status(500).json({
        error: 'Internal server error',
        message: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  }
);

// ============================================
// Callable Function (Firebase SDK)
// ============================================

/**
 * Callable function for generating recommendations
 * Use with Firebase SDK's httpsCallable()
 *
 * Example (JavaScript):
 * const functions = getFunctions();
 * const getRecommendation = httpsCallable(functions, 'getRecommendation');
 * const result = await getRecommendation({ topic: 'Biryani', type: 'recipe' });
 */
export const getRecommendation = onCall<RecommendationRequest, Promise<RecommendationResponse>>(
  async (request) => {
    const { topic, type, angle, audience } = request.data;

    // Validate topic
    if (!topic || typeof topic !== 'string' || topic.trim().length === 0) {
      throw new HttpsError(
        'invalid-argument',
        'Topic is required and must be a non-empty string'
      );
    }

    // Validate content type
    if (type && !isValidContentType(type)) {
      throw new HttpsError(
        'invalid-argument',
        `Invalid content type. Must be one of: ${VALID_CONTENT_TYPES.join(', ')}`
      );
    }

    try {
      const engine = new RecommendationEngine();
      return await engine.generateRecommendation({
        topic: topic.trim(),
        type: type || 'recipe',
        angle: angle?.trim(),
        audience: audience?.trim() || 'Telugu audience',
      });
    } catch (error) {
      console.error('Recommendation error:', error);
      throw new HttpsError(
        'internal',
        error instanceof Error ? error.message : 'Failed to generate recommendation'
      );
    }
  }
);

// ============================================
// Health Check Endpoint
// ============================================

/**
 * Health check endpoint
 *
 * GET /health
 */
export const health = onRequest(async (req, res) => {
  if (req.method !== 'GET') {
    res.status(405).json({ error: 'Method not allowed. Use GET.' });
    return;
  }

  try {
    // Basic health check
    const status = {
      status: 'ok',
      timestamp: new Date().toISOString(),
      version: '1.0.0',
    };

    res.status(200).json(status);
  } catch (error) {
    res.status(500).json({
      status: 'error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
});

// ============================================
// Re-export types for consumers
// ============================================

export type {
  RecommendationRequest,
  RecommendationResponse,
  ContentType,
} from './types';
