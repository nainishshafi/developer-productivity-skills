import * as fs from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';

/**
 * Utility functions and security helpers for SQL Connector MCP server
 */

/**
 * Wraps an async promise in a deterministic timeout boundary
 */
export function withTimeout<T = any>(
  promise: Promise<T>,
  timeoutMs: number = 15000,
  operationName: string = 'Database query'
): Promise<T> {
  let timer: NodeJS.Timeout;

  const timeoutPromise = new Promise<never>((_, reject) => {
    timer = setTimeout(() => {
      reject(new Error(`${operationName} timed out after ${timeoutMs}ms.`));
    }, timeoutMs);
  });

  return Promise.race([promise, timeoutPromise]).finally(() => {
    clearTimeout(timer);
  });
}

/**
 * Redacts embedded credentials from database driver error messages.
 */
export function redactSecrets(text: string): string {
  return text
    .replace(/([a-zA-Z][a-zA-Z0-9+.-]*:\/\/[^:\s/@"']+:)\S+?(@)/g, '$1[REDACTED]$2')
    .replace(/\b(password|pwd|secret|token)\s*=\s*[^;\s"']+/gi, '$1=[REDACTED]');
}

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

function isPathContained(parent: string, target: string): boolean {
  const realParent = resolveRealOrParent(parent);
  const realTarget = resolveRealOrParent(target);
  const normalize = process.platform === 'win32' ? (p: string) => p.toLowerCase() : (p: string) => p;
  const rel = path.relative(normalize(realParent), normalize(realTarget));
  return !rel.startsWith('..') && !path.isAbsolute(rel);
}

/**
 * Validates file-based database paths (SQLite, MS Access) against path traversal,
 * UNC SMB/NTLM leaks, OLEDB delimiter injection, and disallowed extensions.
 */
export function validateDatabaseFilePath(filePath: string, allowedExts: string[]): string {
  const trimmed = filePath.trim();
  if (trimmed === ':memory:' && allowedExts.includes(':memory:')) {
    return ':memory:';
  }
  if (/^[\\/]{2}/.test(trimmed) || trimmed.includes('\x00') || trimmed.includes('"') || trimmed.includes(';')) {
    throw new Error('Security rejection: Invalid characters or UNC network path in database filePath.');
  }

  const resolved = path.resolve(trimmed);
  if (!isPathContained(process.cwd(), resolved) && !isPathContained(os.tmpdir(), resolved)) {
    throw new Error(
      `Security rejection: Database filePath "${resolved}" must reside within workspace (${process.cwd()}) or temp directory.`
    );
  }

  const ext = path.extname(resolved).toLowerCase();
  const validExts = allowedExts.filter((e) => e !== ':memory:');
  if (validExts.length > 0 && !validExts.includes(ext)) {
    throw new Error(
      `Security rejection: Unsupported database file extension "${ext}". Allowed: ${validExts.join(', ')}`
    );
  }

  return resolved;
}
