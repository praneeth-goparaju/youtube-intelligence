import {
  safeCompareKeys,
  extractBearerKey,
  deriveClientIp,
  parseRecommendationInput,
  parseIdeasInput,
  validateGenerationPayload,
  MAX_GENERATION_BYTES,
} from '../src/request-validation';

describe('safeCompareKeys', () => {
  it.each([
    ['equal keys', 'abc123', 'abc123', true],
    ['different keys, same length', 'abc123', 'abc124', false],
    ['different lengths', 'abc', 'abc123', false],
    ['empty provided', '', 'abc123', false],
    ['empty expected never matches', '', '', false],
    ['unicode keys', 'ключ', 'ключ', true],
  ])('%s', (_label, provided, expected, result) => {
    expect(safeCompareKeys(provided, expected)).toBe(result);
  });
});

describe('extractBearerKey', () => {
  it.each([
    ['Bearer abc', 'abc'],
    ['abc', 'abc'],
    [undefined, ''],
  ])('%p -> %p', (header, expected) => {
    expect(extractBearerKey(header)).toBe(expected);
  });
});

describe('deriveClientIp', () => {
  it.each([
    ['right-most X-Forwarded-For hop (GFE-appended)', 'spoofed.1, 203.0.113.7', '10.0.0.1', '203.0.113.7'],
    ['single hop', '203.0.113.7', '10.0.0.1', '203.0.113.7'],
    ['whitespace and empty entries ignored', ' 1.1.1.1 ,  203.0.113.7 , ', undefined, '203.0.113.7'],
    ['array header joined', ['1.1.1.1', '203.0.113.7'], undefined, '203.0.113.7'],
    ['no header falls back to socket address', undefined, '10.0.0.1', '10.0.0.1'],
    ['blank header falls back to socket address', ' , ', '10.0.0.1', '10.0.0.1'],
    ['nothing available', undefined, undefined, 'unknown'],
  ] as const)('%s', (_label, xff, remote, expected) => {
    expect(deriveClientIp(xff as string | string[] | undefined, remote)).toBe(expected);
  });

  it('rotating the client-supplied prefix does not change the key', () => {
    expect(deriveClientIp('a, 203.0.113.7', undefined)).toBe(deriveClientIp('b, c, 203.0.113.7', undefined));
  });
});

describe('parseRecommendationInput', () => {
  it('sanitizes and applies defaults', () => {
    const result = parseRecommendationInput({ topic: '  Biryani\nrecipe ' });
    expect(result).toEqual({
      ok: true,
      value: { topic: 'Biryani recipe', type: 'recipe', angle: undefined, audience: 'Telugu audience' },
    });
  });

  it('keeps valid type, angle and audience', () => {
    const result = parseRecommendationInput({ topic: 'Goa', type: 'vlog', angle: 'budget', audience: 'students' });
    expect(result.ok && result.value).toEqual({ topic: 'Goa', type: 'vlog', angle: 'budget', audience: 'students' });
  });

  it.each([
    ['non-object body', 'topic=x', 'JSON object'],
    ['null body', null, 'JSON object'],
    ['array body', [1], 'JSON object'],
    ['missing topic', {}, 'Topic is required'],
    ['whitespace topic', { topic: '  \n ' }, 'Topic is required'],
    ['numeric topic', { topic: 42 }, 'topic must be a string'],
    ['object angle', { topic: 'x', angle: { a: 1 } }, 'angle must be a string'],
    ['array audience', { topic: 'x', audience: ['a'] }, 'audience must be a string'],
    ['invalid type', { topic: 'x', type: 'podcast' }, 'Invalid content type'],
    ['non-string type', { topic: 'x', type: 5 }, 'Invalid content type'],
  ])('rejects %s', (_label, body, message) => {
    const result = parseRecommendationInput(body);
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error).toContain(message);
  });
});

describe('parseIdeasInput', () => {
  it.each([
    ['undefined body', undefined, undefined],
    ['empty object', {}, undefined],
    ['valid type', { type: 'review' }, 'review'],
  ])('accepts %s', (_label, body, type) => {
    expect(parseIdeasInput(body)).toEqual({ ok: true, value: { type } });
  });

  it.each([
    ['invalid type', { type: 'podcast' }],
    ['array body', ['recipe']],
    ['string body', 'recipe'],
  ])('rejects %s', (_label, body) => {
    expect(parseIdeasInput(body).ok).toBe(false);
  });
});

describe('validateGenerationPayload', () => {
  const valid = { type: 'ideas', request: { type: 'recipe' }, response: { ideas: [] } };

  it('accepts a valid payload', () => {
    expect(validateGenerationPayload(valid)).toEqual({ ok: true, value: valid });
  });

  it.each([
    ['non-object body', 'x', 'JSON object'],
    ['unknown type', { ...valid, type: 'other' }, 'Invalid type'],
    ['missing request', { type: 'ideas', response: {} }, 'request and response'],
    ['array request', { ...valid, request: [] }, 'request and response'],
    ['string response', { ...valid, response: 'x' }, 'request and response'],
    ['null response', { ...valid, response: null }, 'request and response'],
  ])('rejects %s', (_label, body, message) => {
    const result = validateGenerationPayload(body);
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error).toContain(message);
  });

  it('rejects payloads over the size cap', () => {
    const big = { ...valid, response: { blob: 'x'.repeat(MAX_GENERATION_BYTES) } };
    const result = validateGenerationPayload(big);
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error).toContain('too large');
  });

  it('accepts payloads just under the size cap', () => {
    const almost = { ...valid, response: { blob: 'x'.repeat(MAX_GENERATION_BYTES - 200) } };
    expect(validateGenerationPayload(almost).ok).toBe(true);
  });
});
