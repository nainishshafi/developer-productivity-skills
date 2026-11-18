import { QuerySafetyMode, SafetyAuditResult } from '../types.js';

/**
 * Scans SQL while respecting single-quoted, double-quoted, backtick, and bracketed identifiers.
 * Strips comments only outside literals and optionally masks single-quoted string contents.
 */
function processSqlLexemes(sql: string, options: { stripComments: boolean; maskLiterals: boolean }): string {
  let out = '';
  let i = 0;

  while (i < sql.length) {
    const ch = sql[i];
    const next = i + 1 < sql.length ? sql[i + 1] : '';

    // Single-quoted string literal (handles '' and \')
    if (ch === "'") {
      if (options.maskLiterals) {
        out += "''";
      } else {
        out += ch;
      }
      i++;
      while (i < sql.length) {
        const c = sql[i];
        const n = i + 1 < sql.length ? sql[i + 1] : '';
        if (!options.maskLiterals) out += c;
        if (c === '\\' && i + 1 < sql.length) {
          if (!options.maskLiterals) out += n;
          i += 2;
          continue;
        }
        if (c === "'" && n === "'") {
          if (!options.maskLiterals) out += n;
          i += 2;
          continue;
        }
        i++;
        if (c === "'") break;
      }
      continue;
    }

    // Double-quoted or backtick identifier
    if (ch === '"' || ch === '`') {
      const quote = ch;
      out += ch;
      i++;
      while (i < sql.length) {
        const c = sql[i];
        const n = i + 1 < sql.length ? sql[i + 1] : '';
        out += c;
        if (c === quote && n === quote) {
          out += n;
          i += 2;
          continue;
        }
        i++;
        if (c === quote) break;
      }
      continue;
    }

    // Bracketed identifier [...]
    if (ch === '[') {
      out += ch;
      i++;
      while (i < sql.length) {
        out += sql[i];
        if (sql[i] === ']') {
          i++;
          break;
        }
        i++;
      }
      continue;
    }

    // Comments outside literals
    if (options.stripComments) {
      if (ch === '/' && next === '*') {
        const end = sql.indexOf('*/', i + 2);
        out += ' ';
        i = end === -1 ? sql.length : end + 2;
        continue;
      }
      if ((ch === '-' && next === '-') || ch === '#') {
        const nl = sql.indexOf('\n', i);
        out += ' ';
        i = nl === -1 ? sql.length : nl + 1;
        continue;
      }
    }

    out += ch;
    i++;
  }

  return out;
}

/**
 * Normalizes SQL by removing comments outside string literals and collapsing whitespace.
 */
export function normalizeSql(sql: string): string {
  return processSqlLexemes(sql, { stripComments: true, maskLiterals: false })
    .replace(/\s+/g, ' ')
    .trim();
}

/**
 * Splits query string into individual statements safely handling quotes, doubled escapes, and comments.
 */
export function splitSqlStatements(sql: string): string[] {
  const clean = normalizeSql(sql);
  const statements: string[] = [];
  let current = '';
  let quote: string | null = null;
  let inBracket = false;

  for (let i = 0; i < clean.length; i++) {
    const ch = clean[i];
    const next = i + 1 < clean.length ? clean[i + 1] : '';

    if (quote) {
      current += ch;
      if (ch === '\\' && quote === "'" && i + 1 < clean.length) {
        current += next;
        i++;
      } else if (ch === quote && next === quote) {
        current += next;
        i++;
      } else if (ch === quote) {
        quote = null;
      }
      continue;
    }

    if (inBracket) {
      current += ch;
      if (ch === ']') inBracket = false;
      continue;
    }

    if (ch === "'" || ch === '"' || ch === '`') {
      quote = ch;
      current += ch;
    } else if (ch === '[') {
      inBracket = true;
      current += ch;
    } else if (ch === ';') {
      const stmt = current.trim();
      if (stmt.length > 0) statements.push(stmt);
      current = '';
    } else {
      current += ch;
    }
  }

  const remainder = current.trim();
  if (remainder.length > 0) statements.push(remainder);
  return statements;
}

