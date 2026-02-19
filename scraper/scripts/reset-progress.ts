import { config as dotenvConfig } from 'dotenv';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';
import { initializeApp, cert, getApps } from 'firebase-admin/app';
import { getFirestore } from 'firebase-admin/firestore';
import * as readline from 'readline';

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

function initFirebase() {
  if (getApps().length === 0) {
    initializeApp({
      credential: cert({
        projectId: process.env.FIREBASE_PROJECT_ID!,
        clientEmail: process.env.FIREBASE_CLIENT_EMAIL!,
        privateKey: process.env.FIREBASE_PRIVATE_KEY!.replace(/\\n/g, '\n'),
      }),
      storageBucket: process.env.FIREBASE_STORAGE_BUCKET,
    });
  }
  return getFirestore();
}

async function getProgressCount(): Promise<number> {
  const db = initFirebase();
  const snapshot = await db.collection('scrape_progress').count().get();
  return snapshot.data().count;
}

async function deleteAllProgress(): Promise<number> {
  const db = initFirebase();
  const snapshot = await db.collection('scrape_progress').get();

  if (snapshot.empty) {
    return 0;
  }

  // Firestore batches limited to 500 operations
  const BATCH_LIMIT = 500;
  const docs = snapshot.docs;
  for (let i = 0; i < docs.length; i += BATCH_LIMIT) {
    const chunk = docs.slice(i, i + BATCH_LIMIT);
    const batch = db.batch();
    chunk.forEach((doc) => batch.delete(doc.ref));
    await batch.commit();
  }

  return snapshot.size;
}

async function askConfirmation(message: string): Promise<boolean> {
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });

  return new Promise((resolve) => {
    rl.question(`${message} (y/N): `, (answer) => {
      rl.close();
      resolve(answer.toLowerCase() === 'y');
    });
  });
}

async function main(): Promise<void> {
  console.log('\n' + '='.repeat(60));
  console.log('  YouTube Intelligence System - Reset Progress');
  console.log('='.repeat(60) + '\n');

  try {
    const count = await getProgressCount();

    if (count === 0) {
      log('No progress records found.', COLORS.yellow);
      process.exit(0);
    }

    log(`Found ${count} progress record(s).`, COLORS.cyan);
    log('', COLORS.reset);
    log('WARNING: This will delete all scrape progress records.', COLORS.yellow);
    log('The scraper will start fresh on the next run.', COLORS.yellow);
    log('', COLORS.reset);

    const confirmed = await askConfirmation('Are you sure you want to reset all progress?');

    if (!confirmed) {
      log('\nOperation cancelled.', COLORS.yellow);
      process.exit(0);
    }

    log('\nDeleting progress records...', COLORS.cyan);
    const deleted = await deleteAllProgress();
    log(`\nDeleted ${deleted} progress record(s).`, COLORS.green);
    log('Progress has been reset. Run "npm start" to start fresh.', COLORS.green);
  } catch (error) {
    log(`\nError: ${(error as Error).message}`, COLORS.red);
    process.exit(1);
  }

  console.log('\n' + '='.repeat(60) + '\n');
  process.exit(0);
}

main();
