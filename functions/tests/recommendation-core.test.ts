import {
  sanitizeInput,
  escapeForPrompt,
  resolveContentType,
  validateTags,
  getPostingRecommendation,
  generatePrediction,
  generateTitlesFromTemplates,
  generateThumbnailFromTemplates,
  generateTagsFromTemplates,
  generateFromTemplates,
  generateIdeasFromTemplates,
  validateAndFillResponse,
  buildContext,
  buildIdeasContext,
  MAX_TOPIC_LENGTH,
  VALID_CONTENT_TYPES,
} from '../src/recommendation-core';

import type { Insights } from '../src/types';

// ============================================
// Test Fixtures
// ============================================

const emptyInsights: Insights = {};

const fullInsights: Insights = {
  thumbnails: {
    generatedAt: '2024-01-01',
    basedOnVideos: 500,
    topPerformingElements: {
      composition: [
        { element: 'split-frame', lift: 2.3 },
        { element: 'close-up', lift: 1.8 },
      ],
      colors: [{ element: 'yellow-text', lift: 1.9 }],
    },
  },
  titles: {
    generatedAt: '2024-01-01',
    basedOnVideos: 500,
    powerWords: {
      highImpact: [
        { word: 'SECRET', telugu: 'రహస్యం', multiplier: 2.1 },
        { word: 'PERFECT', multiplier: 1.8 },
      ],
    },
    winningPatterns: [
      { pattern: 'Question + Answer', avgViews: 50000, sampleSize: 20, examples: ['How to make perfect biryani?'] },
    ],
  },
  timing: {
    generatedAt: '2024-01-01',
    basedOnVideos: 500,
    bestTimes: {
      byDayOfWeek: [
        { day: 'Saturday', avgViews: 60000, multiplier: 1.5 },
        { day: 'Sunday', avgViews: 55000, multiplier: 1.3 },
        { day: 'Friday', avgViews: 50000, multiplier: 1.1 },
      ],
      byHourIST: [{ hour: 18, avgViews: 60000, multiplier: 1.5 }],
      optimal: { day: 'Saturday', hourIST: 18, multiplier: 1.5 },
    },
  },
  contentGaps: {
    generatedAt: '2024-01-01',
    highOpportunity: [
      { topic: 'Millet Recipes', avgViews: 80000, videoCount: 5, opportunityScore: 85 },
      { topic: 'Street Food Tours', avgViews: 60000, videoCount: 8, opportunityScore: 72 },
    ],
    saturatedTopics: [
      { topic: 'Biryani', competition: 'high' },
      { topic: 'Chicken Curry', competition: 'high' },
    ],
    keywordGaps: {
      highValueKeywords: [
        { keyword: 'millet', avgViewsPerSubscriber: 2.0, viewsMultiplier: 3.1, usageCount: 5, usageRate: 0.02 },
        { keyword: 'street food', avgViewsPerSubscriber: 1.5, viewsMultiplier: 2.5, usageCount: 10, usageRate: 0.05 },
      ],
    },
    formatGaps: {
      formatPerformance: [
        { format: 'challenge', avgViewsPerSubscriber: 2.5, viewsMultiplier: 2.0, count: 10, usagePercent: 5 },
      ],
      recommendedFormats: [
        { format: 'challenge', avgViewsPerSubscriber: 2.5, viewsMultiplier: 2.0, count: 10, usagePercent: 5 },
      ],
    },
  },
};

// ============================================
// sanitizeInput
// ============================================

