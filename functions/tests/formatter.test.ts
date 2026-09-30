import { scoreTier, formatIdeas } from '../src/formatter';
import type { IdeaGenerationResponse } from '../src/types';

describe('scoreTier', () => {
  it('ranks insight-scale scores (small decimals) relative to each other', () => {
    const scores = [0.012, 0.3, 1.9];
    expect(scoreTier(1.9, scores)).toBe('high');
    expect(scoreTier(0.3, scores)).toBe('medium');
    expect(scoreTier(0.012, scores)).toBe('low');
  });

  it('ranks AI-scale scores the same way', () => {
    const scores = [95, 60, 20];
    expect(scoreTier(95, scores)).toBe('high');
    expect(scoreTier(20, scores)).toBe('low');
  });

  it('treats a single score or all-equal scores as high', () => {
    expect(scoreTier(0.05, [0.05])).toBe('high');
    expect(scoreTier(0.5, [0.5, 0.5])).toBe('high');
  });
});

describe('formatIdeas', () => {
  it('shows small scores with decimals instead of raw floats or 0', () => {
    const response: IdeaGenerationResponse = {
      ideas: [
        { topic: 'Millets', angle: 'a', whyItWorks: 'w', opportunityScore: 0.123456, suggestedType: 'recipe', keywords: [] },
      ],
      metadata: { generatedAt: 'now', modelUsed: 'template', insightsVersion: null, fallbackUsed: true },
    };
    const out = formatIdeas(response);
    expect(out).toContain('Score: 0.123');
    expect(out).not.toContain('0.123456');
  });
});
