import {
  timingSafeEqualStr,
  extractBearerKey,
  validateApiKey,
  parseAllowedOrigins,
  withHttpGuards,
  requireCallableAuth,
} from '../src/middleware';

// Mock the Firestore-backed rate limiter so guard tests run without firebase-admin.
jest.mock('../src/rate-limiter', () => ({
  checkRateLimit: jest.fn(),
}));
import { checkRateLimit } from '../src/rate-limiter';
const mockCheckRateLimit = checkRateLimit as jest.MockedFunction<typeof checkRateLimit>;

// Silence expected auth/CORS warnings so test output stays clean.
beforeEach(() => {
  jest.spyOn(console, 'warn').mockImplementation(() => {});
  jest.spyOn(console, 'error').mockImplementation(() => {});
});

afterEach(() => {
  jest.restoreAllMocks();
  mockCheckRateLimit.mockReset();
});

// ============================================
// timingSafeEqualStr
// ============================================

describe('timingSafeEqualStr', () => {
  it('returns true for identical strings', () => {
    expect(timingSafeEqualStr('s3cr3t-key', 's3cr3t-key')).toBe(true);
  });

  it('returns false for different strings of equal length', () => {
    expect(timingSafeEqualStr('aaaaaa', 'aaaaab')).toBe(false);
  });

  it('returns false for strings of different length without throwing', () => {
    expect(timingSafeEqualStr('short', 'a-much-longer-key')).toBe(false);
  });

  it('treats two empty strings as equal', () => {
    expect(timingSafeEqualStr('', '')).toBe(true);
  });

  it('handles unicode safely', () => {
    expect(timingSafeEqualStr('కీ', 'కీ')).toBe(true);
    expect(timingSafeEqualStr('కీ', 'key')).toBe(false);
  });
});

// ============================================
// extractBearerKey
// ============================================

describe('extractBearerKey', () => {
  it('returns empty string for undefined', () => {
    expect(extractBearerKey(undefined)).toBe('');
  });

  it('strips the "Bearer " prefix', () => {
    expect(extractBearerKey('Bearer abc123')).toBe('abc123');
  });

  it('returns the raw value when no prefix is present', () => {
    expect(extractBearerKey('abc123')).toBe('abc123');
  });
});

// ============================================
// validateApiKey
// ============================================

describe('validateApiKey', () => {
  it('rejects when no key is configured (fail closed)', () => {
    expect(validateApiKey('Bearer anything', '')).toBe(false);
  });

  it('rejects a missing authorization header', () => {
    expect(validateApiKey(undefined, 'configured')).toBe(false);
  });

  it('accepts a matching bearer key', () => {
    expect(validateApiKey('Bearer configured', 'configured')).toBe(true);
  });

  it('accepts a matching bare key (no Bearer prefix)', () => {
    expect(validateApiKey('configured', 'configured')).toBe(true);
  });

  it('rejects a non-matching key', () => {
    expect(validateApiKey('Bearer wrong', 'configured')).toBe(false);
  });
});

// ============================================
// parseAllowedOrigins
// ============================================

describe('parseAllowedOrigins', () => {
  it('returns false when unset (deny all cross-origin)', () => {
    expect(parseAllowedOrigins('')).toBe(false);
  });

  it('rejects a wildcard origin', () => {
    expect(parseAllowedOrigins('*')).toBe(false);
  });

  it('accepts an https origin', () => {
    expect(parseAllowedOrigins('https://example.com')).toEqual(['https://example.com']);
  });

  it('accepts http://localhost for local dev', () => {
    expect(parseAllowedOrigins('http://localhost:3000')).toEqual(['http://localhost:3000']);
  });

  it('trims and keeps only valid origins', () => {
    expect(parseAllowedOrigins('https://a.com , *, http://evil.com, https://b.com')).toEqual([
      'https://a.com',
      'https://b.com',
    ]);
  });

  it('returns false when no origin survives validation', () => {
    expect(parseAllowedOrigins('http://evil.com, ftp://x')).toBe(false);
  });
});

// ============================================
// withHttpGuards
// ============================================

interface FakeRes {
  statusCode: number;
  body: unknown;
  headers: Record<string, string>;
  status: jest.Mock;
  json: jest.Mock;
  setHeader: jest.Mock;
}

