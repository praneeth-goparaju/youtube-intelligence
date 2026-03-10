/**
 * AI thumbnail generation using Gemini image generation (Nano Banana Pro).
 *
 * Generates 2 mock thumbnail variations from the recommendation specs.
 */

import { GoogleGenAI } from '@google/genai';
import * as fs from 'fs';
import * as path from 'path';
import type { ThumbnailRecommendation } from './types';

const IMAGE_MODELS = ['gemini-3.1-flash-image-preview', 'gemini-2.5-flash-image'];

/** Convert hex color to a human-readable color name for image generation prompts. */
function describeColor(hex: string): string {
  const colors: Record<string, string> = {
    '#FF0000': 'bright red', '#FF6B35': 'vibrant orange', '#FFFF00': 'bright yellow',
    '#00FF00': 'green', '#3498DB': 'sky blue', '#2C3E50': 'dark navy',
    '#9B59B6': 'purple', '#E74C3C': 'red', '#FFFFFF': 'white', '#000000': 'black',
  };
  return colors[hex.toUpperCase()] || hex;
}

/** Convert position shorthand to natural spatial language. */
function describePosition(pos: string): string {
  const positions: Record<string, string> = {
    'right-third': 'on the right side', 'left-third': 'on the left side',
    'left-center': 'in the left-center area', 'center': 'in the center',
    'top-left': 'in the top-left corner', 'top-center': 'across the top',
    'top-right': 'in the top-right', 'bottom': 'along the bottom',
    'full-frame': 'filling the entire frame', 'around-face': 'surrounding the person',
    'corner': 'in one corner',
  };
  return positions[pos] || pos;
}

function buildImagePrompt(thumb: ThumbnailRecommendation, variation: number): string {
  const face = thumb.elements.face;
  const text = thumb.elements.text;
  const visual = thumb.elements.mainVisual;
  const colors = thumb.colors;

  const parts: string[] = [
    `Create a professional YouTube video thumbnail in 16:9 landscape format.`,
    `This thumbnail must look eye-catching even at small sizes — bold colors, high contrast, clean composition.`,
    `Style: Photorealistic digital art with graphic design elements, similar to top Indian YouTube thumbnails.`,
    ``,
    `Scene: ${thumb.layout.description}.`,
    `The dominant color palette is ${describeColor(colors.background)} background with ${describeColor(colors.accent)} accents.`,
  ];

  if (face.required) {
    const gazeDesc = face.eyeContact ? 'looking directly at the viewer' : 'looking to the side';
    parts.push(`A person with a ${face.expression} facial expression is positioned ${describePosition(face.position)}, taking up a ${face.size} portion of the frame, ${gazeDesc}. The face should be well-lit and expressive.`);
  }

  if (visual.type) {
    const visualParts = [`The main visual subject is a ${visual.type} placed ${describePosition(visual.position)}`];
    if (visual.showSteam) visualParts.push('with visible steam or smoke rising from it for a fresh, hot-food effect');
    if (visual.garnished) visualParts.push('beautifully garnished and plated to look appetizing');
    parts.push(visualParts.join(', ') + '.');
  }

  parts.push(`Large, bold text reading "${text.primary.content}" in ${describeColor(text.primary.color)} with a ${text.primary.style || 'bold'} style is placed ${describePosition(text.primary.position)}. The text must be crisp, legible, and have a dark outline or shadow for contrast.`);
  if (text.secondary) {
    parts.push(`Smaller secondary text "${text.secondary.content}" appears ${describePosition(text.secondary.position)} in ${describeColor(text.secondary.color || '#FFFFFF')}.`);
  }

  const graphics = thumb.elements.graphics;
  if (graphics.addArrow && graphics.arrowPointTo) {
    parts.push(`A bold graphic arrow points toward the ${graphics.arrowPointTo} to draw the viewer's eye.`);
  }
  if (graphics.addBorder && graphics.borderColor) {
    parts.push(`The thumbnail has a thin ${describeColor(graphics.borderColor)} border framing it.`);
  }

  if (variation === 2) {
    parts.push(`\nIMPORTANT VARIATION: Use a noticeably different camera angle, change the person's expression to something more intense, and shift the text to the opposite side. Keep the same overall concept but make it feel like a distinct option.`);
  }

  return parts.join('\n');
}

function ensureOutputDir(): string {
  const outputDir = path.join(process.cwd(), 'outputs');
  fs.mkdirSync(outputDir, { recursive: true });
  return outputDir;
}

async function callImageModel(
  client: GoogleGenAI,
  model: string,
  prompt: string,
): Promise<string | null> {
  const response = await client.models.generateContent({
    model,
    contents: [{ role: 'user', parts: [{ text: prompt }] }],
    config: {
      responseModalities: ['TEXT', 'IMAGE'],
    },
  });

  const candidate = response.candidates?.[0];
  const parts = candidate?.content?.parts;
  if (!parts || parts.length === 0) {
    console.warn(`    No response parts (finishReason: ${candidate?.finishReason})`);
    return null;
  }

  for (const part of parts) {
    if (part.inlineData?.mimeType?.startsWith('image/')) {
      return part.inlineData.data!;
    }
  }

  const partTypes = parts.map(p => p.text ? 'text' : p.inlineData?.mimeType || 'unknown');
  console.warn(`    No image in response. Parts: ${partTypes.join(', ')}`);
  return null;
}

async function generateSingleThumbnail(
  client: GoogleGenAI,
  thumb: ThumbnailRecommendation,
  variation: number,
  outputDir: string,
): Promise<string | null> {
  const prompt = buildImagePrompt(thumb, variation);
  console.log(`  Generating thumbnail ${variation}/2...`);

  for (const model of IMAGE_MODELS) {
    try {
      console.log(`    Trying ${model}...`);
      const base64 = await callImageModel(client, model, prompt);
      if (base64) {
        const outputPath = path.join(outputDir, `thumbnail_${variation}.png`);
        fs.writeFileSync(outputPath, Buffer.from(base64, 'base64'));
        console.log(`    Success (${model})`);
        return outputPath;
      }
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      console.warn(`    ${model} failed: ${msg.slice(0, 150)}`);
    }
  }

  console.warn(`  Warning: All models failed for thumbnail ${variation}`);
  return null;
}

export async function generateThumbnails(thumb: ThumbnailRecommendation): Promise<string[]> {
  const apiKey = process.env.GOOGLE_API_KEY;
  if (!apiKey) {
    throw new Error('GOOGLE_API_KEY not found — required for thumbnail generation');
  }

  const client = new GoogleGenAI({ apiKey });
  const outputDir = ensureOutputDir();

  // Generate both thumbnails in parallel
  const results = await Promise.all([
    generateSingleThumbnail(client, thumb, 1, outputDir),
    generateSingleThumbnail(client, thumb, 2, outputDir),
  ]);

  return results.filter((p): p is string => p !== null);
}