describe('sanitizeInput', () => {
  it('returns empty string for undefined', () => {
    expect(sanitizeInput(undefined, 100)).toBe('');
  });

  it('returns empty string for empty string', () => {
    expect(sanitizeInput('', 100)).toBe('');
  });

  it('trims whitespace', () => {
    expect(sanitizeInput('  hello  ', 100)).toBe('hello');
  });

  it('collapses multiple spaces', () => {
    expect(sanitizeInput('hello   world', 100)).toBe('hello world');
  });

  it('removes control characters', () => {
    expect(sanitizeInput('hello\x00\x01world', 100)).toBe('helloworld');
  });

  it('truncates to maxLength', () => {
    const long = 'a'.repeat(300);
    expect(sanitizeInput(long, MAX_TOPIC_LENGTH).length).toBe(MAX_TOPIC_LENGTH);
  });

  it('handles normal input unchanged', () => {
    expect(sanitizeInput('Hyderabadi Biryani', 200)).toBe('Hyderabadi Biryani');
  });
});

// ============================================
// escapeForPrompt
// ============================================

describe('escapeForPrompt', () => {
  it('removes triple backticks', () => {
    expect(escapeForPrompt('hello ```code``` world')).toBe('hello code world');
  });

  it('removes angle brackets', () => {
    expect(escapeForPrompt('hello <script> world')).toBe('hello script world');
  });

  it('collapses excessive newlines', () => {
    expect(escapeForPrompt('a\n\n\n\nb')).toBe('a\n\nb');
  });

  it('truncates to 500 chars', () => {
    const long = 'x'.repeat(600);
    expect(escapeForPrompt(long).length).toBe(500);
  });
});

// ============================================
// resolveContentType
// ============================================

describe('resolveContentType', () => {
  it('defaults to recipe when undefined', () => {
    expect(resolveContentType(undefined)).toBe('recipe');
  });

  it('returns valid types as-is', () => {
    for (const t of VALID_CONTENT_TYPES) {
      expect(resolveContentType(t)).toBe(t);
    }
  });

  it('is case-insensitive', () => {
    expect(resolveContentType('RECIPE')).toBe('recipe');
    expect(resolveContentType('Vlog')).toBe('vlog');
  });

  it('resolves aliases', () => {
    expect(resolveContentType('cooking')).toBe('recipe');
    expect(resolveContentType('food')).toBe('recipe');
    expect(resolveContentType('travel')).toBe('vlog');
    expect(resolveContentType('howto')).toBe('tutorial');
    expect(resolveContentType('how-to')).toBe('tutorial');
    expect(resolveContentType('unboxing')).toBe('review');
    expect(resolveContentType('guide')).toBe('tutorial');
  });

  it('defaults unknown types to recipe', () => {
    expect(resolveContentType('unknown')).toBe('recipe');
    expect(resolveContentType('random')).toBe('recipe');
  });
});

// ============================================
// validateTags
// ============================================

describe('validateTags', () => {
  it('fills missing tags with defaults', () => {
    const result = validateTags(undefined, 'recipe');
    expect(result.primary.length).toBeGreaterThan(0);
    expect(result.secondary.length).toBeGreaterThan(0);
    expect(result.telugu.length).toBeGreaterThan(0);
    expect(result.fullTagString).toBeTruthy();
    expect(result.characterCount).toBeGreaterThan(0);
    expect(result.utilizationPercent).toBeGreaterThanOrEqual(0);
    expect(result.utilizationPercent).toBeLessThanOrEqual(100);
  });

  it('preserves provided tags', () => {
    const input = { primary: ['test1'], secondary: ['test2'], telugu: ['test3'], longtail: ['test4'], brand: ['test5'] };
    const result = validateTags(input, 'recipe');
    expect(result.primary).toEqual(['test1']);
    expect(result.secondary).toEqual(['test2']);
    expect(result.brand).toEqual(['test5']);
  });

  it('calculates character count and utilization', () => {
    const input = { primary: ['tag1', 'tag2'], secondary: [], telugu: [], longtail: [], brand: [] };
    const result = validateTags(input, 'recipe');
    expect(result.fullTagString).toBe('tag1, tag2');
    expect(result.characterCount).toBe(10);
    expect(result.utilizationPercent).toBeCloseTo((10 / 500) * 100, 1);
  });

  it('caps utilization at 100%', () => {
    const longTags = { primary: Array(50).fill('a'.repeat(20)) };
    const result = validateTags(longTags, 'recipe');
    expect(result.utilizationPercent).toBeLessThanOrEqual(100);
  });
});

