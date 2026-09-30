/**
 * Pure request validation helpers for the HTTP / callable endpoints.
 *
 * No Firebase dependencies so they can be unit-tested directly.
 */

import { createHash, timingSafeEqual } from 'crypto';
import type { ContentType } from './types';
import {
  sanitizeInput,
  InputValidationError,
  VALID_CONTENT_TYPES,
  MAX_TOPIC_LENGTH,
  MAX_ANGLE_LENGTH,
  MAX_AUDIENCE_LENGTH,
} from './recommendation-core';

export type ValidationResult<T> = { ok: true; value: T } | { ok: false; error: string };

// ============================================
// API key comparison
// ============================================

/**
 * Constant-time API key comparison.
 *
 * Both values are hashed to fixed-length SHA-256 digests first so
 * timingSafeEqual never throws on length mismatch and the comparison time
 * doesn't leak the configured key's length. An empty expected key never matches.
 */
export function safeCompareKeys(provided: string, expected: string): boolean {
  if (!expected) return false;
  const a = createHash('sha256').update(provided, 'utf8').digest();
  const b = createHash('sha256').update(expected, 'utf8').digest();
  return timingSafeEqual(a, b);
}

/**
 * Extract the raw API key from an Authorization header.
 */
export function extractBearerKey(authHeader: string | undefined): string {
  if (!authHeader) return '';
  return authHeader.startsWith('Bearer ') ? authHeader.slice(7) : authHeader;
}

// ============================================
// Client IP derivation (failed-auth throttle key)
// ============================================

/**
 * Derive the client IP used to key the failed-auth throttle.
 *
 * Cloud Functions v2 runs on Cloud Run behind Google's front end (GFE), which
 * APPENDS the address of the peer it received the connection from to
 * X-Forwarded-For. Anything to the left of that entry is client-supplied and
 * spoofable, so we take the RIGHT-MOST entry rather than req.ip (whose value
 * depends on Express `trust proxy` and may be the left-most, spoofable hop).
 * Without the header (local emulator / direct connection) fall back to the
 * socket peer address.
 */
export function deriveClientIp(
  forwardedFor: string | string[] | undefined,
  remoteAddress: string | undefined
): string {
  const raw = Array.isArray(forwardedFor) ? forwardedFor.join(',') : forwardedFor;
  if (raw) {
    const hops = raw
      .split(',')
      .map((h) => h.trim())
      .filter((h) => h.length > 0);
    if (hops.length > 0) return hops[hops.length - 1];
  }
  return remoteAddress || 'unknown';
}

// ============================================
// Recommendation / ideas input
// ============================================

export function isValidContentType(type: unknown): type is ContentType {
  return typeof type === 'string' && VALID_CONTENT_TYPES.includes(type as ContentType);
}

export interface ParsedRecommendationInput {
  topic: string;
  type: ContentType;
  angle: string | undefined;
  audience: string;
}

/**
 * Validate and sanitize a recommendation request body (untrusted JSON).
 * Runs before any rate-limit slot is consumed.
 */
export function parseRecommendationInput(data: unknown): ValidationResult<ParsedRecommendationInput> {
  if (typeof data !== 'object' || data === null || Array.isArray(data)) {
    return { ok: false, error: 'Request body must be a JSON object' };
  }
  const body = data as Record<string, unknown>;

  let topic: string;
  let angle: string;
  let audience: string;
  try {
    topic = sanitizeInput(body.topic, MAX_TOPIC_LENGTH, 'topic');
    angle = sanitizeInput(body.angle, MAX_ANGLE_LENGTH, 'angle');
    audience = sanitizeInput(body.audience, MAX_AUDIENCE_LENGTH, 'audience');
  } catch (error) {
    if (error instanceof InputValidationError) return { ok: false, error: error.message };
    throw error;
  }

  if (!topic) {
    return { ok: false, error: 'Topic is required and must be a non-empty string' };
  }

  const typeResult = parseOptionalContentType(body.type);
  if (!typeResult.ok) return typeResult;

  return {
    ok: true,
    value: {
      topic,
      type: typeResult.value || 'recipe',
      angle: angle || undefined,
      audience: audience || 'Telugu audience',
    },
  };
}

/**
 * Validate an ideas request body: `{ type?: ContentType }`.
 * A missing/empty body is allowed (all types).
 */
export function parseIdeasInput(data: unknown): ValidationResult<{ type: ContentType | undefined }> {
  if (data === undefined || data === null || data === '') {
    return { ok: true, value: { type: undefined } };
  }
  if (typeof data !== 'object' || Array.isArray(data)) {
    return { ok: false, error: 'Request body must be a JSON object' };
  }
  const typeResult = parseOptionalContentType((data as Record<string, unknown>).type);
  if (!typeResult.ok) return typeResult;
  return { ok: true, value: { type: typeResult.value } };
}

function parseOptionalContentType(type: unknown): ValidationResult<ContentType | undefined> {
  if (type === undefined || type === null || type === '') return { ok: true, value: undefined };
  if (!isValidContentType(type)) {
    return { ok: false, error: `Invalid content type. Must be one of: ${VALID_CONTENT_TYPES.join(', ')}` };
  }
  return { ok: true, value: type };
}

// ============================================
// Generation save payload
// ============================================

export const GENERATION_TYPES = ['ideas', 'recommendation'] as const;
export type GenerationType = typeof GENERATION_TYPES[number];

/** Max serialized size of a saved generation (request + response), in bytes. */
export const MAX_GENERATION_BYTES = 100 * 1024;

export interface GenerationPayload {
  type: GenerationType;
  request: Record<string, unknown>;
  response: Record<string, unknown>;
}

function isPlainJsonObject(value: unknown): value is Record<string, unknown> {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) return false;
  const proto = Object.getPrototypeOf(value);
  return proto === Object.prototype || proto === null;
}

/**
 * Validate a /generations-save body: type in the allowed set, request/response
 * plain objects, total serialized size capped at MAX_GENERATION_BYTES.
 */
export function validateGenerationPayload(body: unknown): ValidationResult<GenerationPayload> {
  if (!isPlainJsonObject(body)) {
    return { ok: false, error: 'Request body must be a JSON object' };
  }
  const { type, request, response } = body;

  if (typeof type !== 'string' || !(GENERATION_TYPES as readonly string[]).includes(type)) {
    return { ok: false, error: 'Invalid type. Must be "ideas" or "recommendation".' };
  }
  if (!isPlainJsonObject(request) || !isPlainJsonObject(response)) {
    return { ok: false, error: 'Both request and response fields are required and must be JSON objects.' };
  }

  let size: number;
  try {
    size = Buffer.byteLength(JSON.stringify({ request, response }), 'utf8');
  } catch {
    return { ok: false, error: 'Payload is not serializable JSON.' };
  }
  if (size > MAX_GENERATION_BYTES) {
    return { ok: false, error: `Payload too large (${size} bytes; max ${MAX_GENERATION_BYTES}).` };
  }

  return { ok: true, value: { type: type as GenerationType, request, response } };
}
