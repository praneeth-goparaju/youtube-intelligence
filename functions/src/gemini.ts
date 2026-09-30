/**
 * Gemini AI client for generating recommendations
 */

import { GoogleGenerativeAI, GenerativeModel } from '@google/generative-ai';
import { defineSecret } from 'firebase-functions/params';
import { readSecret } from './secrets';
import { runWithRetries } from './retry';

/**
 * Gemini API key, stored in Secret Manager:
 *   firebase functions:secrets:set GOOGLE_API_KEY
 * Every function that calls Gemini must list this in its `secrets` option.
 */
export const geminiApiKey = defineSecret('GOOGLE_API_KEY');

let model: GenerativeModel | null = null;

/**
 * Whether a Gemini API key is available to this function instance.
 * Never exposes the key itself.
 */
export function isGeminiConfigured(): boolean {
  return readSecret(geminiApiKey).length > 0;
}

/**
 * Initialize Gemini client (lazy initialization)
 */
function getModel(): GenerativeModel {
  if (!model) {
    const apiKey = readSecret(geminiApiKey);
    if (!apiKey) {
      // Log loudly on every attempt: without the key every request silently degrades to templates.
      console.error(
        'CONFIGURATION ERROR: GOOGLE_API_KEY secret is not available to this function. ' +
        'All recommendations will use template fallback. Set it with ' +
        '`firebase functions:secrets:set GOOGLE_API_KEY` and ensure the function declares it in `secrets`.'
      );
      throw new Error('GOOGLE_API_KEY not configured');
    }
    const genAI = new GoogleGenerativeAI(apiKey);
    model = genAI.getGenerativeModel({
      model: 'gemini-2.5-flash',
      generationConfig: {
        temperature: 0.7,  // Higher for creative suggestions
        topP: 0.95,
        maxOutputTokens: 16384,
        responseMimeType: 'application/json',
      },
    });
  }
  return model;
}

// Retry / deadline configuration.
// Functions run with timeoutSeconds=120 (index.ts). The whole Gemini phase must
// finish well before that so the template fallback can still run and respond.
export const GEMINI_TOTAL_BUDGET_MS = 90_000;
export const GEMINI_ATTEMPT_TIMEOUT_MS = 60_000;
const MAX_RETRIES = 3;
const BASE_DELAY_MS = 1000;

/**
 * Generate recommendation using Gemini with retry logic, a per-attempt timeout
 * and an overall deadline. Throws once the budget is exhausted so callers fall
 * back to templates before the Cloud Function times out.
 */
export async function generateWithGemini(
  prompt: string,
  options: { totalBudgetMs?: number; attemptTimeoutMs?: number } = {}
): Promise<string> {
  const model = getModel();

  const text = await runWithRetries(
    async (signal, timeoutMs) => {
      const result = await model.generateContent(prompt, { signal, timeout: timeoutMs });
      const response = result.response;
      if (!response) {
        throw new Error('No response received from Gemini');
      }
      const text = response.text();
      if (!text) {
        throw new Error('Empty response text from Gemini');
      }
      return text;
    },
    {
      maxAttempts: MAX_RETRIES,
      baseDelayMs: BASE_DELAY_MS,
      totalBudgetMs: options.totalBudgetMs ?? GEMINI_TOTAL_BUDGET_MS,
      attemptTimeoutMs: options.attemptTimeoutMs ?? GEMINI_ATTEMPT_TIMEOUT_MS,
      label: 'Gemini',
    }
  );

  // Clean up the response (remove markdown code blocks if present)
  return cleanJsonResponse(text);
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
