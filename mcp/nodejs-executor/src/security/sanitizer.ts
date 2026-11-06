import type { SandboxMode } from '../types.js';

const SENSITIVE_KEY_PATTERN = /(TOKEN|SECRET|KEY|PASSWORD|AUTH|CREDENTIAL|PASSWD|PRIVATE|CERT|SESSION|COOKIE|BEARER|PIN)/i;
const SENSITIVE_PREFIX_PATTERN = /^(AWS_|GITHUB_|GH_|AZURE_|GCP_|GOOGLE_|OPENAI_|ANTHROPIC_|SLACK_|DISCORD_|STRIPE_|DATABASE_|DB_|PG_|MONGO_|REDIS_)/i;

/**
 * Scrubs sensitive host credentials, tokens, and API keys from environment variables
 */
export function sanitizeEnvironment(
  overrides?: Record<string, string>,
  sandboxMode: SandboxMode = 'strict'
): NodeJS.ProcessEnv {
  if (sandboxMode === 'unrestricted') {
    return {
      ...process.env,
      ...(overrides ?? {}),
    };
  }

  const cleanEnv: NodeJS.ProcessEnv = {};

  for (const [key, value] of Object.entries(process.env)) {
    if (!key || value === undefined) continue;

    if (SENSITIVE_KEY_PATTERN.test(key) || SENSITIVE_PREFIX_PATTERN.test(key)) {
      continue;
    }

    cleanEnv[key] = value;
  }

  cleanEnv.NODE_ENV = overrides?.NODE_ENV || 'development';

  if (overrides) {
    for (const [k, v] of Object.entries(overrides)) {
      cleanEnv[k] = v;
    }
  }

  return cleanEnv;
}

