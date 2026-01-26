import { initializeApp, cert, getApps, App } from 'firebase-admin/app';
import { getFirestore, Firestore } from 'firebase-admin/firestore';
import { getStorage, Storage } from 'firebase-admin/storage';
import { config } from '../config.js';

let app: App | null = null;
let db: Firestore | null = null;
let storage: Storage | null = null;

/**
 * Initialize Firebase Admin SDK
 */
export function initializeFirebase(): App {
  if (getApps().length > 0) {
    app = getApps()[0];
    return app;
  }

  app = initializeApp({
    credential: cert({
      projectId: config.firebase.projectId,
      clientEmail: config.firebase.clientEmail,
      privateKey: config.firebase.privateKey,
    }),
    storageBucket: config.firebase.storageBucket,
  });

  return app;
}

/**
 * Get Firestore instance
 */
export function getDb(): Firestore {
  if (!db) {
    if (!app) {
      initializeFirebase();
    }
    db = getFirestore();
  }
  return db;
}

/**
 * Get Storage instance
 */
export function getStorageInstance(): Storage {
  if (!storage) {
    if (!app) {
      initializeFirebase();
    }
    storage = getStorage();
  }
  return storage;
}

/**
 * Get the storage bucket
 */
export function getBucket() {
  return getStorageInstance().bucket();
}

/**
 * Test Firebase connection
 */
export async function testFirebaseConnection(): Promise<boolean> {
  try {
    const firestore = getDb();
    // Try to read a document (will create collection if doesn't exist)
    await firestore.collection('_test').doc('connection').get();
    return true;
  } catch (error) {
    console.error('Firebase connection test failed:', error);
    return false;
  }
}
