import * as fs from 'node:fs/promises';
import * as os from 'node:os';
import * as path from 'node:path';
import { runProcess } from '../process/runner.js';
import { sanitizeEnvironment } from '../security/sanitizer.js';
import { preExecutionSecurityCheck } from '../security/validator.js';
import type { ExecutionResult, RunTerminalCommandOptions } from '../types.js';

const SHELL_METACHARS = /[&|;><`$\n\r]/;
const MAX_TIMEOUT_MS = 300000;
const BLOCKED_BINARIES = new Set([
  'cmd', 'cmd.exe', 'powershell', 'powershell.exe', 'pwsh', 'pwsh.exe',
  'bash', 'bash.exe', 'sh', 'zsh', 'fish', 'wsl', 'wsl.exe',
  'diskpart', 'diskpart.exe', 'format', 'format.com', 'mkfs', 'fdisk',
  'reg', 'reg.exe', 'regedit', 'regedit.exe',
]);

function isPathContained(parent: string, target: string): boolean {
  const rel = path.relative(path.resolve(parent).toLowerCase(), path.resolve(target).toLowerCase());
  return !rel.startsWith('..') && !path.isAbsolute(rel);
}

function rejectResult(stderr: string, error: string): ExecutionResult {
  return {
    success: false,
    exitCode: 1,
    stdout: '',
    stderr,
    durationMs: 0,
    timedOut: false,
    error,
  };
}

export async function runTerminalCommand(
  options: RunTerminalCommandOptions
): Promise<ExecutionResult> {
  const command = (options.command ?? '').trim();
  const args = options.args ?? [];
  const timeoutMs = Math.min(Math.max(options.timeout ?? 30000, 100), MAX_TIMEOUT_MS);

  if (!command || SHELL_METACHARS.test(command) || /\s/.test(command)) {
    return rejectResult(
      `Security rejection: Invalid command "${options.command}". Pass the executable name only (no spaces or shell metacharacters) and use args[] for parameters.`,
      'Invalid terminal command'
    );
  }

  const baseBinary = path.basename(command).toLowerCase();
  if (BLOCKED_BINARIES.has(baseBinary)) {
    return rejectResult(
      `Security rejection: Direct shell or system-disk binary "${baseBinary}" is blocked by terminal policy.`,
      `Blocked binary "${baseBinary}"`
    );
  }

  for (const arg of args) {
    if (SHELL_METACHARS.test(arg)) {
      return rejectResult(
        `Security rejection: Command argument contains forbidden shell metacharacters: ${arg}`,
        'Forbidden shell metacharacters detected in arguments'
      );
    }
  }

  const safety = preExecutionSecurityCheck(`${command} ${args.join(' ')}`);
  if (!safety.allowed) {
    return rejectResult(safety.reason || 'Blocked by pre-execution safety policy.', safety.reason || 'Safety check failed');
  }

  const rootCwd = process.cwd();
  const targetCwd = options.workingDirectory ? path.resolve(rootCwd, options.workingDirectory) : rootCwd;
  if (!isPathContained(rootCwd, targetCwd) && !isPathContained(os.tmpdir(), targetCwd)) {
    return rejectResult(
      `Security rejection: workingDirectory "${targetCwd}" must reside within workspace (${rootCwd}) or temp directory.`,
      'workingDirectory outside allowed boundary'
    );
  }

  const env = sanitizeEnvironment(options.environmentVariables);
  const result = await runProcess(command, args, {
    cwd: targetCwd,
    env,
    timeoutMs,
    shell: false,
  });

  const logDir = path.join(os.tmpdir(), 'nodejs-executor-logs');
  await fs.mkdir(logDir, { recursive: true });
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const stdoutLogFile = path.join(logDir, `stdout-${timestamp}-${process.pid}.log`);
  await fs.writeFile(stdoutLogFile, result.stdout, 'utf8');

  return { ...result, stdoutLogFile };
}

