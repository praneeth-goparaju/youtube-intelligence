import { EventEmitter } from 'events';
import { recommend, ideas, getRecommendation, getIdeas, generationsSave, generationsList } from '../src/index';
import { getAllInsights, saveGeneration, listGenerations } from '../src/firebase';

jest.mock('../src/firebase', () => ({
  getAllInsights: jest.fn(async () => ({})),
  saveGeneration: jest.fn(async () => ({ id: 'saved', savedAt: '2026-01-01' })),
  listGenerations: jest.fn(async () => []),
}));
jest.mock('../src/rate-limiter', () => ({
  checkRateLimit: jest.fn(async () => ({ allowed: true, remaining: 99 })),
}));

async function request(handler: typeof recommend, body: unknown, method = 'POST', query: unknown = {}) {
  const events = new EventEmitter();
  const response = Object.assign(events, {
    statusCode: 200,
    body: undefined as unknown,
    setHeader: jest.fn(),
    status(code: number) { this.statusCode = code; return this; },
    json(value: unknown) { this.body = value; events.emit('finish'); return this; },
  });
  await handler({ method, headers: { authorization: 'Bearer test-key' }, body, query } as never, response as never);
  return response;
}

beforeEach(() => {
  process.env.RECOMMEND_API_KEY = 'test-key';
  jest.clearAllMocks();
  jest.spyOn(console, 'error').mockImplementation(() => {});
  jest.spyOn(console, 'log').mockImplementation(() => {});
});
afterEach(() => jest.restoreAllMocks());

test.each([null, [], { topic: 123 }, { topic: 'Biryani', angle: {} }, { topic: 'Biryani', audience: [] }, { topic: 'Biryani', type: false }])('HTTP rejects malformed recommendation %j', async (body) => {
  expect((await request(recommend, body)).statusCode).toBe(400);
  expect(getAllInsights).not.toHaveBeenCalled();
});

test.each([null, [], { type: 0 }, { type: 'invalid' }])('HTTP rejects malformed ideas %j', async (body) => {
  expect((await request(ideas, body)).statusCode).toBe(400);
  expect(getAllInsights).not.toHaveBeenCalled();
});

test.each([null, { topic: 123 }, { topic: 'Biryani', angle: {} }])('callable rejects malformed recommendation %j', async (data) => {
  await expect(getRecommendation.run({ data, auth: { uid: 'test-user' } } as never)).rejects.toMatchObject({ code: 'invalid-argument' });
});

test.each([null, [], { type: false }])('callable rejects malformed ideas %j', async (data) => {
  await expect(getIdeas.run({ data, auth: { uid: 'test-user' } } as never)).rejects.toMatchObject({ code: 'invalid-argument' });
});

test.each([null, { type: 'ideas', request: [], response: {} }, { type: 'ideas', request: {}, response: 'invalid' }])('save rejects malformed generation %j', async (body) => {
  expect((await request(generationsSave, body)).statusCode).toBe(400);
  expect(saveGeneration).not.toHaveBeenCalled();
});

test.each([{ type: 'invalid' }, { type: ['ideas', 'recommendation'] }])('list rejects malformed filter %j', async (query) => {
  expect((await request(generationsList, undefined, 'GET', query)).statusCode).toBe(400);
  expect(listGenerations).not.toHaveBeenCalled();
});

test('valid recommendation still reaches the engine', async () => {
  expect((await request(recommend, { topic: 'Biryani' })).statusCode).toBe(200);
  expect(getAllInsights).toHaveBeenCalled();
});

test('each endpoint binds only the secrets it needs', () => {
  for (const endpoint of [recommend, ideas]) {
    expect(endpoint.__endpoint.secretEnvironmentVariables).toEqual([{ key: 'RECOMMEND_API_KEY' }, { key: 'GOOGLE_API_KEY' }]);
  }
  for (const endpoint of [getRecommendation, getIdeas]) {
    expect(endpoint.__endpoint.secretEnvironmentVariables).toEqual([{ key: 'GOOGLE_API_KEY' }]);
  }
  for (const endpoint of [generationsSave, generationsList]) {
    expect(endpoint.__endpoint.secretEnvironmentVariables).toEqual([{ key: 'RECOMMEND_API_KEY' }]);
  }
});
