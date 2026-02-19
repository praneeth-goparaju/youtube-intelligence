/**
 * YouTube Intelligence System - Firebase Functions
 *
 * Provides HTTP and callable endpoints for the Recommendation API
 */

import { onRequest, onCall, HttpsError } from 'firebase-functions/v2/https';
import { setGlobalOptions } from 'firebase-functions/v2';
import { defineString } from 'firebase-functions/params';
import { RecommendationEngine } from './engine';
import { checkRateLimit } from './rate-limiter';
import { sanitizeInput, MAX_TOPIC_LENGTH, MAX_ANGLE_LENGTH, MAX_AUDIENCE_LENGTH } from './recommendation-core';
import type { RecommendationRequest, RecommendationResponse, ContentType } from './types';

// Set global options for all functions
setGlobalOptions({
  region: 'us-central1',
  memory: '1GiB',
  timeoutSeconds: 60,
});

// API key for authentication (set via Firebase Console or CLI)
const apiKeyParam = defineString('RECOMMEND_API_KEY', {
  description: 'API key for authenticating recommendation requests',
  default: '',
});

// Allowed origins for CORS (comma-separated list)
const allowedOriginsParam = defineString('ALLOWED_ORIGINS', {
  description: 'Comma-separated list of allowed origins for CORS',
  default: '',
});

// Rate limiting configuration (distributed via Firestore)
const RATE_LIMIT_MAX = 100; // requests per window
const RATE_LIMIT_WINDOW_MS = 60 * 60 * 1000; // 1 hour

/**
 * Get allowed origins for CORS
 */
function getAllowedOrigins(): string[] | boolean {
  const originsStr = allowedOriginsParam.value();
  if (!originsStr) {
    // If no origins configured, deny all cross-origin requests in production
    // Return false to disable CORS entirely (same-origin only)
    return false;
  }
  return originsStr.split(',').map((o) => o.trim()).filter((o) => o.length > 0);
}

/**
 * Validate API key from request header
 */
function validateApiKey(authHeader: string | undefined): boolean {
  const configuredKey = apiKeyParam.value();

  // If no API key is configured, allow requests (for development)
  // In production, ALWAYS configure RECOMMEND_API_KEY
  if (!configuredKey) {
    console.warn('WARNING: RECOMMEND_API_KEY not configured. API is unprotected!');
    return true;
  }

  if (!authHeader) {
    return false;
  }

  // Support both "Bearer <key>" and raw key formats
  const key = authHeader.startsWith('Bearer ') ? authHeader.slice(7) : authHeader;
  return key === configuredKey;
}

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
  },
  async (req, res) => {
    // Only allow POST requests
    if (req.method !== 'POST') {
      res.status(405).json({ error: 'Method not allowed. Use POST.' });
      return;
    }

    // Validate API key
    if (!validateApiKey(req.headers.authorization)) {
      res.status(401).json({
        error: 'Unauthorized',
        message: 'Invalid or missing API key. Use Authorization: Bearer <key>',
      });
      return;
    }

    // Check rate limit (use IP or API key as identifier, distributed via Firestore)
    const rateLimitKey = req.headers.authorization || req.ip || 'anonymous';
    const rateLimit = await checkRateLimit(rateLimitKey, RATE_LIMIT_MAX, RATE_LIMIT_WINDOW_MS);
    res.setHeader('X-RateLimit-Remaining', rateLimit.remaining.toString());

    if (!rateLimit.allowed) {
      res.status(429).json({
        error: 'Rate limit exceeded',
        message: 'Too many requests. Please try again later.',
      });
      return;
    }

    try {
      // Parse and validate request
      const { topic, type, angle, audience } = req.body as Partial<RecommendationRequest>;

      // Sanitize inputs to prevent prompt injection
      const sanitizedTopic = sanitizeInput(topic, MAX_TOPIC_LENGTH);
      const sanitizedAngle = sanitizeInput(angle, MAX_ANGLE_LENGTH);
      const sanitizedAudience = sanitizeInput(audience, MAX_AUDIENCE_LENGTH);

      if (!sanitizedTopic || sanitizedTopic.length === 0) {
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

      // Generate recommendation with sanitized inputs
      const engine = new RecommendationEngine();
      const recommendation = await engine.generateRecommendation({
        topic: sanitizedTopic,
        type: type as ContentType || 'recipe',
        angle: sanitizedAngle || undefined,
        audience: sanitizedAudience || 'Telugu audience',
      });

      res.status(200).json(recommendation);
    } catch (error) {
      console.error('Recommendation error:', error);
      res.status(500).json({
        error: 'Internal server error',
        message: 'Failed to generate recommendation',  // Don't leak internal error details
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
export const getRecommendation = onCall<RecommendationRequest, RecommendationResponse>(
  async (request) => {
    // Require authentication
    if (!request.auth) {
      throw new HttpsError(
        'unauthenticated',
        'Authentication required. Please sign in to use this service.'
      );
    }

    const { topic, type, angle, audience } = request.data;

    // Check rate limit using auth UID (distributed via Firestore)
    const rateLimitKey = request.auth.uid;
    const rateLimit = await checkRateLimit(rateLimitKey, RATE_LIMIT_MAX, RATE_LIMIT_WINDOW_MS);

    if (!rateLimit.allowed) {
      throw new HttpsError(
        'resource-exhausted',
        'Rate limit exceeded. Please try again later.'
      );
    }

    // Sanitize inputs to prevent prompt injection
    const sanitizedTopic = sanitizeInput(topic, MAX_TOPIC_LENGTH);
    const sanitizedAngle = sanitizeInput(angle, MAX_ANGLE_LENGTH);
    const sanitizedAudience = sanitizeInput(audience, MAX_AUDIENCE_LENGTH);

    // Validate topic
    if (!sanitizedTopic || sanitizedTopic.length === 0) {
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
        topic: sanitizedTopic,
        type: type || 'recipe',
        angle: sanitizedAngle || undefined,
        audience: sanitizedAudience || 'Telugu audience',
      });
    } catch (error) {
      console.error('Recommendation error:', error);
      throw new HttpsError(
        'internal',
        'Failed to generate recommendation'  // Don't leak internal error details
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