function makeRes(): FakeRes {
  const res: FakeRes = {
    statusCode: 0,
    body: undefined,
    headers: {},
    status: jest.fn(),
    json: jest.fn(),
    setHeader: jest.fn(),
  };
  res.status.mockImplementation((code: number) => {
    res.statusCode = code;
    return res;
  });
  res.json.mockImplementation((body: unknown) => {
    res.body = body;
    return res;
  });
  res.setHeader.mockImplementation((key: string, value: string) => {
    res.headers[key] = value;
  });
  return res;
}

function makeReq(overrides: { method?: string; authorization?: string } = {}) {
  return {
    method: overrides.method ?? 'POST',
    headers: { authorization: overrides.authorization ?? 'Bearer secret' },
    body: {},
    query: {},
  };
}

const guardOpts = {
  method: 'POST' as const,
  getApiKey: () => 'secret',
  rateLimit: { max: 100, windowMs: 1000 },
};

describe('withHttpGuards', () => {
  it('rejects the wrong HTTP method with 405 and skips the handler', async () => {
    const handler = jest.fn();
    const wrapped = withHttpGuards(guardOpts, handler as never);
    const res = makeRes();

    await wrapped(makeReq({ method: 'GET' }) as never, res as never);

    expect(res.statusCode).toBe(405);
    expect(handler).not.toHaveBeenCalled();
    expect(mockCheckRateLimit).not.toHaveBeenCalled();
  });

  it('rejects an invalid API key with 401 and skips the handler', async () => {
    const handler = jest.fn();
    const wrapped = withHttpGuards(guardOpts, handler as never);
    const res = makeRes();

    await wrapped(makeReq({ authorization: 'Bearer wrong' }) as never, res as never);

    expect(res.statusCode).toBe(401);
    expect(handler).not.toHaveBeenCalled();
    expect(mockCheckRateLimit).not.toHaveBeenCalled();
  });

  it('returns 429 and the remaining header when rate limited', async () => {
    mockCheckRateLimit.mockResolvedValue({ allowed: false, remaining: 0 });
    const handler = jest.fn();
    const wrapped = withHttpGuards(guardOpts, handler as never);
    const res = makeRes();

    await wrapped(makeReq() as never, res as never);

    expect(res.statusCode).toBe(429);
    expect(res.headers['X-RateLimit-Remaining']).toBe('0');
    expect(handler).not.toHaveBeenCalled();
  });

  it('runs the handler and sets the remaining header when all guards pass', async () => {
    mockCheckRateLimit.mockResolvedValue({ allowed: true, remaining: 99 });
    const handler = jest.fn(async (_req: unknown, r: FakeRes) => {
      r.status(200);
      r.json({ ok: true });
    });
    const wrapped = withHttpGuards(guardOpts, handler as never);
    const res = makeRes();

    await wrapped(makeReq() as never, res as never);

    expect(handler).toHaveBeenCalledTimes(1);
    expect(res.statusCode).toBe(200);
    expect(res.headers['X-RateLimit-Remaining']).toBe('99');
  });
});

// ============================================
// requireCallableAuth
// ============================================

const callableRateLimit = { max: 100, windowMs: 1000 };

describe('requireCallableAuth', () => {
  it('throws unauthenticated when the request has no auth context', async () => {
    await expect(
      requireCallableAuth({ auth: undefined } as never, callableRateLimit)
    ).rejects.toMatchObject({ code: 'unauthenticated' });
    expect(mockCheckRateLimit).not.toHaveBeenCalled();
  });

  it('throws resource-exhausted when the UID is rate limited', async () => {
    mockCheckRateLimit.mockResolvedValue({ allowed: false, remaining: 0 });
    await expect(
      requireCallableAuth({ auth: { uid: 'user-1' } } as never, callableRateLimit)
    ).rejects.toMatchObject({ code: 'resource-exhausted' });
  });

  it('returns the UID when authenticated and within the limit', async () => {
    mockCheckRateLimit.mockResolvedValue({ allowed: true, remaining: 99 });
    const uid = await requireCallableAuth({ auth: { uid: 'user-1' } } as never, callableRateLimit);
    expect(uid).toBe('user-1');
    expect(mockCheckRateLimit).toHaveBeenCalledWith('user-1', 100, 1000);
  });
});
