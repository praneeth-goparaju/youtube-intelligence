/**
 * Shared HTTP middleware for the Recommendation API.
 *
 * Centralizes the cross-cutting concerns every public HTTP endpoint needs —
 * method enforcement, API-key authentication, and distributed rate limiting —
 * so that each endpoint applies them identically and none can accidentally
 * omit a security check. The pure helpers (timing-safe comparison, bearer
 * extraction, key validation, origin parsing) are exported independently so
 * they can be unit tested without a Functions runtime.
 */

import { createHash, timingSafeEqual } from 'crypto';
import type { Request } from 'firebase-functions/v2/https';
import type { Response } from 'express';
import { checkRateLimit } from './rate-limiter';

export interface RateLimitConfig {
  max: number;
  windowMs: number;
}

export interface HttpGuardOptions {
  /** HTTP method the endpoint accepts (all others get 405). */
  method: 'GET' | 'POST';
  /**
   * Lazily resolves the configured API key. Passed as a getter (not a value)
   * because Firebase params must be read at request time, not module load.
   */
  getApiKey: () => string;
  rateLimit: RateLimitConfig;
}

/**
 * Constant-time string equality.
 *
 * Hashes both inputs to a fixed 32-byte digest before comparing so that
 * `timingSafeEqual` never throws on length mismatch and the comparison leaks
 * neither the key's length nor how many leading characters matched.
 */
export function timingSafeEqualStr(a: string, b: string): boolean {
  const ha = createHash('sha256').update(a, 'utf8').digest();
  const hb = createHash('sha256').update(b, 'utf8').digest();
  return timingSafeEqual(ha, hb);
}

/**
 * Extract the raw API key from an Authorization header.
 * Accepts both "Bearer <key>" and a bare "<key>".
 */
export function extractBearerKey(authHeader: string | undefined): string {
  if (!authHeader) return '';
  return authHeader.startsWith('Bearer ') ? authHeader.slice(7) : authHeader;
}

/**
 * Validate the Authorization header against the configured key.
 *
 * Fails closed: an unset configured key rejects every request. The comparison
 * is constant-time to avoid leaking the key via response timing.
 */
export function validateApiKey(authHeader: string | undefined, configuredKey: string): boolean {
  // Reject all requests if the API key is not configured.
  if (!configuredKey) {
    console.error('RECOMMEND_API_KEY not configured. All API requests will be rejected.');
    return false;
  }

  if (!authHeader) {
    console.warn('Auth failure: no authorization header provided');
    return false;
  }

  const key = extractBearerKey(authHeader);
  if (!timingSafeEqualStr(key, configuredKey)) {
    const keyHash = createHash('sha256').update(key).digest('hex').slice(0, 8);
    console.warn(`Auth failure: invalid key (hash prefix: ${keyHash})`);
    return false;
  }
  return true;
}

/**
 * Parse and validate a comma-separated allowed-origins string into the value
 * expected by the Functions `cors` option.
 *
 * Returns `false` (deny all cross-origin requests) when nothing valid is
 * configured. A wildcard `*` is explicitly rejected, and every origin must be
 * `https://` or `http://localhost`.
 */
export function parseAllowedOrigins(originsStr: string): string[] | false {
  if (!originsStr) {
    // If no origins configured, deny all cross-origin requests in production.
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
 * Wrap an HTTP handler with the standard guards every public endpoint shares:
 * method enforcement → API-key auth → distributed rate limiting.
 *
 * The wrapped handler only runs once all guards pass; on the rate-limit path it
 * also sets the `X-RateLimit-Remaining` header. Guards short-circuit with the
 * same status codes and JSON bodies the endpoints used previously.
 */
export function withHttpGuards(
  options: HttpGuardOptions,
  handler: (req: Request, res: Response) => void | Promise<void>
): (req: Request, res: Response) => Promise<void> {
  return async (req: Request, res: Response): Promise<void> => {
    if (req.method !== options.method) {
      res.status(405).json({ error: `Method not allowed. Use ${options.method}.` });
      return;
    }

    if (!validateApiKey(req.headers.authorization, options.getApiKey())) {
      res.status(401).json({
        error: 'Unauthorized',
        message: 'Invalid or missing API key. Use Authorization: Bearer <key>',
      });
      return;
    }

    const rateLimitKey = `key:${extractBearerKey(req.headers.authorization)}`;
    const rateLimit = await checkRateLimit(rateLimitKey, options.rateLimit.max, options.rateLimit.windowMs);
    res.setHeader('X-RateLimit-Remaining', rateLimit.remaining.toString());

    if (!rateLimit.allowed) {
      res.status(429).json({
        error: 'Rate limit exceeded',
        message: 'Too many requests. Please try again later.',
      });
      return;
    }

    await handler(req, res);
  };
}
