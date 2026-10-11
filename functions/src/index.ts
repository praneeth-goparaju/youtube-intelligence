/**
 * YouTube Intelligence System - Firebase Functions
 *
 * Provides HTTP and callable endpoints for the Recommendation API
 */

import { onRequest, onCall, HttpsError } from 'firebase-functions/v2/https';
import { setGlobalOptions } from 'firebase-functions/v2';
import { defineSecret, defineString } from 'firebase-functions/params';
import { RecommendationEngine } from './engine';
import { geminiApiKey } from './gemini';
import { withHttpGuards, requireCallableAuth, parseAllowedOrigins, type RateLimitConfig } from './middleware';
import {
  InvalidRequest, parseRecommendationRequest, parseIdeasRequest, parseGenerationRequest, parseGenerationType,
} from './request-validation';
import { saveGeneration as saveGen, listGenerations as listGens } from './firebase';
import type { RecommendationResponse, IdeaGenerationResponse } from './types';

// Set global options for all functions
setGlobalOptions({
  region: 'us-central1',
  memory: '1GiB',
  timeoutSeconds: 60,
});

// API key for authentication (set via Firebase Console or CLI)
const apiKeyParam = defineSecret('RECOMMEND_API_KEY');

// Allowed origins for CORS (comma-separated list)
const allowedOriginsParam = defineString('ALLOWED_ORIGINS', {
  description: 'Comma-separated list of allowed origins for CORS',
  default: '',
});

// Rate limiting configuration (distributed via Firestore)
const RATE_LIMIT_MAX = 100; // requests per window
const RATE_LIMIT_WINDOW_MS = 60 * 60 * 1000; // 1 hour
const RATE_LIMIT: RateLimitConfig = { max: RATE_LIMIT_MAX, windowMs: RATE_LIMIT_WINDOW_MS };

/** Read the configured API key at request time (Firebase params resolve at runtime). */
const getApiKey = (): string => apiKeyParam.value();

/**
 * Get allowed origins for CORS from the configured ALLOWED_ORIGINS param.
 */
function getAllowedOrigins(): string[] | boolean {
  return parseAllowedOrigins(allowedOriginsParam.value());
}

// ============================================
// HTTP Endpoint (REST API)
// ============================================

/**
 * HTTP endpoint for generating recommendations
 *
 * POST /recommend
 * Headers: Authorization: Bearer <API_KEY>
 * Body: { topic: string, type?: string, angle?: string, audience?: string }
 *
 * Example:
 * curl -X POST https://REGION-PROJECT.cloudfunctions.net/recommend \
 *   -H "Content-Type: application/json" \
 *   -H "Authorization: Bearer YOUR_API_KEY" \
 *   -d '{"topic": "Biryani", "type": "recipe"}'
 */