// ============================================
// getPostingRecommendation
// ============================================

describe('getPostingRecommendation', () => {
  it('returns default when no timing insights', () => {
    const result = getPostingRecommendation(emptyInsights);
    expect(result.bestDay).toBeTruthy();
    expect(result.bestTime).toBeTruthy();
    expect(result.reasoning).toBeTruthy();
  });

  it('uses insights timing when available', () => {
    const result = getPostingRecommendation(fullInsights);
    expect(result.bestDay).toBe('Saturday');
    expect(result.bestTime).toBe('18:00 IST');
    expect(result.reasoning).toContain('1.5x');
    expect(result.alternativeTimes.length).toBeGreaterThan(0);
  });

  it('excludes optimal day from alternatives', () => {
    const result = getPostingRecommendation(fullInsights);
    expect(result.alternativeTimes.every((t) => !t.startsWith('Saturday'))).toBe(true);
  });
});

// ============================================
// generatePrediction
// ============================================

describe('generatePrediction', () => {
  it('returns low confidence without insights version', () => {
    const result = generatePrediction('Biryani', 'recipe', emptyInsights, null);
    expect(result.confidence).toBe('low');
    expect(result.expectedViewRange.low).toBeGreaterThan(0);
  });

  it('returns medium confidence with insights version', () => {
    const result = generatePrediction('Biryani', 'recipe', fullInsights, 'v1');
    expect(result.confidence).toBe('medium');
  });

  it('flags saturated topics as risk', () => {
    const result = generatePrediction('Biryani', 'recipe', fullInsights, 'v1');
    expect(result.riskFactors.some((f) => f.toLowerCase().includes('saturated'))).toBe(true);
  });

  it('flags high opportunity topics as positive', () => {
    const result = generatePrediction('Millet Recipes', 'recipe', fullInsights, 'v1');
    expect(result.positiveFactors.some((f) => f.toLowerCase().includes('opportunity'))).toBe(true);
  });

  it('has different ranges per content type', () => {
    const recipe = generatePrediction('Test', 'recipe', emptyInsights, null);
    const challenge = generatePrediction('Test', 'challenge', emptyInsights, null);
    expect(challenge.expectedViewRange.high).toBeGreaterThan(recipe.expectedViewRange.high);
  });

  it('always includes base positive factors', () => {
    const result = generatePrediction('Test', 'recipe', emptyInsights, null);
    expect(result.positiveFactors.length).toBeGreaterThanOrEqual(2);
  });
});

// ============================================
// buildContext
// ============================================

describe('buildContext', () => {
  it('returns empty string for empty insights', () => {
    expect(buildContext(emptyInsights)).toBe('');
  });

  it('includes thumbnail elements', () => {
    const ctx = buildContext(fullInsights);
    expect(ctx).toContain('TOP PERFORMING THUMBNAIL ELEMENTS');
    expect(ctx).toContain('split-frame');
    expect(ctx).toContain('2.3x');
  });

  it('includes power words', () => {
    const ctx = buildContext(fullInsights);
    expect(ctx).toContain('TOP POWER WORDS');
    expect(ctx).toContain('SECRET');
  });

  it('includes winning patterns', () => {
    const ctx = buildContext(fullInsights);
    expect(ctx).toContain('WINNING TITLE PATTERNS');
    expect(ctx).toContain('Question + Answer');
  });

  it('includes optimal posting time', () => {
    const ctx = buildContext(fullInsights);
    expect(ctx).toContain('OPTIMAL POSTING');
    expect(ctx).toContain('Saturday');
  });

  it('includes content gaps', () => {
    const ctx = buildContext(fullInsights);
    expect(ctx).toContain('HIGH OPPORTUNITY TOPICS');
    expect(ctx).toContain('Millet Recipes');
    expect(ctx).toContain('SATURATED TOPICS');
    expect(ctx).toContain('Biryani');
  });
});

