import { QuerySafetyMode, SafetyAuditResult } from '../types.js';

export interface MongoCommandPayload {
  operation?: string;
  collection?: string;
  filter?: Record<string, unknown>;
  update?: Record<string, unknown>;
  pipeline?: Record<string, unknown>[];
  options?: Record<string, unknown>;
}

/**
 * Parses and audits MongoDB JSON or string commands for destructive actions
 */
export function auditMongoQuery(
  rawQuery: string,
  mode: QuerySafetyMode = 'read-only'
): SafetyAuditResult {
  const normalizedQuery = rawQuery.trim();
  const violations: string[] = [];
  let isReadOnly = true;
  let detectedOperation = 'UNKNOWN';

  // 1. Check for shell-style destructive commands
  if (/\b(dropDatabase|dropIndexes|dropCollection)\b/i.test(normalizedQuery) || /\.drop\s*\(/i.test(normalizedQuery)) {
    violations.push("CRITICAL: Destructive operation 'drop' is strictly blocked by MongoDB guardrails.");
  }

  // 2. Check for empty deleteMany or remove
  if (/\b(deleteMany|remove)\s*\(\s*\{\s*\}\s*\)/i.test(normalizedQuery)) {
    violations.push("CRITICAL: Unbounded 'deleteMany({})' without filter is strictly blocked.");
  }

  // 3. Try to parse JSON structured command
  let parsedPayload: MongoCommandPayload | null = null;
  if (normalizedQuery.startsWith('{')) {
    try {
      parsedPayload = JSON.parse(normalizedQuery);
    } catch {
      // not strict JSON, continue with regex checks
    }
  }

  if (parsedPayload) {
    const op = (parsedPayload.operation || '').toLowerCase();
    detectedOperation = op;

    const readOps = ['find', 'findone', 'aggregate', 'countdocuments', 'distinct', 'estimateddocumentcount'];
    isReadOnly = readOps.includes(op);

    // Destructive command checks
    if (['drop', 'dropdatabase', 'dropcollection', 'dropindexes'].includes(op)) {
      violations.push(`CRITICAL: Destructive operation '${op}' is strictly blocked.`);
    }

    // Check deleteMany without filter or empty filter
    if (op === 'deletemany' || op === 'delete') {
      const filter = parsedPayload.filter;
      if (!filter || Object.keys(filter).length === 0) {
        violations.push("CRITICAL: Unbounded 'deleteMany' with empty filter is strictly blocked.");
      }
    }

    // Check updateMany without filter
    if (op === 'updatemany') {
      const filter = parsedPayload.filter;
      if (!filter || Object.keys(filter).length === 0) {
        violations.push("CRITICAL: Unbounded 'updateMany' with empty filter is strictly blocked.");
      }
    }

    if (mode === 'read-only' && !isReadOnly) {
      violations.push(`POLICY: MongoDB mutation '${op}' is not permitted in 'read-only' mode. Set mode to 'guarded-write' to execute verified writes.`);
    }
  } else {
    // Regex checks for shell string
    const matchOp = normalizedQuery.match(/\.(find|findOne|aggregate|count|insertOne|updateOne|updateMany|deleteOne|deleteMany|remove|drop)\b/);
    if (matchOp) {
      detectedOperation = matchOp[1];
      const readOps = ['find', 'findOne', 'aggregate', 'count'];
      isReadOnly = readOps.includes(detectedOperation);

      if (mode === 'read-only' && !isReadOnly) {
        violations.push(`POLICY: MongoDB mutation '${detectedOperation}' is not permitted in 'read-only' mode.`);
      }
    }
  }

  let riskLevel: 'SAFE' | 'LOW' | 'MEDIUM' | 'CRITICAL_BLOCKED' = 'SAFE';
  if (violations.some((v) => v.includes('CRITICAL:'))) {
    riskLevel = 'CRITICAL_BLOCKED';
  } else if (violations.length > 0) {
    riskLevel = 'MEDIUM';
  } else if (!isReadOnly) {
    riskLevel = 'LOW';
  }

  return {
    allowed: violations.length === 0,
    violations,
    detectedOperation,
    isReadOnly,
    riskLevel,
    normalizedQuery,
  };
}