const TAUTOLOGY_PATTERNS = [
  /\bWHERE\s+\(?\s*(\d+)\s*=\s*\1\s*\)?\b/i,
  /\bWHERE\s+\(?\s*['"]?([a-zA-Z0-9_-]+)['"]?\s*=\s*['"]?\1['"]?\s*\)?\b/i,
  /\bWHERE\s+\(?\s*true\s*\)?\b/i,
  /\bWHERE\s+\(?\s*1\s*\)?\b/i,
  /\bWHERE\s+null\s+is\s+null\b/i,
  /\bWHERE\s+current_date\s*=\s*current_date\b/i,
  /\bWHERE\s+not\s+(false|0)\b/i,
  /\bWHERE\s+0\s*<>\s*1\b/i,
  /\bWHERE\s+1\s*<=\s*1\b/i,
  /\bOR\s+\(?\s*(\d+)\s*=\s*\1\s*\)?\b/i,
  /\bOR\s+\(?\s*true\s*\)?\b/i,
];

const FORBIDDEN_DDL_PATTERNS = [
  { pattern: /\bDROP\s+(TABLE|DATABASE|SCHEMA|VIEW|INDEX|PROCEDURE|FUNCTION|TRIGGER|SEQUENCE|TABLESPACE|TYPE|ROLE|USER)\b/i, name: 'DROP_STATEMENT' },
  { pattern: /\bTRUNCATE(\s+TABLE)?\b/i, name: 'TRUNCATE_STATEMENT' },
  { pattern: /\bALTER\s+TABLE\s+.*\bDROP\s+(COLUMN|CONSTRAINT|PARTITION|INDEX|PRIMARY\s+KEY)\b/i, name: 'ALTER_TABLE_DROP' },
  { pattern: /\bCREATE\s+(FUNCTION|TRIGGER|PROCEDURE|ROLE|USER)\b/i, name: 'CREATE_PRIVILEGED_OBJECT' },
  { pattern: /\b(GRANT|REVOKE)\b/i, name: 'PRIVILEGE_MODIFICATION' },
  { pattern: /\b(ATTACH\s+DATABASE|LOAD_EXTENSION)\b/i, name: 'SQLITE_EXTENSION_OR_ATTACH' },
  { pattern: /\bCOPY\b[\s\S]*\b(TO|FROM)\s+PROGRAM\b/i, name: 'POSTGRES_COPY_PROGRAM' },
  { pattern: /\b(INTO\s+(OUTFILE|DUMPFILE)|LOAD\s+DATA\s+(LOCAL\s+)?INFILE)\b/i, name: 'MYSQL_FILE_IO' },
  { pattern: /\b(OPENROWSET|BULK\s+INSERT)\b/i, name: 'SQLSERVER_EXTERNAL_IO' },
  { pattern: /\bEXEC(\s+sp_configure|\s+xp_cmdshell|\s+sp_executesql|\s*\()/i, name: 'DANGEROUS_SYSTEM_PROCEDURE' },
  { pattern: /\b(SHUTDOWN|KILL)\b/i, name: 'SERVER_ADMIN_COMMAND' },
];

const READ_ONLY_PRAGMAS = new Set([
  'table_info',
  'database_list',
  'foreign_key_list',
  'index_list',
  'index_info',
  'table_xinfo',
]);

/**
 * Checks if a single statement contains destructive operations or safety violations
 */
export function auditSqlStatement(
  statement: string,
  mode: QuerySafetyMode = 'read-only'
): { allowed: boolean; violations: string[]; detectedOperation: string; isReadOnly: boolean } {
  const clean = normalizeSql(statement);
  const masked = processSqlLexemes(clean, { stripComments: false, maskLiterals: true });
  const violations: string[] = [];

  const firstWordMatch = masked.match(/^([a-zA-Z]+)/i);
  const firstWord = firstWordMatch ? firstWordMatch[1].toUpperCase() : '';

  for (const rule of FORBIDDEN_DDL_PATTERNS) {
    if (rule.pattern.test(masked)) {
      violations.push(`CRITICAL: Destructive operation '${rule.name}' is strictly blocked by SQL Connector firewall.`);
    }
  }

  if (/\bDROP\s+TABLE\b/i.test(masked)) {
    violations.push(`CRITICAL: 'DROP TABLE' execution is strictly blocked by SQL Connector guardrails.`);
  }

  // Unbounded DELETE or DELETE * (checked on masked SQL so string literals cannot fake WHERE)
  if (/\bDELETE\s+(\*|\w+)?\s*(FROM\s+)?/i.test(masked)) {
    if (!/\bWHERE\b/i.test(masked)) {
      violations.push(`CRITICAL: Unbounded 'DELETE' without WHERE clause (or 'DELETE *') is strictly blocked.`);
    } else {
      for (const tautology of TAUTOLOGY_PATTERNS) {
        if (tautology.test(clean)) {
          violations.push(`CRITICAL: 'DELETE' with tautological WHERE condition (${clean.slice(0, 40)}...) is strictly blocked.`);
          break;
        }
      }
    }
  }

  // Unbounded UPDATE (standalone or inside CTEs, including [bracketed] identifiers)
  if (/\bUPDATE\s+([a-zA-Z0-9_."`[\]]+)\s+SET\b/i.test(masked) || /^UPDATE\b/i.test(masked)) {
    if (!/\bWHERE\b/i.test(masked)) {
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

  // Enforce PRAGMA allowlist across all modes so PRAGMA writable_schema = ON is always blocked
  if (firstWord === 'PRAGMA') {
    const pragmaMatch = masked.match(/^PRAGMA\s+([a-zA-Z0-9_]+)/i);
    const pragmaName = pragmaMatch ? pragmaMatch[1].toLowerCase() : '';
    if (!READ_ONLY_PRAGMAS.has(pragmaName)) {
      violations.push(`POLICY: PRAGMA '${pragmaName}' is restricted. Only schema inspection PRAGMAs are allowed.`);
    }
  }

  let isReadOnly = ['SELECT', 'WITH', 'EXPLAIN', 'SHOW', 'DESCRIBE', 'DESC', 'PRAGMA'].includes(firstWord);

  if (firstWord === 'SELECT' && /\bSELECT\b[\s\S]*\bINTO\b/i.test(masked)) {
    isReadOnly = false;
    if (mode === 'read-only') {
      violations.push(`POLICY: 'SELECT ... INTO' creates a table and is not permitted in 'read-only' mode.`);
    }
  }

  if (firstWord === 'WITH') {
    if (/\b(INSERT\s+INTO|UPDATE\s+|DELETE\s+FROM|DELETE\s+|MERGE\s+INTO|DROP\s+|TRUNCATE\s+|ALTER\s+TABLE|CREATE\s+|REPLACE\s+|EXEC\s+|CALL\s+)\b/i.test(masked)) {
      isReadOnly = false;
      if (mode === 'read-only') {
        violations.push(`POLICY: Mutation operation detected inside CTE ('WITH ... DELETE/UPDATE/INSERT') is not permitted in 'read-only' mode. Set mode to 'guarded-write' to execute verified writes.`);
      }
    }
  }

  if (mode === 'read-only' && !isReadOnly && firstWord !== 'WITH' && firstWord !== 'SELECT') {
    violations.push(`POLICY: Mutation operation '${firstWord}' is not permitted in 'read-only' mode. Set mode to 'guarded-write' to execute verified writes.`);
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

/**
 * Audits a query for EXPLAIN, rejecting multi-statement payloads.
 */
export function auditExplainQuery(query: string): SafetyAuditResult {
  const audit = auditSqlQuery(query, 'read-only');
  if (audit.allowed && splitSqlStatements(audit.normalizedQuery).length !== 1) {
    return {
      ...audit,
      allowed: false,
      violations: ['CRITICAL: EXPLAIN only permits a single SQL statement.'],
      riskLevel: 'CRITICAL_BLOCKED',
    };
  }
  return audit;
}
