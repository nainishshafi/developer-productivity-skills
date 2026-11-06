import { spawn, type ChildProcess } from 'node:child_process';

/**
 * Safely terminates a process and process tree across Windows, macOS, and Linux
 */
export function terminateProcess(child: ChildProcess): void {
  if (!child.pid || child.killed) {
    return;
  }

  try {
    child.kill('SIGKILL');
  } catch {}
  try {
    child.kill();
  } catch {}

  if (process.platform === 'win32') {
    try {
      const killer = spawn('taskkill', ['/pid', String(child.pid), '/f', '/t'], {
        windowsHide: true,
        stdio: 'ignore',
      });
      killer.unref();
    } catch {}
  }

  try {
    child.stdout?.destroy();
    child.stderr?.destroy();
  } catch {}
}

