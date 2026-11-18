import type { SandboxMode } from '../types.js';

const SENSITIVE_KEY_PATTERN = /(TOKEN|SECRET|KEY|PASSWORD|AUTH|CREDENTIAL|PASSWD|PRIVATE|CERT|SESSION|COOKIE|BEARER|PIN|DSN|CONN_STR|CONNECTION_STRING)/i;
const SENSITIVE_PREFIX_PATTERN = /^(AWS_|GITHUB_|GH_|AZURE_|GCP_|GOOGLE_|OPENAI_|ANTHROPIC_|SLACK_|DISCORD_|STRIPE_|DATABASE_|DB_|PG_|MONGO_|REDIS_|SMTP_|KUBECONFIG$|SSH_AUTH_SOCK$)/i;
const DANGEROUS_OVERRIDE_KEYS = new Set([
  'NODE_OPTIONS',
  'LD_PRELOAD',
  'LD_LIBRARY_PATH',
  'DYLD_INSERT_LIBRARIES',
  'DYLD_LIBRARY_PATH',
  'PATH',
  'GIT_SSH_COMMAND',
  'GIT_EXEC_PATH',
  'ELECTRON_RUN_AS_NODE',
  'UV_THREADPOOL_SIZE',
]);

/**
 * Scrubs sensitive host credentials, tokens, and API keys from environment variables
 * and blocks dangerous runtime/loader overrides from caller-supplied values.
 */
export function sanitizeEnvironment(
  overrides?: Record<string, string>,
  _sandboxMode: SandboxMode = 'strict'
): NodeJS.ProcessEnv {
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
      if (DANGEROUS_OVERRIDE_KEYS.has(k.toUpperCase())) {
        continue;
      }
      cleanEnv[k] = v;
    }
  }

  return cleanEnv;
}
