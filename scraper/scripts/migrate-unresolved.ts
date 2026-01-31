import { config as dotenvConfig } from 'dotenv';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';
import { initializeApp, cert, getApps } from 'firebase-admin/app';
import { getFirestore, Timestamp } from 'firebase-admin/firestore';
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

/** Real channel IDs match UC + 22 characters */
const CHANNEL_ID_PATTERN = /^UC.{22}$/;

async function main(): Promise<void> {
  console.log('\n' + '='.repeat(60));
  console.log('  YouTube Intelligence System - Migrate Unresolved Channels');
  console.log('='.repeat(60) + '\n');

  try {
    const db = initFirebase();

    log('Scanning scrape_progress for unresolved entries...', COLORS.cyan);
    const snapshot = await db.collection('scrape_progress').get();

    if (snapshot.empty) {
      log('No progress records found.', COLORS.yellow);
      process.exit(0);
    }

    // Identify entries whose doc ID doesn't look like a real channel ID
    const unresolved: Array<{ id: string; data: any }> = [];
    for (const doc of snapshot.docs) {
      if (!CHANNEL_ID_PATTERN.test(doc.id)) {
        unresolved.push({ id: doc.id, data: doc.data() });
      }
    }

    if (unresolved.length === 0) {
      log('No unresolved entries found in scrape_progress.', COLORS.yellow);
      log(`All ${snapshot.size} entries have valid channel IDs.`, COLORS.cyan);
      process.exit(0);
    }

    log(`Found ${unresolved.length} unresolved entry/entries (out of ${snapshot.size} total):`, COLORS.cyan);
    log('', COLORS.reset);
    for (const entry of unresolved) {
      const sourceUrl = entry.data.sourceUrl || entry.data.channelTitle || '(unknown)';
      const error = entry.data.errorMessage || '(no error)';
      log(`  ${entry.id}`, COLORS.yellow);
      log(`    URL: ${sourceUrl}`, COLORS.reset);
      log(`    Error: ${error}`, COLORS.reset);
    }
    log('', COLORS.reset);

    log('This will:', COLORS.yellow);
    log('  1. Create entries in unresolved_channels collection', COLORS.yellow);
    log('  2. Delete these entries from scrape_progress', COLORS.yellow);
    log('', COLORS.reset);

    const confirmed = await askConfirmation('Proceed with migration?');

    if (!confirmed) {
      log('\nOperation cancelled.', COLORS.yellow);
      process.exit(0);
    }

    log('\nMigrating...', COLORS.cyan);

    // Process in batches of 250 (each entry = 1 create + 1 delete = 2 ops, max 500 per batch)
    const BATCH_SIZE = 250;
    let migrated = 0;

    for (let i = 0; i < unresolved.length; i += BATCH_SIZE) {
      const chunk = unresolved.slice(i, i + BATCH_SIZE);
      const batch = db.batch();

      for (const entry of chunk) {
        const now = Timestamp.now();
        const sourceUrl = entry.data.sourceUrl || entry.data.channelTitle || '';
        const errorMessage = entry.data.errorMessage || 'Unknown error (migrated from scrape_progress)';
        const retryCount = entry.data.retryCount || 0;
        const firstSeenAt = entry.data.startedAt || now;
        const lastAttemptAt = entry.data.lastProcessedAt || now;

        // Create in unresolved_channels
        const newRef = db.collection('unresolved_channels').doc(entry.id);
        batch.set(newRef, {
          id: entry.id,
          sourceUrl,
          errorMessage,
          retryCount,
          firstSeenAt,
          lastAttemptAt,
        });

        // Delete from scrape_progress
        const oldRef = db.collection('scrape_progress').doc(entry.id);
        batch.delete(oldRef);
      }

      await batch.commit();
      migrated += chunk.length;
      log(`  Migrated ${migrated}/${unresolved.length}`, COLORS.cyan);
    }

    log('', COLORS.reset);
    log(`Migration complete: ${migrated} entry/entries moved to unresolved_channels.`, COLORS.green);
  } catch (error) {
    log(`\nError: ${(error as Error).message}`, COLORS.red);
    process.exit(1);
  }

  console.log('\n' + '='.repeat(60) + '\n');
  process.exit(0);
}

main();
