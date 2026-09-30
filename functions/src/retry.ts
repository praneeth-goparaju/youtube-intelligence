/**
 * Retry helper with per-attempt timeout and an overall deadline.
 *
 * Pure (no Firebase / SDK dependencies) so it can be unit-tested.
 */

export class DeadlineExceededError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'DeadlineExceededError';
  }
}

export interface RetryOptions {
  maxAttempts: number;
  baseDelayMs: number;
  /** Overall wall-clock budget for all attempts and backoff delays. */
  totalBudgetMs: number;
  /** Upper bound for a single attempt (further capped by remaining budget). */
  attemptTimeoutMs: number;
  /** Don't start an attempt with less than this much budget left. */
  minAttemptMs?: number;
  label?: string;
  /** Injectable clock/sleep for tests. */
  now?: () => number;
  sleep?: (ms: number) => Promise<void>;
}

const defaultSleep = (ms: number): Promise<void> => new Promise((resolve) => setTimeout(resolve, ms));

/**
 * Race `fn` against a timeout. The AbortSignal passed to `fn` is aborted when
 * the timeout fires, so SDKs that honour it can cancel the in-flight request.
 */
export async function withTimeout<T>(
  fn: (signal: AbortSignal, timeoutMs: number) => Promise<T>,
  timeoutMs: number,
  label = 'operation'
): Promise<T> {
  const controller = new AbortController();
  let timer: ReturnType<typeof setTimeout> | undefined;
  const timeout = new Promise<never>((_, reject) => {
    timer = setTimeout(() => {
      controller.abort();
      reject(new DeadlineExceededError(`${label} timed out after ${timeoutMs}ms`));
    }, timeoutMs);
  });
  try {
    return await Promise.race([fn(controller.signal, timeoutMs), timeout]);
  } finally {
    if (timer) clearTimeout(timer);
  }
}

/**
 * Run `fn` up to `maxAttempts` times with exponential backoff (longer for
 * rate-limit errors), never exceeding `totalBudgetMs` overall. Throws the last
 * error (or a DeadlineExceededError) when attempts or budget run out.
 */
export async function runWithRetries<T>(
  fn: (signal: AbortSignal, timeoutMs: number) => Promise<T>,
  options: RetryOptions
): Promise<T> {
  const now = options.now ?? Date.now;
  const sleep = options.sleep ?? defaultSleep;
  const label = options.label ?? 'operation';
  const minAttemptMs = options.minAttemptMs ?? 5_000;
  const deadline = now() + options.totalBudgetMs;
  let lastError: Error | undefined;

  for (let attempt = 0; attempt < options.maxAttempts; attempt++) {
    const remaining = deadline - now();
    if (remaining < minAttemptMs) {
      break;
    }
    const attemptTimeout = Math.min(options.attemptTimeoutMs, remaining);

    try {
      return await withTimeout(fn, attemptTimeout, `${label} attempt ${attempt + 1}`);
    } catch (error) {
      lastError = error instanceof Error ? error : new Error(String(error));
      const message = lastError.message || String(error);
      const isRateLimit = message.includes('429') || message.toLowerCase().includes('rate limit');

      if (attempt < options.maxAttempts - 1) {
        const waitTime = options.baseDelayMs * Math.pow(2, attempt) * (isRateLimit ? 2 : 1);
        if (deadline - now() - waitTime < minAttemptMs) {
          console.warn(`${label} attempt ${attempt + 1} failed: ${message}. No budget left for another attempt.`);
          break;
        }
        console.warn(`${label} attempt ${attempt + 1} failed: ${message}. Retrying in ${waitTime}ms...`);
        await sleep(waitTime);
      } else {
        console.error(`${label} failed after ${options.maxAttempts} attempts:`, lastError);
      }
    }
  }

  throw lastError || new DeadlineExceededError(`${label} deadline of ${options.totalBudgetMs}ms exhausted`);
}
