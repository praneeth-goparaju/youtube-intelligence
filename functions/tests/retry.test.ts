import { runWithRetries, withTimeout, DeadlineExceededError } from '../src/retry';

const never = () => new Promise<string>(() => { /* hangs forever */ });

describe('withTimeout', () => {
  it('rejects and aborts the signal when the operation hangs', async () => {
    let seenSignal: AbortSignal | undefined;
    await expect(
      withTimeout((signal) => { seenSignal = signal; return never(); }, 20, 'op')
    ).rejects.toBeInstanceOf(DeadlineExceededError);
    expect(seenSignal?.aborted).toBe(true);
  });

  it('resolves with the value when fast enough', async () => {
    await expect(withTimeout(async () => 'ok', 1000)).resolves.toBe('ok');
  });
});

describe('runWithRetries', () => {
  const base = { maxAttempts: 3, baseDelayMs: 1, minAttemptMs: 1, label: 'test' };

  beforeEach(() => {
    jest.spyOn(console, 'warn').mockImplementation(() => undefined);
    jest.spyOn(console, 'error').mockImplementation(() => undefined);
  });
  afterEach(() => jest.restoreAllMocks());

  it('retries after a failure and returns the eventual result', async () => {
    let calls = 0;
    const result = await runWithRetries(async () => {
      calls++;
      if (calls < 2) throw new Error('boom');
      return 'ok';
    }, { ...base, totalBudgetMs: 1000, attemptTimeoutMs: 500 });
    expect(result).toBe('ok');
    expect(calls).toBe(2);
  });

  it('gives up within the overall budget when every attempt hangs', async () => {
    const start = Date.now();
    await expect(
      runWithRetries(() => never(), { ...base, totalBudgetMs: 150, attemptTimeoutMs: 1000 })
    ).rejects.toBeInstanceOf(DeadlineExceededError);
    expect(Date.now() - start).toBeLessThan(1000);
  });

  it('caps each attempt timeout at the remaining budget', async () => {
    const timeouts: number[] = [];
    await expect(
      runWithRetries((_signal, timeoutMs) => { timeouts.push(timeoutMs); return never(); },
        { ...base, maxAttempts: 1, totalBudgetMs: 50, attemptTimeoutMs: 10_000 })
    ).rejects.toThrow();
    expect(timeouts[0]).toBeLessThanOrEqual(50);
  });

  it('does not start another attempt when backoff would exceed the budget', async () => {
    let calls = 0;
    await expect(
      runWithRetries(async () => { calls++; throw new Error('429 rate limit'); },
        { ...base, baseDelayMs: 10_000, minAttemptMs: 10, totalBudgetMs: 5_000, attemptTimeoutMs: 1000 })
    ).rejects.toThrow('429');
    expect(calls).toBe(1);
  });

  it('throws the last error after maxAttempts', async () => {
    let calls = 0;
    await expect(
      runWithRetries(async () => { calls++; throw new Error(`fail ${calls}`); },
        { ...base, totalBudgetMs: 1000, attemptTimeoutMs: 100 })
    ).rejects.toThrow('fail 3');
    expect(calls).toBe(3);
  });
});
