import * as os from 'node:os';
import * as path from 'node:path';
import type { SandboxMode } from '../types.js';

export function supportsNativeTypeScript(): boolean {
  const major = parseInt(process.versions.node.split('.')[0], 10);
  return major >= 22;
}

export function supportsPermissionModel(): boolean {
  const major = parseInt(process.versions.node.split('.')[0], 10);
  return major >= 20;
}

/**
 * Builds permission model arguments for Node.js child processes
 */
export function getPermissionFlags(
  tempDir: string,
  cwd: string,
  sandboxMode: SandboxMode = 'strict',
  allowFsWritePaths?: string[]
): string[] {
  if (sandboxMode === 'unrestricted' || !supportsPermissionModel()) {
    return [];
  }

  const flags: string[] = ['--experimental-permission', '--no-warnings'];
  flags.push('--allow-fs-read=*');

  const writePaths = new Set<string>();
  writePaths.add(tempDir);
  writePaths.add(os.tmpdir());

  if (sandboxMode === 'workspace-write') {
    writePaths.add(cwd);
  }

  if (allowFsWritePaths) {
    for (const p of allowFsWritePaths) {
      writePaths.add(path.resolve(cwd, p));
    }
  }

  for (const wp of writePaths) {
    flags.push(`--allow-fs-write=${wp}`);
  }

  return flags;
}

