import { ApiError, GoogleGenAI } from '@google/genai';
import { generateGeminiJson, GEMINI_MODEL } from '../src/gemini-client';
import { generateWithGemini, testGeminiConnection } from '../src/gemini';

function jsonResponse(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), { status, headers: { 'content-type': 'application/json' } });
}

function generatedText(text: string): Response {
  return jsonResponse({ candidates: [{ content: { role: 'model', parts: [{ text }] }, finishReason: 'STOP' }] });
}

let fetchMock: jest.SpyInstance<ReturnType<typeof fetch>, Parameters<typeof fetch>>;

beforeEach(() => {
  process.env.GOOGLE_API_KEY = 'test-key';
  fetchMock = jest.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('Unexpected network request'));
  jest.spyOn(console, 'warn').mockImplementation(() => {});
  jest.spyOn(console, 'error').mockImplementation(() => {});
});

afterEach(() => {
  jest.useRealTimers();
  jest.restoreAllMocks();
});

test('the maintained SDK sends the existing model settings and reads response.text', async () => {
  fetchMock.mockResolvedValueOnce(generatedText('```json\n{"ideas":[]}\n```'));
  const result = await generateGeminiJson(new GoogleGenAI({ apiKey: 'test-key' }), 'Generate ideas');
  expect(result).toBe('{"ideas":[]}');
  expect(fetchMock).toHaveBeenCalledTimes(1);
  const [url, options] = fetchMock.mock.calls[0];
  expect(String(url)).toContain(`/models/${GEMINI_MODEL}:generateContent`);
  expect(JSON.parse(String(options?.body))).toMatchObject({
    contents: [{ role: 'user', parts: [{ text: 'Generate ideas' }] }],
    generationConfig: { temperature: 0.7, topP: 0.95, maxOutputTokens: 16384, responseMimeType: 'application/json' },
  });
});

test.each([{}, { candidates: [] }, { candidates: [{ content: { parts: [{ text: '  ' }] } }] }])('empty SDK response is rejected: %j', async (data) => {
  fetchMock.mockResolvedValueOnce(jsonResponse(data));
  await expect(generateGeminiJson(new GoogleGenAI({ apiKey: 'test-key' }), 'Generate ideas'))
    .rejects.toThrow('Empty response text from Gemini');
});

test('the adapter preserves API error status for retry handling', async () => {
  fetchMock.mockResolvedValueOnce(jsonResponse({ error: { code: 429, message: 'Quota exhausted' } }, 429));
  const result = generateGeminiJson(new GoogleGenAI({ apiKey: 'test-key' }), 'Generate ideas');
  await expect(result).rejects.toBeInstanceOf(ApiError);
  await expect(result).rejects.toMatchObject({ status: 429 });
});

test('the Functions adapter retries a rate limit and returns the next SDK response', async () => {
  jest.useFakeTimers();
  fetchMock.mockResolvedValueOnce(jsonResponse({ error: { code: 429, message: 'Quota exhausted' } }, 429));
  fetchMock.mockResolvedValueOnce(generatedText('{"ideas":[]}'));
  const result = expect(generateWithGemini('Generate ideas')).resolves.toBe('{"ideas":[]}');
  await jest.runAllTimersAsync();
  await result;
  expect(fetchMock).toHaveBeenCalledTimes(2);
});

test('the Functions adapter stops after three failed attempts', async () => {
  jest.useFakeTimers();
  fetchMock.mockImplementation(async () => jsonResponse({ error: { code: 500, message: 'Unavailable' } }, 500));
  const result = expect(generateWithGemini('Generate ideas')).rejects.toMatchObject({ status: 500 });
  await jest.runAllTimersAsync();
  await result;
  expect(fetchMock).toHaveBeenCalledTimes(3);
});

test('the connection check uses the new text property', async () => {
  fetchMock.mockResolvedValueOnce(generatedText('OK'));
  await expect(testGeminiConnection()).resolves.toBe(true);
  fetchMock.mockResolvedValueOnce(jsonResponse({ candidates: [] }));
  await expect(testGeminiConnection()).resolves.toBe(false);
});
