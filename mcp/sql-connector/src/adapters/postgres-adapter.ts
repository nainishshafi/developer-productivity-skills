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

export class PostgresAdapter implements DatabaseAdapter {
  readonly engine = 'postgres' as const;
  private client: any = null;
  private connected = false;

  constructor(private config: DatabaseConnectionConfig) {}

  isConnected(): boolean {
    return this.connected && this.client !== null;
  }

  async connect(): Promise<void> {
    if (this.connected) return;

    try {
      // Dynamically import 'pg' if installed
      const { Client } = await import('pg' as any);
      const connConfig = this.config.connectionString
        ? { connectionString: this.config.connectionString }
        : {
            host: this.config.host || 'localhost',
            port: this.config.port || 5432,
            database: this.config.database,
            user: this.config.user,
            password: this.config.password,
            ssl: this.config.ssl,
          };

      this.client = new Client(connConfig);
      await this.client.connect();
      this.connected = true;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      if (msg.includes("Cannot find package 'pg'") || msg.includes("Cannot find module 'pg'")) {
        throw new Error(
          `PostgreSQL driver ('pg') is not installed. To execute live queries against PostgreSQL, install the driver:\n  npm install pg\nConnection config validated successfully.`
        );
      }
      throw err;
    }
  }

  async disconnect(): Promise<void> {
    if (this.client) {
      await this.client.end();
      this.client = null;
      this.connected = false;
    }
  }

  async query(options: QueryOptions): Promise<QueryResult> {
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

    if (!this.connected) {
      await this.connect();
    }

    const startTime = performance.now();
    const maxRows = options.maxRows || 500;

    try {
      const res = await this.client.query(audit.normalizedQuery, options.parameters || []);
      const executionTimeMs = Math.round(performance.now() - startTime);

      if (audit.isReadOnly) {
        const rawRows = (res.rows || []) as Record<string, unknown>[];
        const truncated = rawRows.length > maxRows;
        const rows = truncated ? rawRows.slice(0, maxRows) : rawRows;
        const columns = res.fields ? res.fields.map((f: any) => f.name) : rows.length > 0 ? Object.keys(rows[0]) : [];

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
        return {
          success: true,
          engine: this.engine,
          mode,
          affectedRows: res.rowCount ?? 0,
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
    if (!this.connected) await this.connect();

    const sql = `
      SELECT table_name as name, table_type as type, table_schema as schema
      FROM information_schema.tables
      WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
      ORDER BY table_name ASC;
    `;
    const res = await this.client.query(sql);
    return res.rows.map((r: any) => ({
      name: r.name,
      schema: r.schema,
      type: r.type === 'VIEW' ? 'VIEW' : 'TABLE',
    }));
  }

  async describeTable(tableName: string): Promise<TableColumnMetadata[]> {
    if (!this.connected) await this.connect();

    const sql = `
      SELECT column_name as name, data_type as type, is_nullable
      FROM information_schema.columns
      WHERE table_name = $1
      ORDER BY ordinal_position ASC;
    `;
    const res = await this.client.query(sql, [tableName]);
    return res.rows.map((r: any) => ({
      name: r.name,
      type: r.type,
      nullable: r.is_nullable === 'YES',
    }));
  }

  async explain(query: string, options?: QueryOptions): Promise<ExplainResult> {
    const audit = auditSqlQuery(query, 'read-only');
    if (!audit.allowed) {
      throw new Error(`Explain blocked by SQL guardrails: ${audit.violations.join('; ')}`);
    }

    if (!this.connected) await this.connect();
    const res = await this.client.query(`EXPLAIN (FORMAT JSON) ${audit.normalizedQuery}`);
    return {
      engine: this.engine,
      plan: res.rows[0],
      rawText: JSON.stringify(res.rows[0], null, 2),
    };
  }
}
