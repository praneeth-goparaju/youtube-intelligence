/**
 * Secret access helper shared by the Functions runtime and local tooling.
 */

/**
 * Read a Secret Manager-backed param.
 *
 * In the Functions runtime `secret.value()` returns the value injected for
 * functions that declare the secret in their `secrets` option. Outside that
 * runtime (CLI, tests, emulator without secrets) it may throw or be empty, so
 * fall back to `process.env[name]`. Returns '' when unset.
 */
export function readSecret(secret: { name: string; value(): string }): string {
  let value = '';
  try {
    value = secret.value() || '';
  } catch {
    value = '';
  }
  return value || process.env[secret.name] || '';
}
