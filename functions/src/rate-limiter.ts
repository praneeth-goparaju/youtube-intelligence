/**
 * Firestore-based distributed rate limiter.
 *
 * Stores rate limit counters in Firestore so they persist across
 * function cold starts and work across multiple instances.
 */

import * as admin from 'firebase-admin';
import { createHash } from 'crypto';

const RATE_LIMIT_COLLECTION = 'rateLimits';

interface RateLimitRecord {
  count: number;
  windowStart: number;
}

/**
 * Check and update rate limit for a given key using Firestore.
 *
 * Uses a Firestore transaction to atomically read and increment the counter.
 * Falls back to allowing the request if Firestore is unavailable.
 */
export async function checkRateLimit(
  key: string,
  maxRequests: number,
  windowMs: number
): Promise<{ allowed: boolean; remaining: number }> {
  const db = admin.firestore();
  const now = Date.now();

  // Hash key for use as Firestore document ID (avoids storing raw API keys/tokens)
  const docId = createHash('sha256').update(key).digest('hex').slice(0, 64);
  const docRef = db.collection(RATE_LIMIT_COLLECTION).doc(docId);

  try {
    const result = await db.runTransaction(async (txn) => {
      const doc = await txn.get(docRef);
      const data = doc.data() as RateLimitRecord | undefined;

      // If no record or window expired, start new window
      if (!data || now - data.windowStart >= windowMs) {
        txn.set(docRef, { count: 1, windowStart: now });
        return { allowed: true, remaining: maxRequests - 1 };
      }

      // Window still active
      if (data.count >= maxRequests) {
        return { allowed: false, remaining: 0 };
      }

      txn.update(docRef, { count: data.count + 1 });
      return { allowed: true, remaining: maxRequests - (data.count + 1) };
    });

    return result;
  } catch (error) {
    // If Firestore fails, deny the request (fail-closed)
    console.error('Rate limiter Firestore error (denying request):', {
      hashedKey: docId.slice(0, 16),
      errorType: error instanceof Error ? error.constructor.name : typeof error,
      errorMessage: error instanceof Error ? error.message : String(error),
    });
    return { allowed: false, remaining: 0 };
  }
}
