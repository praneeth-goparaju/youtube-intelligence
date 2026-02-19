import { config as dotenvConfig } from 'dotenv';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';
import { initializeApp, cert, getApps } from 'firebase-admin/app';
import { getFirestore } from 'firebase-admin/firestore';

const __dirname = dirname(fileURLToPath(import.meta.url));
dotenvConfig({ path: resolve(__dirname, '../../.env') });

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

async function checkStatus() {
  const db = initFirebase();
  const snapshot = await db.collection('scrape_progress').get();
  const allProgress = snapshot.docs.map((doc) => ({ id: doc.id, ...doc.data() })) as any[];

  const failed = allProgress.filter((p) => p.status === 'failed');
  const inProgress = allProgress.filter((p) => p.status === 'in_progress');
  const pending = allProgress.filter((p) => p.status === 'pending');
  const completed = allProgress.filter((p) => p.status === 'completed');

  console.log(`\n=== Scrape Progress Summary ===`);
  console.log(`Completed:   ${completed.length}`);
  console.log(`In Progress: ${inProgress.length}`);
  console.log(`Pending:     ${pending.length}`);
  console.log(`Failed:      ${failed.length}`);
  console.log(`Total:       ${allProgress.length}`);

  if (failed.length > 0) {
    console.log(`\n=== Failed Channels ===`);
    for (const p of failed) {
      console.log(`\n  Channel: ${p.channelTitle || p.channelId}`);
      console.log(`  URL:     ${p.sourceUrl}`);
      console.log(`  Error:   ${p.errorMessage}`);
      console.log(`  Retries: ${p.retryCount}/3`);
      console.log(`  Videos:  ${p.videosProcessed}/${p.totalVideos} processed`);
    }
  }

  if (inProgress.length > 0) {
    console.log(`\n=== Stuck In-Progress (possibly interrupted) ===`);
    for (const p of inProgress) {
      console.log(`\n  Channel: ${p.channelTitle || p.channelId}`);
      console.log(`  URL:     ${p.sourceUrl}`);
      console.log(`  Phase:   ${p.phase}`);
      console.log(`  Videos:  ${p.videosProcessed}/${p.totalVideos} processed`);
    }
  }

  process.exit(0);
}

checkStatus().catch((err) => {
  console.error('Error:', err);
  process.exit(1);
});
