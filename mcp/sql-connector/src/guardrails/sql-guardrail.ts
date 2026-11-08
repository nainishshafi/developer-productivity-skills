import { QuerySafetyMode, SafetyAuditResult } from '../types.js';

/**
 * Normalizes SQL by removing single-line and multi-line comments,
 * collapsing whitespace, and trimming trailing semicolons.
 */
export function normalizeSql(sql: string): string {
  // Remove block comments /* ... */
  let clean = sql.replace(/\/\*[\s\S]*?\*\//g, ' ');
  // Remove line comments -- ...
  clean = clean.replace(/--.*$/gm, ' ');
  // Remove # comments (MySQL/SQLite)
  clean = clean.replace(/#.*$/gm, ' ');
  // Collapse whitespace
  clean = clean.replace(/\s+/g, ' ').trim();
  return clean;
}

/**
 * Splits query string into individual statements safely handling quotes
 */
export function splitSqlStatements(sql: string): string[] {
  const statements: string[] = [];
  let current = '';
  let inSingleQuote = false;
  let inDoubleQuote = false;
  let inBacktick = false;

  for (let i = 0; i < sql.length; i++) {
    const char = sql[i];
    const prevChar = i > 0 ? sql[i - 1] : '';

    if (char === "'" && prevChar !== '\\' && !inDoubleQuote && !inBacktick) {
      inSingleQuote = !inSingleQuote;
    } else if (char === '"' && prevChar !== '\\' && !inSingleQuote && !inBacktick) {
      inDoubleQuote = !inDoubleQuote;
    } else if (char === '`' && prevChar !== '\\' && !inSingleQuote && !inDoubleQuote) {
      inBacktick = !inBacktick;
    }

    if (char === ';' && !inSingleQuote && !inDoubleQuote && !inBacktick) {
      const stmt = current.trim();
      if (stmt.length > 0) {
        statements.push(stmt);
      }
      current = '';
    } else {
      current += char;
    }
  }

  const remainder = current.trim();
  if (remainder.length > 0) {
    statements.push(remainder);
  }

  return statements;
}

/**
 * Detects tautological / unconditionally true WHERE clauses designed to wipe or update all rows
 * Examples: 1=1, 0=0, 'a'='a', '1'='1', true, 1, 1 <= 1, NULL IS NULL
 */
const TAUTOLOGY_PATTERNS = [
  /\bWHERE\s+1\s*=\s*1\b/i,
  /\bWHERE\s+0\s*=\s*0\b/i,
  /\bWHERE\s+['"]?([a-zA-Z0-9_-]+)['"]?\s*=\s*['"]?\1['"]?\b/i,
  /\bWHERE\s+true\b/i,
  /\bWHERE\s+1\b/i,
  /\bWHERE\s+null\s+is\s+null\b/i,
  /\bWHERE\s+current_date\s*=\s*current_date\b/i,
  /\bWHERE\s+not\s+false\b/i,
  /\bWHERE\s+not\s+0\b/i,
  /\bWHERE\s+0\s*<>\s*1\b/i,
  /\bWHERE\s+1\s*<=\s*1\b/i,
];

/**
 * Strictly forbidden DDL patterns in all execution modes
 */
const FORBIDDEN_DDL_PATTERNS = [
  { pattern: /\bDROP\s+(TABLE|DATABASE|SCHEMA|VIEW|INDEX|PROCEDURE|FUNCTION|TRIGGER|SEQUENCE|TABLESPACE|TYPE|ROLE|USER)\b/i, name: 'DROP_STATEMENT' },
  { pattern: /\bTRUNCATE(\s+TABLE)?\b/i, name: 'TRUNCATE_STATEMENT' },
  { pattern: /\bALTER\s+TABLE\s+.*\bDROP\s+(COLUMN|CONSTRAINT|PARTITION|INDEX|PRIMARY\s+KEY)\b/i, name: 'ALTER_TABLE_DROP' },
  { pattern: /\bEXEC(\s+sp_configure|\s+xp_cmdshell)\b/i, name: 'DANGEROUS_SYSTEM_PROCEDURE' },
  { pattern: /\b(SHUTDOWN|KILL)\b/i, name: 'SERVER_ADMIN_COMMAND' },
];

/**
 * Checks if a single statement contains destructive operations or safety violations
 */
export function auditSqlStatement(
  statement: string,
  mode: QuerySafetyMode = 'read-only'
): { allowed: boolean; violations: string[]; detectedOperation: string; isReadOnly: boolean } {
  const clean = normalizeSql(statement);
  const violations: string[] = [];

  // 1. Detect root operation keyword
  const firstWordMatch = clean.match(/^([a-zA-Z]+)/i);
  const firstWord = firstWordMatch ? firstWordMatch[1].toUpperCase() : '';

  // 2. Unconditionally check for forbidden DDL / Admin commands across ALL modes
  for (const rule of FORBIDDEN_DDL_PATTERNS) {
    if (rule.pattern.test(clean)) {
      violations.push(`CRITICAL: Destructive operation '${rule.name}' is strictly blocked by SQL Connector firewall.`);
    }
  }

  // 3. Strict Check: DROP TABLE or DELETE *
  if (/\bDROP\s+TABLE\b/i.test(clean)) {
    violations.push(`CRITICAL: 'DROP TABLE' execution is strictly blocked by SQL Connector guardrails.`);
  }

  // 4. Strict Check: Unbounded DELETE or DELETE *
  // Checks: "DELETE * FROM", "DELETE FROM table" (no WHERE), "DELETE table" (no WHERE)
  if (/\bDELETE\s+(\*|\w+)?\s*(FROM\s+)?/i.test(clean)) {
    if (!/\bWHERE\b/i.test(clean)) {
      violations.push(`CRITICAL: Unbounded 'DELETE' without WHERE clause (or 'DELETE *') is strictly blocked.`);
    } else {
      // Check for tautological WHERE clause
      for (const tautology of TAUTOLOGY_PATTERNS) {
        if (tautology.test(clean)) {
          violations.push(`CRITICAL: 'DELETE' with tautological WHERE condition (${clean.slice(0, 40)}...) is strictly blocked.`);
          break;
        }
      }
    }
  }

  // 5. Strict Check: Unbounded UPDATE
  if (/^UPDATE\b/i.test(clean)) {
    if (!/\bWHERE\b/i.test(clean)) {
      violations.push(`CRITICAL: Unbounded 'UPDATE' without WHERE clause is strictly blocked.`);
    } else {
      for (const tautology of TAUTOLOGY_PATTERNS) {
        if (tautology.test(clean)) {
          violations.push(`CRITICAL: 'UPDATE' with tautological WHERE condition is strictly blocked.`);
          break;
        }
      }
    }
  }

  // 6. Check for Read-Only mode violations
  const isReadOnly = ['SELECT', 'WITH', 'EXPLAIN', 'SHOW', 'DESCRIBE', 'DESC', 'PRAGMA'].includes(firstWord);

  if (mode === 'read-only') {
    if (!isReadOnly) {
      violations.push(`POLICY: Mutation operation '${firstWord}' is not permitted in 'read-only' mode. Set mode to 'guarded-write' to execute verified writes.`);
    }

    // SQLite PRAGMA guardrail: only allow read-only pragmas
    if (firstWord === 'PRAGMA') {
      const pragmaMatch = clean.match(/^PRAGMA\s+([a-zA-Z0-9_]+)/i);
      const pragmaName = pragmaMatch ? pragmaMatch[1].toLowerCase() : '';
      const allowedPragmas = ['table_info', 'database_list', 'foreign_key_list', 'index_list', 'index_info', 'table_xinfo'];
      if (!allowedPragmas.includes(pragmaName)) {
        violations.push(`POLICY: PRAGMA '${pragmaName}' is restricted. Only schema inspection PRAGMAs are allowed in read-only mode.`);
      }
    }
  }

  return {
    allowed: violations.length === 0,
    violations,
    detectedOperation: firstWord || 'UNKNOWN',
    isReadOnly,
  };
}

/**
 * Audits complete query string (including potential multi-statements)
 */
export function auditSqlQuery(
  query: string,
  mode: QuerySafetyMode = 'read-only'
): SafetyAuditResult {
  const normalizedQuery = normalizeSql(query);
  const statements = splitSqlStatements(query);

  if (statements.length === 0) {
    return {
      allowed: false,
      violations: ['Query is empty or contains only comments/whitespace.'],
      detectedOperation: 'NONE',
      isReadOnly: true,
      riskLevel: 'LOW',
      normalizedQuery,
    };
  }

  const allViolations: string[] = [];
  let detectedOperation = 'UNKNOWN';
  let isReadOnlyOverall = true;

  for (let i = 0; i < statements.length; i++) {
    const stmt = statements[i];
    const audit = auditSqlStatement(stmt, mode);

    if (i === 0) {
      detectedOperation = audit.detectedOperation;
    }

    if (!audit.isReadOnly) {
      isReadOnlyOverall = false;
    }

    for (const v of audit.violations) {
      const prefix = statements.length > 1 ? `[Statement ${i + 1}] ` : '';
      allViolations.push(`${prefix}${v}`);
    }
  }

  let riskLevel: 'SAFE' | 'LOW' | 'MEDIUM' | 'CRITICAL_BLOCKED' = 'SAFE';
  if (allViolations.some((v) => v.includes('CRITICAL:'))) {
    riskLevel = 'CRITICAL_BLOCKED';
  } else if (allViolations.length > 0) {
    riskLevel = 'MEDIUM';
  } else if (!isReadOnlyOverall) {
    riskLevel = 'LOW';
  }

  return {
    allowed: allViolations.length === 0,
    violations: allViolations,
    detectedOperation,
    isReadOnly: isReadOnlyOverall,
    riskLevel,
    normalizedQuery,
  };
}
