import type {
  ContentType, TitleSuggestion, TitleRecommendations, ThumbnailRecommendation,
  TextElement, PostingRecommendation, PerformancePrediction, ProductionToolkit, VideoIdea,
  TimingInsights,
} from './types';

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

export function isContentType(value: unknown): value is ContentType {
  return value === 'recipe' || value === 'vlog' || value === 'tutorial' || value === 'review' || value === 'challenge';
}

export function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item: unknown) => typeof item === 'string');
}

function hasStrings(value: Record<string, unknown>, ...keys: string[]): boolean {
  return keys.every((key) => typeof value[key] === 'string');
}

function optionalString(value: unknown): boolean {
  return value === undefined || typeof value === 'string';
}

function optionalBoolean(value: unknown): boolean {
  return value === undefined || typeof value === 'boolean';
}

function isNonnegativeNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value) && value >= 0;
}

function isHexColor(value: unknown): boolean {
  return typeof value === 'string' && /^#(?:[0-9a-f]{3}|[0-9a-f]{6})$/i.test(value);
}

function isTitle(value: unknown): value is TitleSuggestion {
  return isRecord(value) && hasStrings(value, 'combined', 'reasoning') &&
    optionalString(value.english) && optionalString(value.telugu) &&
    ['below-average', 'average', 'above-average', 'high'].some((ctr) => ctr === value.predictedCTR);
}

export function isTitles(value: unknown): value is TitleRecommendations {
  return isRecord(value) && isTitle(value.primary) &&
    Array.isArray(value.alternatives) && value.alternatives.every(isTitle);
}

function isTextElement(value: unknown): value is TextElement {
  return isRecord(value) && hasStrings(value, 'content', 'position', 'color') &&
    isHexColor(value.color) && optionalString(value.style) && optionalString(value.language);
}

export function isThumbnail(value: unknown): value is ThumbnailRecommendation {
  if (!isRecord(value) || !isRecord(value.layout) || !hasStrings(value.layout, 'type', 'description') ||
      !isRecord(value.elements) || !isRecord(value.colors)) return false;
  const { face, mainVisual, text, graphics } = value.elements;
  return isRecord(face) && hasStrings(face, 'expression', 'position', 'size') &&
    typeof face.required === 'boolean' && typeof face.eyeContact === 'boolean' &&
    isRecord(mainVisual) && hasStrings(mainVisual, 'type', 'position') &&
    optionalBoolean(mainVisual.showSteam) && optionalBoolean(mainVisual.garnished) &&
    isRecord(text) && isTextElement(text.primary) &&
    (text.secondary === undefined || isTextElement(text.secondary)) &&
    isRecord(graphics) && typeof graphics.addArrow === 'boolean' && typeof graphics.addBorder === 'boolean' &&
    optionalString(graphics.arrowPointTo) && optionalString(graphics.borderColor) &&
    isHexColor(value.colors.background) && isHexColor(value.colors.accent) && isHexColor(value.colors.text) &&
    (value.referenceExamples === undefined || (Array.isArray(value.referenceExamples) &&
      value.referenceExamples.every((item: unknown) => isRecord(item) && hasStrings(item, 'videoId', 'reason'))));
}

export function isPosting(value: unknown): value is PostingRecommendation {
  return isRecord(value) && hasStrings(value, 'bestDay', 'bestTime', 'reasoning') && isStringArray(value.alternativeTimes);
}

export function isPrediction(value: unknown): value is PerformancePrediction {
  if (!isRecord(value) || !isRecord(value.expectedViewRange)) return false;
  const { low, medium, high } = value.expectedViewRange;
  return isNonnegativeNumber(low) && isNonnegativeNumber(medium) && isNonnegativeNumber(high) &&
    low <= medium && medium <= high && ['low', 'medium', 'high'].some((confidence) => confidence === value.confidence) &&
    isStringArray(value.positiveFactors) && isStringArray(value.riskFactors);
}

export function isProduction(value: unknown): value is ProductionToolkit {
  return isRecord(value) && hasStrings(value, 'optimalDuration', 'pinnedComment', 'seoDescription', 'endScreenScript') &&
    Array.isArray(value.hookScript) && value.hookScript.every((line: unknown) =>
      isRecord(line) && hasStrings(line, 'visual', 'dialogue', 'duration')) &&
    Array.isArray(value.segments) && value.segments.every((segment: unknown) =>
      isRecord(segment) && hasStrings(segment, 'startTime', 'endTime', 'title', 'description') && optionalString(segment.tips)) &&
    Array.isArray(value.shotList) && value.shotList.every((shot: unknown) =>
      isRecord(shot) && hasStrings(shot, 'type', 'description', 'timing'));
}

function isVideoIdea(value: unknown): value is VideoIdea {
  return isRecord(value) && hasStrings(value, 'topic', 'angle', 'whyItWorks') &&
    isNonnegativeNumber(value.opportunityScore) && value.opportunityScore >= 1 && value.opportunityScore <= 100 &&
    isContentType(value.suggestedType) && isStringArray(value.keywords);
}

export function parseIdeas(value: unknown, type?: ContentType): VideoIdea[] {
  if (!isRecord(value) || !Array.isArray(value.ideas) || value.ideas.length === 0 ||
      !value.ideas.every(isVideoIdea) || (type && value.ideas.some((idea) => idea.suggestedType !== type))) {
    throw new Error('Invalid ideas in AI response');
  }
  return value.ideas;
}

export function isOptimalTiming(value: unknown): value is TimingInsights['bestTimes']['optimal'] {
  return isRecord(value) && typeof value.day === 'string' &&
    ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'].includes(value.day) &&
    typeof value.hourIST === 'number' && Number.isInteger(value.hourIST) && value.hourIST >= 0 && value.hourIST < 24 &&
    isNonnegativeNumber(value.multiplier) && optionalString(value.description);
}

export function parseSection<T>(value: unknown, fallback: T, valid: (value: unknown) => value is T, name: string): T {
  if (value === undefined) return fallback;
  if (!valid(value)) throw new Error(`Invalid ${name} in AI response`);
  return value;
}

export function cleanJsonResponse(text: string): string {
  let cleaned = text.trim();
  while (cleaned.startsWith('```')) {
    cleaned = cleaned.slice(3).replace(/^[a-z][\w-]*(?=\s|[\[{])/i, '').trimStart();
  }
  while (cleaned.endsWith('```')) cleaned = cleaned.slice(0, -3).trimEnd();
  return cleaned.trim();
}
