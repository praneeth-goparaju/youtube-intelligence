/**
 * Gemini AI client for generating recommendations
 */

import { ApiError, GoogleGenAI } from '@google/genai';
import { defineSecret } from 'firebase-functions/params';
import { generateGeminiJson, GEMINI_MODEL } from './gemini-client';

// Define the API key as a Firebase parameter (set via Firebase Console or CLI)
export const geminiApiKey = defineSecret('GOOGLE_API_KEY');

let client: GoogleGenAI | undefined;

/**
 * Initialize Gemini client (lazy initialization)
 */
function getClient(): GoogleGenAI {
  if (!client) {
    const apiKey = geminiApiKey.value();
    if (!apiKey) {
      throw new Error('GOOGLE_API_KEY not configured. Set it using: firebase functions:secrets:set GOOGLE_API_KEY');
    }
    client = new GoogleGenAI({ apiKey });
  }
  return client;
}

// Retry configuration
const MAX_RETRIES = 3;
const BASE_DELAY_MS = 1000;

/**
 * Delay helper
 */
function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Generate recommendation using Gemini with retry logic
 */
export async function generateWithGemini(prompt: string): Promise<string> {
  const client = getClient();
  let lastError: Error | undefined;

  for (let attempt = 0; attempt < MAX_RETRIES; attempt++) {
    try {
      return await generateGeminiJson(client, prompt);
    } catch (error) {
      lastError = error instanceof Error ? error : new Error(String(error));
      const errorMessage = lastError.message;

      // Check if it's a rate limit error (429) - wait longer
      const isRateLimit = (error instanceof ApiError && error.status === 429) ||
        errorMessage.includes('429') || errorMessage.toLowerCase().includes('rate limit');

      if (attempt < MAX_RETRIES - 1) {
        const waitTime = isRateLimit
          ? BASE_DELAY_MS * Math.pow(2, attempt) * 2  // Longer wait for rate limits
          : BASE_DELAY_MS * Math.pow(2, attempt);

        console.warn(`Gemini attempt ${attempt + 1} failed: ${errorMessage}. Retrying in ${waitTime}ms...`);
        await delay(waitTime);
      } else {
        console.error(`Gemini generation failed after ${MAX_RETRIES} attempts:`, error);
      }
    }
  }

  throw lastError || new Error('Gemini generation failed');
}

/**
 * Test Gemini connection
 */
export async function testGeminiConnection(): Promise<boolean> {
  try {
    const response = await getClient().models.generateContent({
      model: GEMINI_MODEL,
      contents: 'Say "OK" if you can read this.',
    });
    return response.text?.toLowerCase().includes('ok') ?? false;
  } catch {
    return false;
  }
}
