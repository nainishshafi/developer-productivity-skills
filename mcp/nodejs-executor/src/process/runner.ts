import { spawn, type ChildProcess } from 'node:child_process';
import { terminateProcess } from './terminator.js';
import type { ExecutionResult } from '../types.js';

const MAX_OUTPUT_SIZE = 512 * 1024; // 512 KB limit per stream

export interface ProcessRunOptions {
  cwd: string;
  env: NodeJS.ProcessEnv;
  timeoutMs: number;
  shell?: boolean;
}

/**
 * Spawns a child process with stream capping, timeout management, and safe teardown
 */
export function runProcess(
  command: string,
  args: string[],
  options: ProcessRunOptions
): Promise<ExecutionResult> {
  return new Promise((resolve) => {
    const startTime = Date.now();
    let stdoutText = '';
    let stderrText = '';
    let stdoutTruncated = false;
    let stderrTruncated = false;
    let timedOut = false;
    let timeoutTimer: NodeJS.Timeout | null = null;
    let settled = false;

    let child: ChildProcess;
    try {
      child = spawn(command, args, {
        cwd: options.cwd,
        env: options.env,
        shell: options.shell ?? false,
        windowsHide: true,
        stdio: ['ignore', 'pipe', 'pipe'],
      });
    } catch (err: unknown) {
      return resolve({
        success: false,
        exitCode: 1,
        stdout: '',
        stderr: err instanceof Error ? err.message : String(err),
        durationMs: Date.now() - startTime,
        timedOut: false,
        error: `Failed to spawn process: ${err instanceof Error ? err.message : String(err)}`,
      });
    }

    const finish = (exitCode: number | null, error?: string) => {
      if (settled) return;
      settled = true;

      if (timeoutTimer) {
        clearTimeout(timeoutTimer);
        timeoutTimer = null;
      }

      try {
        child.stdout?.destroy();
        child.stderr?.destroy();
      } catch {}

      const durationMs = Date.now() - startTime;
      const success = !timedOut && exitCode === 0;

      if (stdoutTruncated) {
        stdoutText += '\n[Output truncated: exceeded 512 KB limit]';
      }
      if (stderrTruncated) {
        stderrText += '\n[Error output truncated: exceeded 512 KB limit]';
      }

      let errorMsg = error;
      if (timedOut) {
        errorMsg = `Execution timed out after ${options.timeoutMs}ms`;
      } else if (!success && !errorMsg) {
        errorMsg = `Process exited with code ${exitCode}`;
      }

      resolve({
        success,
        exitCode,
        stdout: stdoutText,
        stderr: stderrText,
        durationMs,
        timedOut,
        error: errorMsg,
      });
    };

    timeoutTimer = setTimeout(() => {
      timedOut = true;
      terminateProcess(child);
    }, options.timeoutMs);
    timeoutTimer.unref();

    child.stdout?.on('data', (chunk: Buffer) => {
      if (stdoutText.length < MAX_OUTPUT_SIZE) {
        const remaining = MAX_OUTPUT_SIZE - stdoutText.length;
        const text = chunk.toString('utf8');
        if (text.length > remaining) {
          stdoutText += text.slice(0, remaining);
          stdoutTruncated = true;
        } else {
          stdoutText += text;
        }
      } else {
        stdoutTruncated = true;
      }
    });

    child.stderr?.on('data', (chunk: Buffer) => {
      if (stderrText.length < MAX_OUTPUT_SIZE) {
        const remaining = MAX_OUTPUT_SIZE - stderrText.length;
        const text = chunk.toString('utf8');
        if (text.length > remaining) {
          stderrText += text.slice(0, remaining);
          stderrTruncated = true;
        } else {
          stderrText += text;
        }
      } else {
        stderrTruncated = true;
      }
    });

    child.on('error', (err) => {
      finish(1, `Process execution error: ${err.message}`);
    });

    child.on('close', (code) => {
      finish(code);
    });

    child.on('exit', (code) => {
      setTimeout(() => {
        finish(code);
      }, 80).unref();
    });
  });
}

