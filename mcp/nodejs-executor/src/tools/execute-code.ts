import * as fs from 'node:fs/promises';
import * as os from 'node:os';
import * as path from 'node:path';
import * as crypto from 'node:crypto';
import { runProcess } from '../process/runner.js';
import { getPermissionFlags, supportsNativeTypeScript } from '../security/permissions.js';
import { sanitizeEnvironment } from '../security/sanitizer.js';
import { preExecutionSecurityCheck } from '../security/validator.js';
import type { ExecuteCodeOptions, ExecutionResult } from '../types.js';

const DEFAULT_TIMEOUT_MS = 30000;
const MAX_TIMEOUT_MS = 300000;

export async function executeCode(options: ExecuteCodeOptions): Promise<ExecutionResult> {
  const language = options.language ?? 'javascript';
  const sandboxMode = options.sandboxMode ?? 'strict';
  const timeoutMs = Math.min(Math.max(options.timeout ?? DEFAULT_TIMEOUT_MS, 100), MAX_TIMEOUT_MS);
  const cwd = options.workingDirectory ? path.resolve(options.workingDirectory) : process.cwd();

  const safetyCheck = preExecutionSecurityCheck(options.code, sandboxMode);
  if (!safetyCheck.allowed) {
    return {
      success: false,
      exitCode: 1,
      stdout: '',
      stderr: `Security policy violation: ${safetyCheck.reason}`,
      durationMs: 0,
      timedOut: false,
      error: safetyCheck.reason,
      sandboxMode,
    };
  }

  const isTs = language === 'typescript';
  const ext = isTs ? '.ts' : '.mjs';
  const tempDir = await fs.mkdtemp(path.join(os.tmpdir(), 'node-mcp-'));
  const scriptPath = path.join(tempDir, `snippet_${crypto.randomUUID()}${ext}`);

  try {
    await fs.writeFile(scriptPath, options.code, 'utf8');

    const permFlags = getPermissionFlags(tempDir, cwd, sandboxMode, options.allowFsWritePaths);
    const args: string[] = [...permFlags];

    if (isTs) {
      if (supportsNativeTypeScript()) {
        args.push('--experimental-strip-types');
        if (!permFlags.includes('--no-warnings')) {
          args.push('--no-warnings');
        }
      } else {
        return {
          success: false,
          exitCode: 1,
          stdout: '',
          stderr: `Native TypeScript execution requires Node.js v22+ (Current: ${process.versions.node}).`,
          durationMs: 0,
          timedOut: false,
          error: 'Unsupported Node.js version for native TypeScript strip-types.',
          sandboxMode,
        };
      }
    }

    args.push(scriptPath);
    const cleanEnv = sanitizeEnvironment(options.environmentVariables, sandboxMode);

    const result = await runProcess(process.execPath, args, {
      cwd,
      env: cleanEnv,
      timeoutMs,
    });

    return { ...result, sandboxMode };
  } finally {
    try {
      await fs.rm(tempDir, { recursive: true, force: true });
    } catch {}
  }
}

