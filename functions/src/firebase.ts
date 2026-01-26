/**
 * Firebase client for accessing Firestore insights data
 */

import * as admin from 'firebase-admin';
import type { Insights, ThumbnailInsights, TitleInsights, TimingInsights, ContentGapInsights } from './types';

// Initialize Firebase Admin (only once)
if (!admin.apps.length) {
  admin.initializeApp();
}

const db = admin.firestore();

/**
 * Get all insights from Firestore
 */
export async function getAllInsights(): Promise<Insights> {
  const insights: Insights = {};

  try {
    // Fetch all insight documents in parallel
    const [thumbnails, titles, timing, contentGaps] = await Promise.all([
      getInsightDocument<ThumbnailInsights>('thumbnails'),
      getInsightDocument<TitleInsights>('titles'),
      getInsightDocument<TimingInsights>('timing'),
      getInsightDocument<ContentGapInsights>('contentGaps'),
    ]);

    if (thumbnails) insights.thumbnails = thumbnails;
    if (titles) insights.titles = titles;
    if (timing) insights.timing = timing;
    if (contentGaps) insights.contentGaps = contentGaps;
  } catch (error) {
    console.error('Error fetching insights:', error);
  }

  return insights;
}

/**
 * Get a specific insight document
 */
async function getInsightDocument<T>(type: string): Promise<T | null> {
  try {
    const doc = await db.collection('insights').doc(type).get();
    if (doc.exists) {
      return doc.data() as T;
    }
    return null;
  } catch (error) {
    console.warn(`Failed to fetch insight: ${type}`, error);
    return null;
  }
}

/**
 * Check if insights are available
 */
export async function hasInsights(): Promise<boolean> {
  try {
    const snapshot = await db.collection('insights').limit(1).get();
    return !snapshot.empty;
  } catch {
    return false;
  }
}

/**
 * Get insight metadata (for version tracking)
 */
export async function getInsightsVersion(): Promise<string | null> {
  try {
    const doc = await db.collection('insights').doc('thumbnails').get();
    if (doc.exists) {
      const data = doc.data();
      return data?.generatedAt || null;
    }
    return null;
  } catch {
    return null;
  }
}
