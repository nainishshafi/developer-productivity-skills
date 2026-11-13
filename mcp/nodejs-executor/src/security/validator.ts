import type { SandboxMode } from '../types.js';

const DESTRUCTIVE_PATTERNS = [
  /fs(\.promises)?\.(rm|rmdir|unlink)(Sync)?\s*\(\s*['"](\/|[A-Za-z]:(\\{1,2}|\/)?|~|%USERPROFILE%)/i,
  /format\s+[A-Za-z]:/i,
  /diskpart/i,
  /del\s+\/[sfq]\s+['"]?([A-Za-z]:\\|\/)/i,
  /rm\s+-rf\s+['"]?(\/|~|[A-Za-z]:\\|\/\*)/i,
];

/**
 * Pre-execution static analysis check for destructive filesystem operations
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

