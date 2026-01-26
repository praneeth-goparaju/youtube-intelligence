/**
 * Parse ISO 8601 duration format to seconds
 * Examples: PT15M33S -> 933, PT1H30M -> 5400, PT45S -> 45
 */
export function parseDuration(isoDuration: string): number {
  if (!isoDuration || !isoDuration.startsWith('PT')) {
    return 0;
  }

  const duration = isoDuration.substring(2); // Remove 'PT'
  let totalSeconds = 0;

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
 */
export function isShortVideo(durationSeconds: number): boolean {
  return durationSeconds <= 60;
}
