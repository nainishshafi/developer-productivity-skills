import * as path from 'node:path';
import type { SandboxMode } from '../types.js';
import { isAllowedWorkspaceOrTempPath, isPathContained } from './validator.js';

export function supportsNativeTypeScript(): boolean {
  const major = parseInt(process.versions.node.split('.')[0], 10);
  return major >= 22;
}

export function supportsPermissionModel(): boolean {
  const major = parseInt(process.versions.node.split('.')[0], 10);
  return major >= 20;
}

/**
 * Builds permission model arguments for Node.js child processes.
 * Fails closed on Node.js < 20 where --experimental-permission is unavailable.
 */
export function getPermissionFlags(
  tempDir: string,
  cwd: string,
  sandboxMode: SandboxMode = 'strict',
  allowFsWritePaths?: string[],
  additionalReadPaths?: string[]
): string[] {
  if (!supportsPermissionModel()) {
    throw new Error(
      `Security policy violation: Node.js ${process.versions.node} does not support the permission model (requires v20+).`
    );
  }

  const flags: string[] = ['--experimental-permission', '--no-warnings', '--max-old-space-size=512'];

  const readPaths = new Set<string>([
    tempDir,
    cwd,
    process.cwd(),
    path.dirname(process.execPath),
    ...(additionalReadPaths ?? []),
  ]);
  for (const rp of readPaths) {
    flags.push(`--allow-fs-read=${rp}`);
  }

  const writePaths = new Set<string>([tempDir]);

  if (sandboxMode === 'workspace-write' || sandboxMode === 'unrestricted') {
    if (!isAllowedWorkspaceOrTempPath(cwd)) {
      throw new Error(`Security rejection: workingDirectory "${cwd}" is outside workspace and temp boundaries.`);
    }
    writePaths.add(cwd);
  }

  if (sandboxMode === 'unrestricted') {
    flags.push('--allow-child-process');
  }

  if (allowFsWritePaths) {
    for (const p of allowFsWritePaths) {
      const resolved = path.resolve(cwd, p);
      if (sandboxMode === 'strict' && !isPathContained(tempDir, resolved)) {
        throw new Error(`Security rejection: allowFsWritePaths "${p}" is not permitted in strict mode.`);
      }
      if (!isAllowedWorkspaceOrTempPath(resolved)) {
        throw new Error(`Security rejection: allowFsWritePaths "${p}" escapes workspace and temp boundaries.`);
      }
      writePaths.add(resolved);
    }
  }

  for (const wp of writePaths) {
    flags.push(`--allow-fs-write=${wp}`);
  }

  return flags;
}
