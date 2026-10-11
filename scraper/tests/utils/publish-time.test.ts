import { execFileSync } from 'node:child_process';
import { describe, expect, it } from 'vitest';
import { getDayOfWeek } from '../../src/utils/helpers.js';

describe('publish time in India', () => {
  it('uses the same timezone for the publication weekday and hour', () => {
    expect(getDayOfWeek(new Date('2025-01-01T20:00:00Z'))).toBe('Thursday');
  });

  it.each(['UTC', 'Europe/Berlin', 'America/Los_Angeles'])('is independent of host timezone %s across daylight-saving transitions', (timezone) => {
    const moduleUrl = new URL('../../src/utils/helpers.ts', import.meta.url).href;
    const script = `import { getHourIST } from ${JSON.stringify(moduleUrl)};
      process.stdout.write(JSON.stringify(['2024-03-31T00:00:00Z', '2024-10-27T00:00:00Z'].map((date) => getHourIST(new Date(date)))));`;
    const output = execFileSync(process.execPath, ['--throw-deprecation', '--import', 'tsx', '--input-type=module', '--eval', script], {
      env: { ...process.env, TZ: timezone }, encoding: 'utf8',
    });
    expect(JSON.parse(output)).toEqual([5, 5]);
  });
});
