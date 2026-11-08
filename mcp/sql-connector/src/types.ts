/**
 * Core type definitions for SQL Connector MCP server
 */

export type DatabaseEngine =
  | 'sqlserver'
  | 'oracle'
  | 'postgres'
  | 'sqlite'
  | 'mongodb'
  | 'msaccess'
  | 'mysql';

export type QuerySafetyMode = 'read-only' | 'guarded-write';

export interface DatabaseConnectionConfig {
  engine: DatabaseEngine;
  connectionString?: string;
  host?: string;
  port?: number;
  database?: string;
  user?: string;
  password?: string;
  filePath?: string; // For SQLite and MS Access (.accdb, .mdb)
  ssl?: boolean | { rejectUnauthorized?: boolean };
  options?: Record<string, unknown>;
}

export interface QueryOptions {
  query: string;
  engine?: DatabaseEngine;
  parameters?: unknown[] | Record<string, unknown>;
  mode?: QuerySafetyMode;
  maxRows?: number;
  timeoutMs?: number;
}

export interface QueryResult {
  success: boolean;
  engine: DatabaseEngine;
  rows?: Record<string, unknown>[];
  rowCount?: number;
  columns?: string[];
  executionTimeMs: number;
  mode: QuerySafetyMode;
  truncated?: boolean;
  affectedRows?: number;
  error?: string;
}

export interface TableColumnMetadata {
  name: string;
  type: string;
  nullable: boolean;
  isPrimaryKey?: boolean;
  defaultValue?: string | null;
}

export interface TableMetadata {
  name: string;
  schema?: string;
  type: 'TABLE' | 'VIEW' | 'COLLECTION';
  columns?: TableColumnMetadata[];
  rowCountEstimate?: number;
}

export interface SafetyAuditResult {
  allowed: boolean;
  violations: string[];
  detectedOperation?: string;
  isReadOnly: boolean;
  riskLevel: 'SAFE' | 'LOW' | 'MEDIUM' | 'CRITICAL_BLOCKED';
  normalizedQuery: string;
}

export interface ExplainResult {
  engine: DatabaseEngine;
  plan: unknown;
  rawText?: string;
}
