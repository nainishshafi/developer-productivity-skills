import * as fs from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';
import type { SandboxMode } from '../types.js';

const DESTRUCTIVE_PATTERNS = [
  /fs(\.promises)?\.(rm|rmdir|unlink)(Sync)?\s*\(\s*(['"`](\/|[A-Za-z]:(\\{1,2}|\/)?|~|%USERPROFILE%)|path\.resolve\s*\(\s*['"](\/|[A-Za-z]:))/i,
  /format\s+[A-Za-z]:/i,
  /diskpart/i,
  /del\s+\/[sfq]\s+['"]?([A-Za-z]:\\|\/)/i,
  /rm\s+-rf\s+['"]?(\/|~|[A-Za-z]:\\|\/\*)/i,
];

function resolveRealOrParent(targetPath: string): string {
  const resolved = path.resolve(targetPath);
  try {
    return fs.realpathSync.native(resolved);
  } catch {
    const parent = path.dirname(resolved);
    if (parent === resolved) {
      return resolved;
    }
    return path.join(resolveRealOrParent(parent), path.basename(resolved));
  }
}

/**
 * Verifies that target resides inside parent after resolving symlinks and NTFS junctions.
 */
export function isPathContained(parent: string, target: string): boolean {
  const realParent = resolveRealOrParent(parent);
  const realTarget = resolveRealOrParent(target);
  const normalize = process.platform === 'win32' ? (p: string) => p.toLowerCase() : (p: string) => p;
  const rel = path.relative(normalize(realParent), normalize(realTarget));
  return !rel.startsWith('..') && !path.isAbsolute(rel);
}

/**
 * Verifies that targetPath resides within the workspace root or OS temp directory.
 */
export function isAllowedWorkspaceOrTempPath(targetPath: string, workspaceRoot: string = process.cwd()): boolean {
  return isPathContained(workspaceRoot, targetPath) || isPathContained(os.tmpdir(), targetPath);
}

/**
 * Pre-execution static analysis check for destructive filesystem operations.
 */
export function preExecutionSecurityCheck(
  code: string,
  _sandboxMode: SandboxMode = 'strict'
): { allowed: boolean; reason?: string } {
  for (const pattern of DESTRUCTIVE_PATTERNS) {
    if (pattern.test(code)) {
      return {
        allowed: false,
        reason: 'Blocked by pre-execution safety policy: broad destructive root filesystem operation detected.',
      };
    }
  }

  return { allowed: true };
}
