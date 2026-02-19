/**
 * Parse ISO 8601 duration format to seconds
 * Examples: PT15M33S -> 933, PT1H30M -> 5400, PT45S -> 45
 */
export function parseDuration(isoDuration: string): number {
  if (!isoDuration) {
    return 0;
  }

  // Handle P1DT2H3M4S format (with day component)
  let remaining = isoDuration;
  let totalSeconds = 0;

  if (remaining.startsWith('P')) {
    remaining = remaining.substring(1);
    const dayMatch = remaining.match(/(\d+)D/);
    if (dayMatch) {
      totalSeconds += parseInt(dayMatch[1], 10) * 86400;
    }
  }

  // Remove 'T' separator if present
  const tIndex = remaining.indexOf('T');
  const duration = tIndex >= 0 ? remaining.substring(tIndex + 1) : remaining;

  // Match hours
  const hoursMatch = duration.match(/(\d+)H/);
  if (hoursMatch) {
    totalSeconds += parseInt(hoursMatch[1], 10) * 3600;
  }

  // Match minutes
  const minutesMatch = duration.match(/(\d+)M/);
  if (minutesMatch) {
    totalSeconds += parseInt(minutesMatch[1], 10) * 60;
  }

  // Match seconds
  const secondsMatch = duration.match(/(\d+)S/);
  if (secondsMatch) {
    totalSeconds += parseInt(secondsMatch[1], 10);
  }

  return totalSeconds;
}

/**
 * Format seconds to human-readable duration
 */
export function formatDuration(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;

  if (hours > 0) {
    return `${hours}h ${minutes}m ${secs}s`;
  } else if (minutes > 0) {
    return `${minutes}m ${secs}s`;
  } else {
    return `${secs}s`;
  }
}

/**
 * Check if duration indicates a YouTube Short (< 60 seconds)
 * @deprecated Use isShortVideoDetailed for more accurate detection
 */
export function isShortVideo(durationSeconds: number): boolean {
  return durationSeconds <= 60;
}

/**
 * Detect if a video is a YouTube Short using multiple signals:
 * 1. Duration <= 60 seconds (required)
 * 2. #Shorts hashtag in title or description (strong indicator)
 * 3. Common Short-related patterns
 *
 * Note: Duration alone is not sufficient - a 45-second normal video is not a Short
 * The #Shorts hashtag or similar indicators help distinguish actual Shorts
 */
export function isShortVideoDetailed(
  durationSeconds: number,
  title: string,
  description: string
): { isShort: boolean; confidence: 'high' | 'medium' | 'low'; reason: string } {
  // Shorts must be <= 60 seconds
  if (durationSeconds > 60) {
    return { isShort: false, confidence: 'high', reason: 'Duration exceeds 60 seconds' };
  }

  // Check for #Shorts hashtag (case-insensitive)
  const shortsHashtagRegex = /#shorts?\b/i;
  const hasHashtagInTitle = shortsHashtagRegex.test(title);
  const hasHashtagInDescription = shortsHashtagRegex.test(description);

  if (hasHashtagInTitle || hasHashtagInDescription) {
    return {
      isShort: true,
      confidence: 'high',
      reason: `#Shorts hashtag found in ${hasHashtagInTitle ? 'title' : 'description'}`
    };
  }

  // Check for youtube.com/shorts/ URL pattern in description
  if (description.includes('youtube.com/shorts/') || description.includes('youtu.be/shorts/')) {
    return { isShort: true, confidence: 'high', reason: 'Shorts URL found in description' };
  }

  // Very short videos (<=15s) are more likely to be Shorts
  if (durationSeconds <= 15) {
    return { isShort: true, confidence: 'medium', reason: 'Very short duration (<=15s)' };
  }

  // Videos between 16-60s without #Shorts are uncertain
  // Default to considering them as regular short videos, not Shorts
  return {
    isShort: false,
    confidence: 'low',
    reason: 'Duration <=60s but no #Shorts indicator found'
  };
}
