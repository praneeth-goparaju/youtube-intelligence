import { RecommendationEngine } from '../src/engine';
import { generateWithGemini } from '../src/gemini';
import { getAllInsights } from '../src/firebase';
import {
  buildContext, buildIdeasContext, generateFromTemplates, generateIdeasFromTemplates,
  generateTagsFromTemplates, getPostingRecommendation, validateAndFillResponse, validateTags,
} from '../src/recommendation-core';
import { cleanJsonResponse } from '../src/response-validation';
import { formatIdeas, formatRecommendation } from '../src/formatter';
import type { Insights } from '../src/types';

jest.mock('../src/firebase', () => ({ getAllInsights: jest.fn() }));
jest.mock('../src/gemini', () => ({ generateWithGemini: jest.fn() }));

const insights: Insights = {
  thumbnails: { generatedAt: 'test', basedOnVideos: 10, topPerformingElements: {} },
  contentGaps: {
    generatedAt: 'test', saturatedTopics: [],
    highOpportunity: [{ topic: 'Biryani', avgViews: 100, videoCount: 2, opportunityScore: 85 }],
    keywordGaps: { highValueKeywords: [{ keyword: 'millet', avgViewsPerSubscriber: 2, viewsMultiplier: 3, usageCount: 2, usageRate: 2 }] },
  },
};
const valid = generateFromTemplates('Biryani', 'recipe', undefined, 'Telugu audience', {}, null);
const validIdea = { topic: 'Biryani', angle: 'Simple', whyItWorks: 'Demand', opportunityScore: 85, suggestedType: 'recipe', keywords: ['biryani'] };

beforeEach(() => {
  jest.mocked(getAllInsights).mockResolvedValue(insights);
  jest.spyOn(console, 'error').mockImplementation(() => {});
});
afterEach(() => jest.restoreAllMocks());

test.each([
  null, [], {}, { tags: {} }, { metadata: { modelUsed: 'test' } },
  { titles: {} }, { titles: { ...valid.titles, primary: { ...valid.titles.primary, combined: 3 } } },
  { thumbnail: {} }, { thumbnail: { ...valid.thumbnail, colors: { ...valid.thumbnail.colors, background: 'invalid' } } },
  { prediction: { ...valid.prediction, expectedViewRange: { low: 100, medium: 20, high: 3 } } },
  { production: {} }, { production: { ...valid.production, hookScript: [{ visual: 'Pan', dialogue: 'Hello', duration: 5 }] } },
  { production: { ...valid.production, shotList: [null] } }, { posting: {} }, { tags: { primary: 'biryani' } },
  { tags: { primary: [3] } },
])('malformed AI recommendation falls back to a renderable response: %j', async (data) => {
  jest.mocked(generateWithGemini).mockResolvedValue(JSON.stringify(data));
  const response = await new RecommendationEngine().generateRecommendation({ topic: 'Biryani' });
  expect(response.metadata.fallbackUsed).toBe(true);
  expect(() => formatRecommendation(response)).not.toThrow();
});

test.each([
  { ideas: 'wrong-shape' }, { ideas: {} }, { ideas: [] }, { ideas: [null] },
  { ideas: [{ ...validIdea, keywords: null }] }, { ideas: [{ ...validIdea, suggestedType: 'invalid' }] },
  { ideas: [{ ...validIdea, opportunityScore: 101 }] }, { ideas: [{ ...validIdea, suggestedType: 'vlog' }] },
])('malformed AI ideas fall back to a renderable response: %j', async (data) => {
  jest.mocked(generateWithGemini).mockResolvedValue(JSON.stringify(data));
  const response = await new RecommendationEngine().generateIdeas('recipe');
  expect(response.metadata.fallbackUsed).toBe(true);
  expect(response.ideas.length).toBeGreaterThan(0);
  expect(() => formatIdeas(response)).not.toThrow();
});

test('valid AI output remains intact and renderable', async () => {
  jest.mocked(generateWithGemini).mockResolvedValue(JSON.stringify(valid));
  const response = await new RecommendationEngine().generateRecommendation({ topic: 'Biryani' });
  expect(response.metadata.fallbackUsed).toBe(false);
  expect(response.titles).toEqual(valid.titles);
  expect(() => formatRecommendation(response)).not.toThrow();
  jest.mocked(generateWithGemini).mockResolvedValue(JSON.stringify({ ideas: [validIdea] }));
  const ideas = await new RecommendationEngine().generateIdeas('recipe');
  expect(ideas.metadata.fallbackUsed).toBe(false);
  expect(ideas.ideas).toEqual([validIdea]);
});

test.each(['Restaurant Style Hyderabadi Chicken Biryani For Beginners', 'x'.repeat(200)])('fallback tags fit the limit for %s', (topic) => {
  const tags = generateTagsFromTemplates(topic, 'recipe');
  expect(tags.characterCount).toBe(tags.fullTagString.length);
  expect(tags.characterCount).toBeLessThanOrEqual(500);
  expect(tags.primary).toContain(topic.toLowerCase());
});

test('AI tags are deduplicated and bounded as complete tags', () => {
  const tags = validateTags({ primary: [' Biryani ', 'biryani', 'x'.repeat(501)], secondary: ['short'] }, 'recipe');
  expect(tags.primary).toEqual(['Biryani']);
  expect(tags.secondary).toEqual(['short']);
  expect(tags.characterCount).toBeLessThanOrEqual(500);
});

test.each([{}, { day: 'Monday' }, { day: 'Monday', hourIST: 25, multiplier: 2 }])('sparse timing uses defaults without disabling AI: %j', async (optimal) => {
  const sparse: Insights = JSON.parse(JSON.stringify({ timing: { generatedAt: 'test', basedOnVideos: 1, bestTimes: { optimal } } }));
  expect(buildContext(sparse)).not.toContain('OPTIMAL POSTING');
  expect(getPostingRecommendation(sparse)).toEqual(getPostingRecommendation({}));
  expect(() => validateAndFillResponse(valid, 'Biryani', 'recipe', sparse, null, 'test')).not.toThrow();
  jest.mocked(getAllInsights).mockResolvedValue(sparse);
  jest.mocked(generateWithGemini).mockResolvedValue(JSON.stringify(valid));
  const response = await new RecommendationEngine().generateRecommendation({ topic: 'Biryani' });
  expect(response.metadata.fallbackUsed).toBe(false);
});

test('keyword usage rates are already percentages', () => {
  expect(buildIdeasContext(insights)).toContain('2.0% usage');
  expect(buildIdeasContext(insights)).not.toContain('200.0%');
  expect(generateIdeasFromTemplates('recipe', insights)[1].whyItWorks).toContain('2% of videos');
});

test.each([
  '{"ok":true}', '```json\n{"ok":true}\n```', '```json{"ok":true}\n```',
  '```\n{"ok":true}\n```', '```JSON\n{"ok":true}\n```',
  '```json\n```json\n{"ok":true}\n```\n```',
])('JSON cleaning preserves the payload: %s', (text) => {
  expect(JSON.parse(cleanJsonResponse(text))).toEqual({ ok: true });
});
