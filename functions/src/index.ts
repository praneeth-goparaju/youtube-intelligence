/**
 * YouTube Intelligence System - Firebase Functions
 *
 * Provides HTTP and callable endpoints for the Recommendation API
 */

import { onRequest, onCall, HttpsError } from 'firebase-functions/v2/https';
import type { Request } from 'firebase-functions/v2/https';
import type { Response } from 'express';
import { setGlobalOptions } from 'firebase-functions/v2';
import { defineSecret, defineString } from 'firebase-functions/params';
import { createHash } from 'crypto';
import { RecommendationEngine } from './engine';
import { checkRateLimit } from './rate-limiter';
import { saveGeneration as saveGen, listGenerations as listGens } from './firebase';
import { geminiApiKey, isGeminiConfigured } from './gemini';
import { readSecret } from './secrets';
import {
  safeCompareKeys,
  extractBearerKey,
  deriveClientIp,
  parseRecommendationInput,
  parseIdeasInput,
  validateGenerationPayload,
} from './request-validation';
import type { RecommendationResponse, IdeaGenerationResponse } from './types';

// Set global options for all functions.
// timeoutSeconds must exceed the Gemini deadline budget (gemini.ts,
// GEMINI_TOTAL_BUDGET_MS = 90s) so the template fallback can still respond.
setGlobalOptions({
  region: 'us-central1',
  memory: '1GiB',
  timeoutSeconds: 120,
  maxInstances: 10,
});

// API key for authenticating HTTP requests (Secret Manager):
//   firebase functions:secrets:set RECOMMEND_API_KEY
const recommendApiKey = defineSecret('RECOMMEND_API_KEY');

// Allowed origins for CORS (comma-separated list). Not a secret: a plain param
// read from functions/.env(.<project>) or prompted at deploy. Empty/unset denies
// all cross-origin browser requests (server-to-server calls are unaffected).
const allowedOriginsParam = defineString('ALLOWED_ORIGINS', {
  description: 'Comma-separated list of allowed origins for CORS',
  default: '',
});

// Rate limiting configuration (distributed via Firestore)
const RATE_LIMIT_MAX = 100; // requests per window, per API key, per endpoint
const RATE_LIMIT_WINDOW_MS = 60 * 60 * 1000; // 1 hour

// Failed-authentication throttling (per client IP)
const AUTH_FAIL_MAX = 10; // failed attempts per window
const AUTH_FAIL_WINDOW_MS = 15 * 60 * 1000; // 15 minutes

/**
 * Get allowed origins for CORS
 */
function getAllowedOrigins(): string[] | boolean {
  const originsStr = allowedOriginsParam.value();
  if (!originsStr) {
    // If no origins configured, deny all cross-origin requests in production
    return false;
  }
  const origins = originsStr.split(',').map((o) => o.trim()).filter((o) => o.length > 0);
  const validated = origins.filter((origin) => {
    if (origin === '*') {
      console.warn('CORS: Wildcard origin "*" rejected. Configure specific origins.');
      return false;
    }
    if (origin.startsWith('https://') || origin.startsWith('http://localhost')) {
      return true;
    }
    console.warn(`CORS: Invalid origin "${origin}" rejected. Must start with https:// or http://localhost.`);
    return false;
  });
  if (validated.length === 0) {
    console.warn('CORS: No valid origins after filtering. Denying all cross-origin requests.');
    return false;
  }
  return validated;
}

/**
 * Validate API key from request header (constant-time comparison).
 */
function validateApiKey(authHeader: string | undefined): boolean {
  const configuredKey = readSecret(recommendApiKey);

  // Reject all requests if API key is not configured
  if (!configuredKey) {
    console.error('CONFIGURATION ERROR: RECOMMEND_API_KEY secret not available. All API requests will be rejected.');
    return false;
  }

  if (!authHeader) {
    console.warn('Auth failure: no authorization header provided');
    return false;
  }

  const key = extractBearerKey(authHeader);
  if (!safeCompareKeys(key, configuredKey)) {
    const keyHash = createHash('sha256').update(key).digest('hex').slice(0, 8);
    console.warn(`Auth failure: invalid key (hash prefix: ${keyHash})`);
    return false;
  }
  return true;
}

