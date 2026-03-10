import { GoogleGenAI } from '@google/genai';
import * as fs from 'fs';
import * as path from 'path';

// Load env
const envPaths = [
  path.join(__dirname, '../../.env'),
  path.join(__dirname, '../../../.env'),
];
for (const envPath of envPaths) {
  if (fs.existsSync(envPath)) {
    const content = fs.readFileSync(envPath, 'utf-8');
    for (const line of content.split('\n')) {
      const trimmed = line.trim();
      if (trimmed && trimmed.indexOf('#') !== 0) {
        const eqIdx = trimmed.indexOf('=');
        if (eqIdx > 0) {
          const key = trimmed.slice(0, eqIdx);
          const value = trimmed.slice(eqIdx + 1).replace(/^["']|["']$/g, '');
          if (key && value && process.env[key] === undefined) {
            process.env[key] = value;
          }
        }
      }
    }
    break;
  }
}

async function listImageModels() {
  const client = new GoogleGenAI({ apiKey: process.env.GOOGLE_API_KEY || '' });
  console.log('Listing models with image support or "2.5" in name...\n');

  const result = await client.models.list();
  for await (const model of result) {
    const name = model.name || '';
    if (name.includes('image') || name.includes('imagen') || name.includes('2.5')) {
      console.log(`  ${name}`);
    }
  }
}

async function testModel(modelName: string) {
  const client = new GoogleGenAI({ apiKey: process.env.GOOGLE_API_KEY || '' });
  console.log(`\nTesting ${modelName}...`);
  try {
    const response = await client.models.generateContent({
      model: modelName,
      contents: [{ role: 'user', parts: [{ text: 'Generate a simple red circle on white background' }] }],
      config: { responseModalities: ['TEXT', 'IMAGE'] },
    });
    const candidate = response.candidates?.[0];
    console.log('  finishReason:', candidate?.finishReason);
    const parts = candidate?.content?.parts;
    if (parts) {
      for (const p of parts) {
        if (p.text) console.log('  Text:', p.text.slice(0, 100));
        if (p.inlineData) console.log(`  Image: ${p.inlineData.mimeType}, ${p.inlineData.data?.length} base64 chars`);
      }
    }
    return true;
  } catch (e: any) {
    console.log(`  FAILED: ${e.message?.slice(0, 200)}`);
    return false;
  }
}

async function main() {
  await listImageModels();
  await testModel('gemini-2.5-flash');
}

main();
