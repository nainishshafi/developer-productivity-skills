import { QuerySafetyMode, SafetyAuditResult } from '../types.js';

export interface MongoCommandPayload {
  operation?: string;
  collection?: string;
  filter?: Record<string, unknown>;
  update?: Record<string, unknown>;
  pipeline?: Record<string, unknown>[];
  options?: Record<string, unknown>;
}

const UNSAFE_MONGO_OPERATOR_RE = /"(?:\$where|\$function|\$accumulator)"|\$(?:where|function|accumulator)\s*:/i;
const WRITE_PIPELINE_STAGE_RE = /"\$(?:out|merge)"|\$(?:out|merge)\s*:/i;

function hasKeyRecursive(obj: unknown, keys: Set<string>): boolean {
  if (!obj || typeof obj !== 'object') return false;
  if (Array.isArray(obj)) return obj.some((item) => hasKeyRecursive(item, keys));
  for (const [k, v] of Object.entries(obj as Record<string, unknown>)) {
    if (keys.has(k) || hasKeyRecursive(v, keys)) return true;
  }
  return false;
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

  if (/\b(dropDatabase|dropIndexes|dropCollection)\b/i.test(normalizedQuery) || /\.drop\s*\(/i.test(normalizedQuery)) {
    violations.push("CRITICAL: Destructive operation 'drop' is strictly blocked by MongoDB guardrails.");
  }

  if (/\b(deleteMany|remove)\s*\(\s*\{\s*\}\s*\)/i.test(normalizedQuery)) {
    violations.push("CRITICAL: Unbounded 'deleteMany({})' without filter is strictly blocked.");
  }

  if (UNSAFE_MONGO_OPERATOR_RE.test(normalizedQuery)) {
    violations.push('CRITICAL: Server-side JavaScript execution ($where/$function/$accumulator) is strictly blocked.');
  }

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

    if (['drop', 'dropdatabase', 'dropcollection', 'dropindexes'].includes(op)) {
      violations.push(`CRITICAL: Destructive operation '${op}' is strictly blocked.`);
    }

    if (
      hasKeyRecursive(parsedPayload.filter, new Set(['$where', '$function', '$accumulator'])) ||
      hasKeyRecursive(parsedPayload.pipeline, new Set(['$where', '$function', '$accumulator']))
    ) {
      violations.push('CRITICAL: Server-side JavaScript execution ($where/$function/$accumulator) is strictly blocked.');
    }

    if (op === 'aggregate' && hasKeyRecursive(parsedPayload.pipeline, new Set(['$out', '$merge']))) {
      isReadOnly = false;
      violations.push('CRITICAL: Write pipeline stages ($out/$merge) are blocked in aggregate queries.');
    }

    if (op === 'deletemany' || op === 'delete' || op === 'updatemany' || op === 'updateone') {
      const filter = parsedPayload.filter;
      if (!filter || Object.keys(filter).length === 0) {
        violations.push(`CRITICAL: Unbounded '${op}' with empty filter is strictly blocked.`);
      }
    }

    if (mode === 'read-only' && !isReadOnly) {
      violations.push(`POLICY: MongoDB mutation '${op}' is not permitted in 'read-only' mode. Set mode to 'guarded-write' to execute verified writes.`);
    }
  } else {
    if (WRITE_PIPELINE_STAGE_RE.test(normalizedQuery)) {
      isReadOnly = false;
      violations.push('CRITICAL: Write pipeline stages ($out/$merge) are blocked in aggregate queries.');
    }

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