function clientIp(req: Request): string {
  return deriveClientIp(req.headers['x-forwarded-for'], req.socket?.remoteAddress);
}

/**
 * Authenticate an HTTP request. The API key is validated first: a request with
 * a valid key is never blocked by the failed-auth throttle, and only failed
 * attempts touch Firestore (recording the failure and checking the per-IP
 * budget in one transaction). Sends the error response and returns false when
 * the request must not proceed.
 */
async function authenticate(req: Request, res: Response): Promise<boolean> {
  if (validateApiKey(req.headers.authorization)) return true;

  const failKey = `authfail:${clientIp(req)}`;
  const throttle = await checkRateLimit(failKey, AUTH_FAIL_MAX, AUTH_FAIL_WINDOW_MS);
  if (!throttle.allowed) {
    res.status(429).json({
      error: 'Too many failed attempts',
      message: 'Too many failed authentication attempts. Please try again later.',
    });
    return false;
  }

  res.status(401).json({
    error: 'Unauthorized',
    message: 'Invalid or missing API key. Use Authorization: Bearer <key>',
  });
  return false;
}

/**
 * Consume a rate-limit slot for (API key, endpoint). Each endpoint has its own
 * bucket so e.g. auto-saving generations doesn't eat the /recommend budget.
 */
async function consumeRateLimit(req: Request, res: Response, endpoint: string): Promise<boolean> {
  const rateLimitKey = `key:${endpoint}:${extractBearerKey(req.headers.authorization)}`;
  const rateLimit = await checkRateLimit(rateLimitKey, RATE_LIMIT_MAX, RATE_LIMIT_WINDOW_MS);
  res.setHeader('X-RateLimit-Remaining', rateLimit.remaining.toString());

  if (!rateLimit.allowed) {
    res.status(429).json({
      error: 'Rate limit exceeded',
      message: 'Too many requests. Please try again later.',
    });
    return false;
  }
  return true;
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
    secrets: [recommendApiKey, geminiApiKey],
  },
  async (req, res) => {
    // Only allow POST requests
    if (req.method !== 'POST') {
      res.status(405).json({ error: 'Method not allowed. Use POST.' });
      return;
    }

    if (!(await authenticate(req, res))) return;

    // Validate/sanitize before consuming a rate-limit slot
    const parsed = parseRecommendationInput(req.body);
    if (!parsed.ok) {
      res.status(400).json({ error: 'Invalid request', message: parsed.error });
      return;
    }

    if (!(await consumeRateLimit(req, res, 'recommend'))) return;

    try {
      const engine = new RecommendationEngine();
      const recommendation = await engine.generateRecommendation(parsed.value);
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

const CALLABLE_OPTIONS = {
  enforceAppCheck: true,        // Reject requests without a valid App Check token
  consumeAppCheckToken: false,
  secrets: [geminiApiKey],
};

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
  CALLABLE_OPTIONS,
  async (request) => {
    // Require authentication
    if (!request.auth) {
      throw new HttpsError(
        'unauthenticated',
        'Authentication required. Please sign in to use this service.'
      );
    }

    // Validate/sanitize before consuming a rate-limit slot
    const parsed = parseRecommendationInput(request.data);
    if (!parsed.ok) {
      throw new HttpsError('invalid-argument', parsed.error);
    }

    // Check rate limit using auth UID (distributed via Firestore)
    const rateLimit = await checkRateLimit(`uid:recommend:${request.auth.uid}`, RATE_LIMIT_MAX, RATE_LIMIT_WINDOW_MS);
    if (!rateLimit.allowed) {
      throw new HttpsError(
        'resource-exhausted',
        'Rate limit exceeded. Please try again later.'
      );
    }

    try {
      const engine = new RecommendationEngine();
      return await engine.generateRecommendation(parsed.value);
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
    secrets: [recommendApiKey, geminiApiKey],
  },
  async (req, res) => {
    if (req.method !== 'POST') {
      res.status(405).json({ error: 'Method not allowed. Use POST.' });
      return;
    }

    if (!(await authenticate(req, res))) return;

    const parsed = parseIdeasInput(req.body);
    if (!parsed.ok) {
      res.status(400).json({ error: 'Invalid request', message: parsed.error });
      return;
    }

    if (!(await consumeRateLimit(req, res, 'ideas'))) return;

    try {
      const engine = new RecommendationEngine();
      const response = await engine.generateIdeas(parsed.value.type);
      res.status(200).json(response);
    } catch (error) {
      console.error('Ideas generation error:', error);
      res.status(500).json({
        error: 'Internal server error',
        message: 'Failed to generate ideas',
      });
    }
  }
);

// ============================================
// Ideas Callable Function
// ============================================

/**
 * Callable function for generating video ideas
 */
export const getIdeas = onCall<unknown, Promise<IdeaGenerationResponse>>(
  CALLABLE_OPTIONS,
  async (request) => {
    if (!request.auth) {
      throw new HttpsError(
        'unauthenticated',
        'Authentication required. Please sign in to use this service.'
      );
    }

    const parsed = parseIdeasInput(request.data);
    if (!parsed.ok) {
      throw new HttpsError('invalid-argument', parsed.error);
    }

    const rateLimit = await checkRateLimit(`uid:ideas:${request.auth.uid}`, RATE_LIMIT_MAX, RATE_LIMIT_WINDOW_MS);
    if (!rateLimit.allowed) {
      throw new HttpsError(
        'resource-exhausted',
        'Rate limit exceeded. Please try again later.'
      );
    }

    try {
      const engine = new RecommendationEngine();
      return await engine.generateIdeas(parsed.value.type);
    } catch (error) {
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
 * POST /generations-save
 * Body: { type: 'ideas' | 'recommendation', request: object, response: object } (max 100KB)
 * Returns: { id, savedAt }
 */
export const generationsSave = onRequest(
  {
    cors: getAllowedOrigins(),
    secrets: [recommendApiKey],
  },
  async (req, res) => {
    if (req.method !== 'POST') {
      res.status(405).json({ error: 'Method not allowed. Use POST.' });
      return;
    }

    if (!(await authenticate(req, res))) return;

    const payload = validateGenerationPayload(req.body);
    if (!payload.ok) {
      res.status(400).json({ error: payload.error });
      return;
    }

    if (!(await consumeRateLimit(req, res, 'generations-save'))) return;

    try {
      const result = await saveGen(payload.value);
      res.status(200).json(result);
    } catch (error) {
      console.error('Save generation error:', error);
      res.status(500).json({ error: 'Failed to save generation' });
    }
  }
);

/**
 * GET /generations-list
 * Query: ?type=ideas|recommendation (optional)
 * Returns: { generations: [...] }
 */
export const generationsList = onRequest(
  {
    cors: getAllowedOrigins(),
    secrets: [recommendApiKey],
  },
  async (req, res) => {
    if (req.method !== 'GET') {
      res.status(405).json({ error: 'Method not allowed. Use GET.' });
      return;
    }

    if (!(await authenticate(req, res))) return;
    if (!(await consumeRateLimit(req, res, 'generations-list'))) return;

    try {
      const typeParam = req.query.type;
      let type: 'ideas' | 'recommendation' | undefined;
      if (typeParam === 'ideas' || typeParam === 'recommendation') {
        type = typeParam;
      }

      const generations = await listGens(type);
      res.status(200).json({ generations });
    } catch (error) {
      console.error('List generations error:', error);
      res.status(500).json({ error: 'Failed to list generations' });
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
 * Returns { status, timestamp, version, geminiConfigured } — never secret values.
 */
export const health = onRequest(
  {
    secrets: [geminiApiKey],
  },
  async (req, res) => {
    if (req.method !== 'GET') {
      res.status(405).json({ error: 'Method not allowed. Use GET.' });
      return;
    }

    try {
      const geminiConfigured = isGeminiConfigured();
      if (!geminiConfigured) {
        console.error('CONFIGURATION ERROR: GOOGLE_API_KEY secret not available; recommendations use template fallback.');
      }
      res.status(200).json({
        status: 'ok',
        timestamp: new Date().toISOString(),
        version: '1.0.0',
        geminiConfigured,
      });
    } catch (error) {
      res.status(500).json({
        status: 'error',
        message: 'Internal server error',
      });
    }
  }
);

// ============================================
// Re-export types for consumers
// ============================================

export type {
  RecommendationRequest,
  RecommendationResponse,
  IdeaGenerationResponse,
  ContentType,
} from './types';
