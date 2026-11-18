import * as fs from 'node:fs/promises';
import * as os from 'node:os';
import * as path from 'node:path';
import { runProcess } from '../process/runner.js';
import { getPermissionFlags, supportsNativeTypeScript } from '../security/permissions.js';
import { sanitizeEnvironment } from '../security/sanitizer.js';
import { isAllowedWorkspaceOrTempPath, preExecutionSecurityCheck } from '../security/validator.js';
import type { ExecuteFileOptions, ExecutionResult } from '../types.js';

const DEFAULT_TIMEOUT_MS = 30000;
const MAX_TIMEOUT_MS = 300000;

export async function executeFile(options: ExecuteFileOptions): Promise<ExecutionResult> {
  const sandboxMode = options.sandboxMode ?? 'strict';
  const timeoutMs = Math.min(Math.max(options.timeout ?? DEFAULT_TIMEOUT_MS, 100), MAX_TIMEOUT_MS);
  const cwd = options.workingDirectory ? path.resolve(options.workingDirectory) : process.cwd();
  const filePath = path.resolve(cwd, options.filePath);

  if (!isAllowedWorkspaceOrTempPath(cwd) || !isAllowedWorkspaceOrTempPath(filePath)) {
    return {
      success: false,
      exitCode: 1,
      stdout: '',
      stderr: `Security rejection: filePath "${filePath}" and workingDirectory "${cwd}" must reside within workspace or temp directory.`,
      durationMs: 0,
      timedOut: false,
      error: 'Path outside allowed workspace/temp boundary',
      sandboxMode,
    };
  }

  let fileContent = '';
  try {
    const stat = await fs.stat(filePath);
    if (!stat.isFile()) {
      return {
        success: false,
        exitCode: 1,
        stdout: '',
        stderr: `Target path is not a file: ${filePath}`,
        durationMs: 0,
        timedOut: false,
        error: `Target path is not a file: ${filePath}`,
        sandboxMode,
      };
    }
    fileContent = await fs.readFile(filePath, 'utf8');
  } catch {
    return {
      success: false,
      exitCode: 1,
      stdout: '',
      stderr: `File not found: ${filePath}`,
      durationMs: 0,
      timedOut: false,
      error: `File not found: ${filePath}`,
      sandboxMode,
    };
  }

  const safetyCheck = preExecutionSecurityCheck(fileContent, sandboxMode);
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

  const isTs = filePath.endsWith('.ts') || filePath.endsWith('.mts') || filePath.endsWith('.cts');
  const tempDir = await fs.mkdtemp(path.join(os.tmpdir(), 'node-mcp-file-'));

  try {
    const permFlags = getPermissionFlags(tempDir, cwd, sandboxMode, options.allowFsWritePaths, [
      path.dirname(filePath),
    ]);
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

    args.push(filePath, ...(options.args ?? []));
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
