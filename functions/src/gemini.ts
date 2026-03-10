/**
 * Gemini AI client for generating recommendations
 */

import { GoogleGenerativeAI, GenerativeModel } from '@google/generative-ai';
import { defineString } from 'firebase-functions/params';

// Define the API key as a Firebase parameter (set via Firebase Console or CLI)
const geminiApiKey = defineString('GOOGLE_API_KEY');

let genAI: GoogleGenerativeAI | null = null;
let model: GenerativeModel | null = null;

/**
 * Initialize Gemini client (lazy initialization)
 */
function getModel(): GenerativeModel {
  if (!model) {
    const apiKey = geminiApiKey.value();
    if (!apiKey) {
      throw new Error('GOOGLE_API_KEY not configured. Set it using: firebase functions:secrets:set GOOGLE_API_KEY');
    }
    genAI = new GoogleGenerativeAI(apiKey);
    model = genAI.getGenerativeModel({
      model: 'gemini-2.5-flash',
      generationConfig: {
        temperature: 0.7,  // Higher for creative suggestions
        topP: 0.95,
        maxOutputTokens: 16384,
      },
    });
  }
  return model;
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
  const model = getModel();
  let lastError: Error | undefined;

  for (let attempt = 0; attempt < MAX_RETRIES; attempt++) {
    try {
      const result = await model.generateContent(prompt);
      const response = result.response;

      // Validate response
      if (!response) {
        throw new Error('No response received from Gemini');
      }

      const text = response.text();
      if (!text) {
        throw new Error('Empty response text from Gemini');
      }

      // Clean up the response (remove markdown code blocks if present)
      return cleanJsonResponse(text);
    } catch (error) {
      lastError = error as Error;
      const errorMessage = lastError.message || String(error);

      // Check if it's a rate limit error (429) - wait longer
      const isRateLimit = errorMessage.includes('429') || errorMessage.toLowerCase().includes('rate limit');

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
 * Clean JSON response from Gemini (remove markdown formatting)
 */
function cleanJsonResponse(text: string): string {
  // Remove markdown code blocks
  let cleaned = text.trim();

  // Remove ```json and ``` markers
  if (cleaned.startsWith('```json')) {
    cleaned = cleaned.slice(7);
  } else if (cleaned.startsWith('```')) {
    cleaned = cleaned.slice(3);
  }

  if (cleaned.endsWith('```')) {
    cleaned = cleaned.slice(0, -3);
  }

  return cleaned.trim();
}

/**
 * Test Gemini connection
 */
export async function testGeminiConnection(): Promise<boolean> {
  try {
    const model = getModel();
    const result = await model.generateContent('Say "OK" if you can read this.');
    return result.response.text().toLowerCase().includes('ok');
  } catch {
    return false;
  }
}