export const recommend = onRequest(
  {
    cors: getAllowedOrigins(),  // Restricted CORS - configure ALLOWED_ORIGINS
    secrets: [apiKeyParam, geminiApiKey],
  },
  withHttpGuards({ method: 'POST', getApiKey, rateLimit: RATE_LIMIT }, async (req, res) => {
    try {
      const request = parseRecommendationRequest(req.body);
      const engine = new RecommendationEngine();
      const recommendation = await engine.generateRecommendation(request);

      res.status(200).json(recommendation);
    } catch (error) {
      if (error instanceof InvalidRequest) {
        res.status(400).json({ error: 'Invalid request', message: error.message });
        return;
      }
      console.error('Recommendation error:', error);
      res.status(500).json({
        error: 'Internal server error',
        message: 'Failed to generate recommendation',  // Don't leak internal error details
      });
    }
  })
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
export const getRecommendation = onCall<unknown, Promise<RecommendationResponse>>(
  { secrets: [geminiApiKey] },
  async (request) => {
    await requireCallableAuth(request, RATE_LIMIT);

    try {
      const input = parseRecommendationRequest(request.data);
      const engine = new RecommendationEngine();
      return await engine.generateRecommendation(input);
    } catch (error) {
      if (error instanceof InvalidRequest) throw new HttpsError('invalid-argument', error.message);
      console.error('Recommendation error:', error);
      throw new HttpsError(
        'internal',
        'Failed to generate recommendation'  // Don't leak internal error details
      );
    }
  }
);

// ============================================
// Ideas HTTP Endpoint
// ============================================

/**
 * HTTP endpoint for generating video ideas
 *
 * POST /ideas
 * Headers: Authorization: Bearer <API_KEY>
 * Body: { type?: string }
 */
export const ideas = onRequest(
  {
    cors: getAllowedOrigins(),
    secrets: [apiKeyParam, geminiApiKey],
  },
  withHttpGuards({ method: 'POST', getApiKey, rateLimit: RATE_LIMIT }, async (req, res) => {
    try {
      const { type } = parseIdeasRequest(req.body);
      const engine = new RecommendationEngine();
      const response = await engine.generateIdeas(type);
      res.status(200).json(response);
    } catch (error) {
      if (error instanceof InvalidRequest) {
        res.status(400).json({ error: 'Invalid request', message: error.message });
        return;
      }
      console.error('Ideas generation error:', error);
      res.status(500).json({
        error: 'Internal server error',
        message: 'Failed to generate ideas',
      });
    }
  })
);

// ============================================
// Ideas Callable Function
// ============================================

/**
 * Callable function for generating video ideas
 */
export const getIdeas = onCall<unknown, Promise<IdeaGenerationResponse>>(
  { secrets: [geminiApiKey] },
  async (request) => {
    await requireCallableAuth(request, RATE_LIMIT);

    try {
      const { type } = parseIdeasRequest(request.data);
      const engine = new RecommendationEngine();
      return await engine.generateIdeas(type);
    } catch (error) {
      if (error instanceof InvalidRequest) throw new HttpsError('invalid-argument', error.message);
      console.error('Ideas generation error:', error);
      throw new HttpsError(
        'internal',
        'Failed to generate ideas'
      );
    }
  }
);

// ============================================
// Generations Endpoints (auto-save history)
// ============================================

/**
 * POST /generationsSave
 * Body: { type, request, response }
 * Returns: { id, savedAt }
 */
export const generationsSave = onRequest(
  {
    cors: getAllowedOrigins(),
    secrets: [apiKeyParam],
  },
  withHttpGuards({ method: 'POST', getApiKey, rateLimit: RATE_LIMIT }, async (req, res) => {
    try {
      const result = await saveGen(parseGenerationRequest(req.body));
      res.status(200).json(result);
    } catch (error) {
      if (error instanceof InvalidRequest) {
        res.status(400).json({ error: 'Invalid request', message: error.message });
        return;
      }
      console.error('Save generation error:', error);
      res.status(500).json({ error: 'Failed to save generation' });
    }
  })
);

/**
 * GET /generationsList
 * Query: ?type=ideas|recommendation (optional)
 * Returns: { generations: [...] }
 */
export const generationsList = onRequest(
  {
    cors: getAllowedOrigins(),
    secrets: [apiKeyParam],
  },
  withHttpGuards({ method: 'GET', getApiKey, rateLimit: RATE_LIMIT }, async (req, res) => {
    try {
      const type = parseGenerationType(req.query.type);
      const generations = await listGens(type);
      res.status(200).json({ generations });
    } catch (error) {
      if (error instanceof InvalidRequest) {
        res.status(400).json({ error: 'Invalid request', message: error.message });
        return;
      }
      console.error('List generations error:', error);
      res.status(500).json({ error: 'Failed to list generations' });
    }
  })
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
      message: 'Internal server error',
    });
  }
});

// ============================================
// Re-export types for consumers
// ============================================

export type {
  RecommendationRequest,
  RecommendationResponse,
  IdeaGenerationResponse,
  ContentType,
} from './types';
