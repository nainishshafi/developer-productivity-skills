import { DatabaseEngine, QuerySafetyMode, SafetyAuditResult } from '../types.js';
import { auditSqlQuery } from '../guardrails/sql-guardrail.js';
import { auditMongoQuery } from '../guardrails/mongo-guardrail.js';

export interface AuditQuerySafetyParams {
  query: string;
  engine?: DatabaseEngine;
  mode?: QuerySafetyMode;
}

export function auditQuerySafety(params: AuditQuerySafetyParams): SafetyAuditResult {
  const engine = params.engine || 'postgres';
  const mode = params.mode || 'read-only';

  if (engine === 'mongodb') {
    return auditMongoQuery(params.query, mode);
  } else {
    return auditSqlQuery(params.query, mode);
  }
}
