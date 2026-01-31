import { config as dotenvConfig } from 'dotenv';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));

// Load .env from project root
dotenvConfig({ path: resolve(__dirname, '../../.env') });

function getEnvVar(name: string, required = true): string {
  const value = process.env[name];
  if (required && !value) {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return value || '';
}

function getEnvNumber(name: string, defaultValue: number): number {
  const value = process.env[name];
  if (!value) return defaultValue;
  const parsed = parseInt(value, 10);
  return isNaN(parsed) ? defaultValue : parsed;
}

export const config = {
  // YouTube API
  youtube: {
    apiKey: getEnvVar('YOUTUBE_API_KEY'),
  },

  // Firebase
  firebase: {
    projectId: getEnvVar('FIREBASE_PROJECT_ID'),
    clientEmail: getEnvVar('FIREBASE_CLIENT_EMAIL'),
    privateKey: getEnvVar('FIREBASE_PRIVATE_KEY').replace(/\\n/g, '\n'),
    storageBucket: getEnvVar('FIREBASE_STORAGE_BUCKET'),
  },

  // Scraper settings
  scraper: {
    apiDelayMs: getEnvNumber('API_DELAY_MS', 100),
    quotaWarningThreshold: getEnvNumber('QUOTA_WARNING_THRESHOLD', 500),
    thumbnailQuality: process.env.THUMBNAIL_QUALITY || 'mqdefault',
    batchSize: 50, // YouTube API limit for video details
    maxRetries: 3,
    retryDelayMs: 1000,
    apiTimeoutMs: getEnvNumber('API_TIMEOUT_MS', 30000), // 30 second timeout for API requests
  },

  // Quota tracking
  quota: {
    dailyLimit: 10000,
  },

  // Paths
  paths: {
    channelsConfig: resolve(__dirname, '../../config/channels.json'),
  },
};

export function validateConfig(): void {
  const requiredVars = [
    'YOUTUBE_API_KEY',
    'FIREBASE_PROJECT_ID',
    'FIREBASE_CLIENT_EMAIL',
    'FIREBASE_PRIVATE_KEY',
    'FIREBASE_STORAGE_BUCKET',
  ];

  const missing: string[] = [];
  for (const varName of requiredVars) {
    if (!process.env[varName]) {
      missing.push(varName);
    }
  }

  if (missing.length > 0) {
    throw new Error(
      `Missing required environment variables:\n${missing.map((v) => `  - ${v}`).join('\n')}`
    );
  }
}
