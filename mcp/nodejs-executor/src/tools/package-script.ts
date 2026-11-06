import * as fs from 'node:fs/promises';
import * as path from 'node:path';
import { runProcess } from '../process/runner.js';
import type { RunPackageScriptOptions, ExecutionResult } from '../types.js';

const SCRIPT_NAME_REGEX = /^[a-zA-Z0-9_:.-]+$/;
const SHELL_METACHARS = /[&|;><`$\n\r]/;
const MAX_TIMEOUT_MS = 300000;

export async function runPackageScript(options: RunPackageScriptOptions): Promise<ExecutionResult> {
  const pm = options.packageManager ?? 'npm';
  const timeoutMs = Math.min(Math.max(options.timeout ?? 60000, 100), MAX_TIMEOUT_MS);
  const projectPath = options.projectPath ? path.resolve(options.projectPath) : process.cwd();

  // Validate script name
  if (!SCRIPT_NAME_REGEX.test(options.script)) {
    return {
      success: false,
      exitCode: 1,
      stdout: '',
      stderr: `Security rejection: Invalid script name "${options.script}". Script names must only contain alphanumeric characters, hyphens, underscores, dots, or colons.`,
      durationMs: 0,
      timedOut: false,
      error: `Invalid script name "${options.script}"`,
    };
  }

  // Reject shell metacharacters in extra arguments
  if (options.args) {
    for (const arg of options.args) {
      if (SHELL_METACHARS.test(arg)) {
        return {
          success: false,
          exitCode: 1,
          stdout: '',
          stderr: `Security rejection: Command argument contains forbidden shell metacharacters: ${arg}`,
          durationMs: 0,
          timedOut: false,
          error: 'Forbidden shell metacharacters detected in package arguments',
        };
      }
    }
  }

  const packageJsonPath = path.join(projectPath, 'package.json');
  try {
    const pkgContent = await fs.readFile(packageJsonPath, 'utf8');
    const pkg = JSON.parse(pkgContent);

    if (!pkg.scripts || !pkg.scripts[options.script]) {
      const available = pkg.scripts ? Object.keys(pkg.scripts).join(', ') : 'none';
      return {
        success: false,
        exitCode: 1,
        stdout: '',
        stderr: `Script "${options.script}" not found in ${packageJsonPath}.\nAvailable scripts: ${available}`,
        durationMs: 0,
        timedOut: false,
        error: `Script "${options.script}" not found in package.json`,
      };
    }
  } catch (err: unknown) {
    return {
      success: false,
      exitCode: 1,
      stdout: '',
      stderr: `Failed to read package.json in ${projectPath}: ${err instanceof Error ? err.message : String(err)}`,
      durationMs: 0,
      timedOut: false,
      error: `Could not load package.json from ${projectPath}`,
    };
  }

  const isWindows = process.platform === 'win32';
  const command = isWindows ? `${pm}.cmd` : pm;
  const args = ['run', options.script];

  if (options.args && options.args.length > 0) {
    args.push('--', ...options.args);
  }

  return await runProcess(command, args, {
    cwd: projectPath,
    env: process.env,
    timeoutMs,
    shell: isWindows,
  });
}

