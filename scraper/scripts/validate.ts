import { config as dotenvConfig } from 'dotenv';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';
import { google } from 'googleapis';
import { initializeApp, cert, getApps } from 'firebase-admin/app';
import { getFirestore } from 'firebase-admin/firestore';
import { getStorage } from 'firebase-admin/storage';

const __dirname = dirname(fileURLToPath(import.meta.url));
dotenvConfig({ path: resolve(__dirname, '../../.env') });

const COLORS = {
  reset: '\x1b[0m',
  green: '\x1b[32m',
  red: '\x1b[31m',
  yellow: '\x1b[33m',
  cyan: '\x1b[36m',
};

function log(message: string, color = COLORS.reset): void {
  console.log(`${color}${message}${COLORS.reset}`);
}

function success(message: string): void {
  log(`[OK] ${message}`, COLORS.green);
}

function error(message: string): void {
  log(`[FAIL] ${message}`, COLORS.red);
}

function warn(message: string): void {
  log(`[WARN] ${message}`, COLORS.yellow);
}

function info(message: string): void {
  log(`[INFO] ${message}`, COLORS.cyan);
}

async function validateYouTubeAPI(): Promise<boolean> {
  info('Testing YouTube Data API v3...');

  const apiKey = process.env.YOUTUBE_API_KEY;
  if (!apiKey) {
    error('YOUTUBE_API_KEY not set');
    return false;
  }

  try {
    const youtube = google.youtube({ version: 'v3', auth: apiKey });
    const response = await youtube.channels.list({
      part: ['snippet'],
      forHandle: 'Google',
    });

    if (response.data.items && response.data.items.length > 0) {
      success(`YouTube API working - Found channel: ${response.data.items[0].snippet?.title}`);
      return true;
    } else {
      error('YouTube API returned no results');
      return false;
    }
  } catch (err) {
    error(`YouTube API error: ${(err as Error).message}`);
    return false;
  }
}

async function validateFirebase(): Promise<boolean> {
  info('Testing Firebase connection...');

  const projectId = process.env.FIREBASE_PROJECT_ID;
  const clientEmail = process.env.FIREBASE_CLIENT_EMAIL;
  const privateKey = process.env.FIREBASE_PRIVATE_KEY?.replace(/\\n/g, '\n');
  const storageBucket = process.env.FIREBASE_STORAGE_BUCKET;

  if (!projectId || !clientEmail || !privateKey || !storageBucket) {
    error('Missing Firebase configuration');
    if (!projectId) warn('  - FIREBASE_PROJECT_ID not set');
    if (!clientEmail) warn('  - FIREBASE_CLIENT_EMAIL not set');
    if (!privateKey) warn('  - FIREBASE_PRIVATE_KEY not set');
    if (!storageBucket) warn('  - FIREBASE_STORAGE_BUCKET not set');
    return false;
  }

  try {
    // Initialize Firebase if not already done
    if (getApps().length === 0) {
      initializeApp({
        credential: cert({
          projectId,
          clientEmail,
          privateKey,
        }),
        storageBucket,
      });
    }

    // Test Firestore
    const db = getFirestore();
    await db.collection('_validation').doc('test').set({ timestamp: new Date() });
    await db.collection('_validation').doc('test').delete();
    success('Firestore connection working');

    // Test Storage
    const storage = getStorage();
    const bucket = storage.bucket();
    const [exists] = await bucket.exists();
    if (exists) {
      success(`Storage bucket accessible: ${storageBucket}`);
    } else {
      warn(`Storage bucket may not exist: ${storageBucket}`);
    }

    return true;
  } catch (err) {
    error(`Firebase error: ${(err as Error).message}`);
    return false;
  }
}

function validateEnvironment(): boolean {
  info('Checking environment variables...');

  const required = [
    'YOUTUBE_API_KEY',
    'FIREBASE_PROJECT_ID',
    'FIREBASE_CLIENT_EMAIL',
    'FIREBASE_PRIVATE_KEY',
    'FIREBASE_STORAGE_BUCKET',
  ];

  let allPresent = true;
  for (const varName of required) {
    if (process.env[varName]) {
      success(`${varName} is set`);
    } else {
      error(`${varName} is NOT set`);
      allPresent = false;
    }
  }

  return allPresent;
}

async function main(): Promise<void> {
  console.log('\n' + '='.repeat(60));
  console.log('  YouTube Intelligence System - Connection Validator');
  console.log('='.repeat(60) + '\n');

  const envValid = validateEnvironment();
  console.log('');

  if (!envValid) {
    error('Environment validation failed. Please check your .env file.');
    process.exit(1);
  }

  const youtubeValid = await validateYouTubeAPI();
  console.log('');

  const firebaseValid = await validateFirebase();
  console.log('');

  console.log('='.repeat(60));

  if (youtubeValid && firebaseValid) {
    success('All validations passed! Ready to run scraper.');
    console.log('\nRun: npm start');
  } else {
    error('Some validations failed. Please fix the issues above.');
    process.exit(1);
  }

  console.log('='.repeat(60) + '\n');
  process.exit(0);
}

main().catch((err) => {
  error(`Unexpected error: ${(err as Error).message}`);
  process.exit(1);
});