// ============================================
// buildIdeasContext
// ============================================

describe('buildIdeasContext', () => {
  it('returns empty string for empty insights', () => {
    expect(buildIdeasContext(emptyInsights)).toBe('');
  });

  it('includes high opportunity topics', () => {
    const ctx = buildIdeasContext(fullInsights);
    expect(ctx).toContain('HIGH OPPORTUNITY TOPICS');
    expect(ctx).toContain('Millet Recipes');
  });

  it('includes high value keywords', () => {
    const ctx = buildIdeasContext(fullInsights);
    expect(ctx).toContain('HIGH VALUE KEYWORDS');
    expect(ctx).toContain('millet');
  });

  it('includes format performance', () => {
    const ctx = buildIdeasContext(fullInsights);
    expect(ctx).toContain('FORMAT PERFORMANCE');
    expect(ctx).toContain('challenge');
  });

  it('includes saturated topics', () => {
    const ctx = buildIdeasContext(fullInsights);
    expect(ctx).toContain('SATURATED TOPICS');
    expect(ctx).toContain('Biryani');
  });
});

// ============================================
// Template Generation
// ============================================

describe('generateTitlesFromTemplates', () => {
  it('generates primary title with topic', () => {
    const result = generateTitlesFromTemplates('Biryani', 'recipe', undefined);
    expect(result.primary.combined).toContain('Biryani');
    expect(result.primary.predictedCTR).toBe('above-average');
  });

  it('generates 2 alternatives', () => {
    const result = generateTitlesFromTemplates('Biryani', 'recipe', undefined);
    expect(result.alternatives.length).toBe(2);
  });

  it('uses angle when provided', () => {
    const result = generateTitlesFromTemplates('Biryani', 'recipe', 'Restaurant Secret');
    expect(result.primary.english).toContain('Restaurant Secret');
  });

  it('works for all content types', () => {
    for (const type of VALID_CONTENT_TYPES) {
      const result = generateTitlesFromTemplates('Test', type, undefined);
      expect(result.primary.combined).toBeTruthy();
      expect(result.alternatives.length).toBe(2);
    }
  });
});

describe('generateThumbnailFromTemplates', () => {
  it('returns valid thumbnail spec', () => {
    const result = generateThumbnailFromTemplates('Biryani', 'recipe');
    expect(result.layout.type).toBeTruthy();
    expect(result.elements.face).toBeTruthy();
    expect(result.elements.mainVisual).toBeTruthy();
    expect(result.colors.background).toBeTruthy();
  });

  it('sets primary text to uppercase first word of topic', () => {
    const result = generateThumbnailFromTemplates('Chicken Biryani', 'recipe');
    expect(result.elements.text.primary.content).toBe('CHICKEN');
  });

  it('works for all content types', () => {
    for (const type of VALID_CONTENT_TYPES) {
      const result = generateThumbnailFromTemplates('Test', type);
      expect(result.layout).toBeTruthy();
      expect(result.colors).toBeTruthy();
    }
  });
});

describe('generateTagsFromTemplates', () => {
  it('includes topic in primary tags', () => {
    const result = generateTagsFromTemplates('Biryani', 'recipe');
    expect(result.primary).toContain('biryani');
    expect(result.primary).toContain('biryani recipe');
  });

  it('includes telugu tags in longtail', () => {
    const result = generateTagsFromTemplates('Biryani', 'recipe');
    expect(result.longtail.some((t) => t.includes('in telugu'))).toBe(true);
  });

  it('calculates character count', () => {
    const result = generateTagsFromTemplates('Biryani', 'recipe');
    expect(result.characterCount).toBe(result.fullTagString.length);
  });
});

