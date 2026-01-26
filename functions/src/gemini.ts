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
      throw new Error('GOOGLE_API_KEY not configured. Set it using: firebase functions:config:set google.api_key="YOUR_KEY"');
    }
    genAI = new GoogleGenerativeAI(apiKey);
    model = genAI.getGenerativeModel({
      model: 'gemini-2.0-flash',
      generationConfig: {
        temperature: 0.7,  // Higher for creative suggestions
        topP: 0.95,
        maxOutputTokens: 4096,
      },
    });
  }
  return model;
}

/**
 * Generate recommendation using Gemini
 */
export async function generateWithGemini(prompt: string): Promise<string> {
  const model = getModel();

  try {
    const result = await model.generateContent(prompt);
    const response = result.response;
    const text = response.text();

    // Clean up the response (remove markdown code blocks if present)
    return cleanJsonResponse(text);
  } catch (error) {
    console.error('Gemini generation failed:', error);
    throw error;
  }
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
