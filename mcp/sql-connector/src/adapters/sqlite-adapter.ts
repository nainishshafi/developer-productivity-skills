import { DatabaseSync } from 'node:sqlite';
import { DatabaseAdapter } from './adapter-interface.js';
import {
  DatabaseConnectionConfig,
  ExplainResult,
  QueryOptions,
  QueryResult,
  TableColumnMetadata,
  TableMetadata,
} from '../types.js';
import { auditSqlQuery } from '../guardrails/sql-guardrail.js';

export class SqliteAdapter implements DatabaseAdapter {
  readonly engine = 'sqlite' as const;
  private db: DatabaseSync | null = null;
  private connected = false;

  constructor(private config: DatabaseConnectionConfig) {}

  isConnected(): boolean {
    return this.connected && this.db !== null;
  }

  async connect(): Promise<void> {
    if (this.db) {
      return;
    }
    const path = this.config.filePath || ':memory:';
    this.db = new DatabaseSync(path);
    this.connected = true;
  }

  async disconnect(): Promise<void> {
    if (this.db) {
      this.db.close();
      this.db = null;
      this.connected = false;
    }
  }

  async query(options: QueryOptions): Promise<QueryResult> {
    if (!this.db) {
      await this.connect();
    }

    const mode = options.mode || 'read-only';
    const audit = auditSqlQuery(options.query, mode);

    if (!audit.allowed) {
      return {
        success: false,
        engine: this.engine,
        mode,
        executionTimeMs: 0,
        error: `SQL Firewall blocked execution:\n- ${audit.violations.join('\n- ')}`,
      };
    }

    const startTime = performance.now();
    const maxRows = options.maxRows || 500;

    try {
      const stmt = this.db!.prepare(audit.normalizedQuery);
      const params = Array.isArray(options.parameters)
        ? options.parameters
        : [];

      if (audit.isReadOnly) {
        const rawRows = stmt.all(...(params as any[])) as Record<string, unknown>[];
        const executionTimeMs = Math.round(performance.now() - startTime);

        const truncated = rawRows.length > maxRows;
        const rows = truncated ? rawRows.slice(0, maxRows) : rawRows;
        const columns = rows.length > 0 ? Object.keys(rows[0]) : [];

        return {
          success: true,
          engine: this.engine,
          mode,
          rows,
          rowCount: rows.length,
          columns,
          executionTimeMs,
          truncated,
        };
      } else {
        const result = stmt.run(...(params as any[]));
        const executionTimeMs = Math.round(performance.now() - startTime);

        return {
          success: true,
          engine: this.engine,
          mode,
          affectedRows: typeof result === 'object' && result && 'changes' in result ? Number(result.changes) : 1,
          executionTimeMs,
        };
      }
    } catch (err: unknown) {
      const executionTimeMs = Math.round(performance.now() - startTime);
      return {
        success: false,
        engine: this.engine,
        mode,
        executionTimeMs,
        error: err instanceof Error ? err.message : String(err),
      };
    }
  }

  async listTables(): Promise<TableMetadata[]> {
    if (!this.db) await this.connect();

    const stmt = this.db!.prepare(`
      SELECT name, type 
      FROM sqlite_master 
      WHERE type IN ('table', 'view') AND name NOT LIKE 'sqlite_%'
      ORDER BY name ASC;
    `);

    const rows = stmt.all() as Array<{ name: string; type: string }>;
    return rows.map((r) => ({
      name: r.name,
      type: r.type.toUpperCase() === 'VIEW' ? 'VIEW' : 'TABLE',
    }));
  }

  async describeTable(tableName: string): Promise<TableColumnMetadata[]> {
    if (!this.db) await this.connect();

    // Sanitize table name against injection
    const cleanTableName = tableName.replace(/[^a-zA-Z0-9_]/g, '');
    const stmt = this.db!.prepare(`PRAGMA table_info("${cleanTableName}");`);
    const rows = stmt.all() as Array<{
      cid: number;
      name: string;
      type: string;
      notnull: number;
      dflt_value: string | null;
      pk: number;
    }>;

    return rows.map((col) => ({
      name: col.name,
      type: col.type || 'TEXT',
      nullable: col.notnull === 0,
      isPrimaryKey: col.pk > 0,
      defaultValue: col.dflt_value,
    }));
  }

  async explain(query: string, options?: QueryOptions): Promise<ExplainResult> {
    if (!this.db) await this.connect();

    const audit = auditSqlQuery(query, 'read-only');
    if (!audit.allowed) {
      throw new Error(`Explain blocked by SQL guardrails: ${audit.violations.join('; ')}`);
    }

    const stmt = this.db!.prepare(`EXPLAIN QUERY PLAN ${audit.normalizedQuery}`);
    const rows = stmt.all();

    return {
      engine: this.engine,
      plan: rows,
      rawText: JSON.stringify(rows, null, 2),
    };
  }
}