describe('generateFromTemplates', () => {
  it('returns complete recommendation', () => {
    const result = generateFromTemplates('Biryani', 'recipe', undefined, 'Telugu audience', emptyInsights, null);
    expect(result.titles).toBeTruthy();
    expect(result.thumbnail).toBeTruthy();
    expect(result.tags).toBeTruthy();
    expect(result.posting).toBeTruthy();
    expect(result.prediction).toBeTruthy();
    expect(result.production).toBeTruthy();
    expect(result.metadata).toBeTruthy();
  });

  it('marks as fallback', () => {
    const result = generateFromTemplates('Biryani', 'recipe', undefined, 'Telugu audience', emptyInsights, null);
    expect(result.metadata.fallbackUsed).toBe(true);
    expect(result.metadata.modelUsed).toBe('template');
  });

  it('includes insights version in metadata', () => {
    const result = generateFromTemplates('Biryani', 'recipe', undefined, 'Telugu audience', fullInsights, 'v1');
    expect(result.metadata.insightsVersion).toBe('v1');
  });
});

// ============================================
// generateIdeasFromTemplates
// ============================================

describe('generateIdeasFromTemplates', () => {
  it('returns empty array with no insights', () => {
    const result = generateIdeasFromTemplates(undefined, emptyInsights);
    expect(result).toEqual([]);
  });

  it('generates ideas from high opportunity gaps', () => {
    const result = generateIdeasFromTemplates(undefined, fullInsights);
    expect(result.length).toBeGreaterThan(0);
    expect(result[0].topic).toBe('Millet Recipes');
    expect(result[0].opportunityScore).toBe(85);
  });

  it('pads with keyword-based ideas when gaps are few', () => {
    const sparseInsights: Insights = {
      contentGaps: {
        generatedAt: '2024-01-01',
        highOpportunity: [{ topic: 'Only One', avgViews: 100, videoCount: 1, opportunityScore: 90 }],
        saturatedTopics: [],
        keywordGaps: {
          highValueKeywords: [
            { keyword: 'test-kw', avgViewsPerSubscriber: 2, viewsMultiplier: 3, usageCount: 1, usageRate: 0.01 },
          ],
        },
      },
    };
    const result = generateIdeasFromTemplates(undefined, sparseInsights);
    expect(result.length).toBe(2);
    expect(result[1].topic).toBe('test-kw');
  });

  it('respects content type filter', () => {
    const result = generateIdeasFromTemplates('vlog', fullInsights);
    for (const idea of result) {
      expect(idea.suggestedType).toBe('vlog');
    }
  });
});

// ============================================
// validateAndFillResponse
// ============================================

describe('validateAndFillResponse', () => {
  it('fills missing fields from templates', () => {
    const result = validateAndFillResponse({}, 'Biryani', 'recipe', emptyInsights, null, 'gemini-2.5-flash');
    expect(result.titles).toBeTruthy();
    expect(result.thumbnail).toBeTruthy();
    expect(result.tags).toBeTruthy();
    expect(result.metadata.modelUsed).toBe('gemini-2.5-flash');
    expect(result.metadata.fallbackUsed).toBe(false);
  });

  it('preserves provided fields', () => {
    const titles = generateTitlesFromTemplates('Custom', 'vlog', undefined);
    const result = validateAndFillResponse({ titles }, 'Biryani', 'recipe', emptyInsights, null, 'gemini-2.5-flash');
    expect(result.titles).toBe(titles);
  });

  it('validates tags even when provided', () => {
    const partialTags = { primary: ['my-tag'] };
    const result = validateAndFillResponse(
      { tags: partialTags as any },
      'Biryani',
      'recipe',
      emptyInsights,
      null,
      'gemini-2.5-flash'
    );
    expect(result.tags.primary).toEqual(['my-tag']);
    expect(result.tags.fullTagString).toBeTruthy();
    expect(result.tags.characterCount).toBeGreaterThan(0);
  });
});
