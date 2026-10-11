import type { RecommendationRequest } from './types';
import type { GenerationDoc } from './firebase';
import { sanitizeInput, VALID_CONTENT_TYPES, MAX_TOPIC_LENGTH, MAX_ANGLE_LENGTH, MAX_AUDIENCE_LENGTH } from './recommendation-core';
import { isRecord, isContentType } from './response-validation';

export class InvalidRequest extends Error {}

function parseObject(value: unknown): Record<string, unknown> {
  if (!isRecord(value)) throw new InvalidRequest('Request must be a JSON object');
  return value;
}

function parseString(value: unknown, field: string, maxLength: number): string | undefined {
  if (value === undefined) return undefined;
  if (typeof value !== 'string') throw new InvalidRequest(`${field} must be a string`);
  return sanitizeInput(value, maxLength);
}

export function parseIdeasRequest(value: unknown): Pick<RecommendationRequest, 'type'> {
  const { type } = parseObject(value);
  if (type === undefined) return {};
  if (!isContentType(type)) throw new InvalidRequest(`Invalid content type. Must be one of: ${VALID_CONTENT_TYPES.join(', ')}`);
  return { type };
}

export function parseRecommendationRequest(value: unknown): RecommendationRequest {
  const body = parseObject(value);
  const topic = parseString(body.topic, 'Topic', MAX_TOPIC_LENGTH);
  if (!topic) throw new InvalidRequest('Topic is required and must be a non-empty string');
  return {
    topic,
    ...parseIdeasRequest(body),
    angle: parseString(body.angle, 'Angle', MAX_ANGLE_LENGTH) || undefined,
    audience: parseString(body.audience, 'Audience', MAX_AUDIENCE_LENGTH) || undefined,
  };
}

export function parseGenerationType(value: unknown): GenerationDoc['type'] | undefined {
  if (value === undefined) return undefined;
  if (value !== 'ideas' && value !== 'recommendation') throw new InvalidRequest('Invalid type. Must be "ideas" or "recommendation".');
  return value;
}

export function parseGenerationRequest(value: unknown): Omit<GenerationDoc, 'savedAt'> {
  const body = parseObject(value);
  const type = parseGenerationType(body.type);
  if (!type) throw new InvalidRequest('Type is required');
  if (!isRecord(body.request) || !isRecord(body.response)) {
    throw new InvalidRequest('Both request and response must be JSON objects.');
  }
  return { type, request: body.request, response: body.response };
}
