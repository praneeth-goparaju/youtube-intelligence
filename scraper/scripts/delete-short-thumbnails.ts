import { config as dotenvConfig } from 'dotenv';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';
import { initializeApp, cert, getApps } from 'firebase-admin/app';
import { getFirestore, Firestore } from 'firebase-admin/firestore';
import { getStorage } from 'firebase-admin/storage';
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
  return { db: getFirestore(), bucket: getStorage().bucket() };
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

interface ShortWithThumbnail {
  channelId: string;
  videoId: string;
  thumbnailStoragePath: string;
}

async function findShortsWithThumbnails(db: Firestore): Promise<ShortWithThumbnail[]> {
  const channelsSnapshot = await db.collection('channels').get();
  const results: ShortWithThumbnail[] = [];

  for (const channelDoc of channelsSnapshot.docs) {
    const channelId = channelDoc.id;
    const videosSnapshot = await db
      .collection('channels')
      .doc(channelId)
      .collection('videos')
      .where('isShort', '==', true)
      .get();

    for (const videoDoc of videosSnapshot.docs) {
      const data = videoDoc.data();
      if (data.thumbnailStoragePath && data.thumbnailStoragePath !== '') {
        results.push({
          channelId,
          videoId: videoDoc.id,
          thumbnailStoragePath: data.thumbnailStoragePath,
        });
      }
    }
  }

  return results;
}

async function main(): Promise<void> {
  console.log('\n' + '='.repeat(60));
  console.log('  YouTube Intelligence System - Delete Short Thumbnails');
  console.log('='.repeat(60) + '\n');

  try {
    const { db, bucket } = initFirebase();

    log('Scanning for shorts with thumbnails...', COLORS.cyan);
    const shorts = await findShortsWithThumbnails(db);

    if (shorts.length === 0) {
      log('No shorts with thumbnails found.', COLORS.yellow);
      process.exit(0);
    }

    // Count unique channels
    const uniqueChannels = new Set(shorts.map((s) => s.channelId));

    log(`Found ${shorts.length} short(s) with thumbnails across ${uniqueChannels.size} channel(s).`, COLORS.cyan);
    log('', COLORS.reset);
    log('This will:', COLORS.yellow);
    log('  1. Delete thumbnail files from Firebase Storage', COLORS.yellow);
    log('  2. Clear thumbnailStoragePath in Firestore video documents', COLORS.yellow);
    log('', COLORS.reset);

    const confirmed = await askConfirmation('Proceed with deletion?');

    if (!confirmed) {
      log('\nOperation cancelled.', COLORS.yellow);
      process.exit(0);
    }

    // Delete files from Storage with concurrency limit
    log('\nDeleting thumbnail files from Storage...', COLORS.cyan);
    const CONCURRENCY = 20;
    let storageDeleted = 0;
    let storageErrors = 0;
    let nextIndex = 0;

    async function deleteWorker(): Promise<void> {
      while (nextIndex < shorts.length) {
        const idx = nextIndex++;
        const entry = shorts[idx];

        try {
          await bucket.file(entry.thumbnailStoragePath).delete();
          storageDeleted++;
        } catch (error: any) {
          if (error?.code === 404 || error?.errors?.[0]?.reason === 'notFound') {
            // File already gone, count as success
            storageDeleted++;
          } else {
            storageErrors++;
            log(`  Failed to delete ${entry.thumbnailStoragePath}: ${(error as Error).message}`, COLORS.red);
          }
        }

        const total = storageDeleted + storageErrors;
        if (total % 100 === 0 || total === shorts.length) {
          log(`  Storage: ${total}/${shorts.length} processed`, COLORS.cyan);
        }
      }
    }

    const workers = Array.from(
      { length: Math.min(CONCURRENCY, shorts.length) },
      () => deleteWorker()
    );
    await Promise.all(workers);

    // Batch-update Firestore documents to clear thumbnailStoragePath
    log('\nClearing thumbnailStoragePath in Firestore...', COLORS.cyan);
    const BATCH_SIZE = 500;
    let firestoreUpdated = 0;

    for (let i = 0; i < shorts.length; i += BATCH_SIZE) {
      const chunk = shorts.slice(i, i + BATCH_SIZE);
      const batch = db.batch();

      for (const entry of chunk) {
        const ref = db
          .collection('channels')
          .doc(entry.channelId)
          .collection('videos')
          .doc(entry.videoId);
        batch.update(ref, { thumbnailStoragePath: '' });
      }

      await batch.commit();
      firestoreUpdated += chunk.length;
      log(`  Firestore: ${firestoreUpdated}/${shorts.length} updated`, COLORS.cyan);
    }

    log('', COLORS.reset);
    log('='.repeat(40), COLORS.reset);
    log(`Storage files deleted: ${storageDeleted}`, COLORS.green);
    if (storageErrors > 0) {
      log(`Storage errors: ${storageErrors}`, COLORS.red);
    }
    log(`Firestore paths cleared: ${firestoreUpdated}`, COLORS.green);
  } catch (error) {
    log(`\nError: ${(error as Error).message}`, COLORS.red);
    process.exit(1);
  }

  console.log('\n' + '='.repeat(60) + '\n');
  process.exit(0);
}

main();
