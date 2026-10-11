import type { GoogleGenAI } from '@google/genai';
import { cleanJsonResponse } from './response-validation';

export const GEMINI_MODEL = 'gemini-2.5-flash';

export async function generateGeminiJson(client: GoogleGenAI, prompt: string): Promise<string> {
  const response = await client.models.generateContent({
    model: GEMINI_MODEL,
    contents: prompt,
    config: {
      temperature: 0.7,
      topP: 0.95,
      maxOutputTokens: 16384,
      responseMimeType: 'application/json',
    },
  });
  const text = response.text;
  if (!text?.trim()) throw new Error('Empty response text from Gemini');
  return cleanJsonResponse(text);
}
