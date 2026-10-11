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
 * Infer Shorts from explicit metadata. The public API does not expose aspect
 * ratio, so a positive hashtag match remains an inference, not a certainty.
 */
export function isShortVideoDetailed({
  durationSeconds, title, description, publishedAt, videoId,
}: {
  durationSeconds: number;
  title: string;
  description: string;
  publishedAt: Date;
  videoId: string;
}): { isShort: boolean; confidence: 'high' | 'medium' | 'low'; reason: string } {
  if (!Number.isFinite(durationSeconds) || durationSeconds <= 0) {
    return { isShort: false, confidence: 'low', reason: 'No usable duration' };
  }
  const maximumDuration = publishedAt.getTime() < Date.parse('2024-10-15T00:00:00Z') ? 60 : 180;
  if (durationSeconds > maximumDuration) {
    return { isShort: false, confidence: 'high', reason: `Duration exceeds ${maximumDuration} seconds` };
  }

  const hasHashtag = /#shorts?\b/i.test(title) || /#shorts?\b/i.test(description);
  const hasOwnShortsLink = (description.match(/https?:\/\/[^\s]+/g) ?? []).some((link) => {
    try {
      const url = new URL(link);
      return ['youtube.com', 'www.youtube.com', 'm.youtube.com'].includes(url.hostname) &&
        url.pathname.replace(/\/$/, '') === `/shorts/${videoId}`;
    } catch {
      return false;
    }
  });
  if (hasHashtag || hasOwnShortsLink) {
    return {
      isShort: true, confidence: 'medium',
      reason: hasHashtag ? '#Shorts metadata found; aspect ratio unavailable' : 'Own Shorts URL found; aspect ratio unavailable',
    };
  }
  return { isShort: false, confidence: 'low', reason: 'No explicit Shorts metadata; duration alone is insufficient' };
}
