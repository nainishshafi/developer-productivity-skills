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
import { withTimeout } from '../utils.js';

export class OracleAdapter implements DatabaseAdapter {
  readonly engine = 'oracle' as const;
  private connection: any = null;
  private connected = false;

  constructor(private config: DatabaseConnectionConfig) {}

  isConnected(): boolean {
    return this.connected && this.connection !== null;
  }

  async connect(): Promise<void> {
    if (this.connected) return;

    try {
      // oracledb supports pure-JS thin mode (no Instant Client needed)
      const oracledb = await import('oracledb' as any);
      const host = this.config.host || 'localhost';
      const port = this.config.port || 1521;
      const serviceName = this.config.database || 'XE';

      const connectString = this.config.connectionString || `${host}:${port}/${serviceName}`;

      this.connection = await oracledb.getConnection({
        user: this.config.user,
        password: this.config.password,
        connectString,
      });
      this.connected = true;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      if (msg.includes("Cannot find package 'oracledb'") || msg.includes("Cannot find module 'oracledb'")) {
        throw new Error(
          `Oracle driver ('oracledb') is not installed. To execute live queries against Oracle, install the driver:\n  npm install oracledb\nConnection config validated successfully.`
        );
      }
      throw err;
    }
  }

  async disconnect(): Promise<void> {
    if (this.connection) {
      await this.connection.close();
      this.connection = null;
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

    if (!this.connected) await this.connect();

    const startTime = performance.now();
    const maxRows = options.maxRows || 500;
    const timeoutMs = options.timeoutMs || 15000;

    try {
      const oracledb = await import('oracledb' as any);
      const res = await withTimeout<any>(
        this.connection.execute(audit.normalizedQuery, options.parameters || [], {
          outFormat: oracledb.OUT_FORMAT_OBJECT,
          maxRows,
        }),
        timeoutMs,
        'Oracle query'
      );

      const executionTimeMs = Math.round(performance.now() - startTime);

      if (audit.isReadOnly) {
        const rows = (res.rows || []) as Record<string, unknown>[];
        const columns = res.metaData ? res.metaData.map((m: any) => m.name) : rows.length > 0 ? Object.keys(rows[0]) : [];

        return {
          success: true,
          engine: this.engine,
          mode,
          rows,
          rowCount: rows.length,
          columns,
          executionTimeMs,
          truncated: rows.length >= maxRows,
        };
      } else {
        return {
          success: true,
          engine: this.engine,
          mode,
          affectedRows: res.rowsAffected ?? 0,
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
    const res = await this.query({
      query: `SELECT table_name AS name, 'TABLE' AS type FROM user_tables ORDER BY table_name ASC`,
      mode: 'read-only',
    });

    if (!res.success || !res.rows) {
      throw new Error(`Failed to list Oracle tables: ${res.error}`);
    }

    return res.rows.map((r: any) => ({
      name: String(r.NAME || r.name),
      type: 'TABLE',
    }));
  }

  async describeTable(tableName: string): Promise<TableColumnMetadata[]> {
    const cleanTable = tableName.replace(/[^a-zA-Z0-9_]/g, '').toUpperCase();
    const res = await this.query({
      query: `
        SELECT column_name AS name, data_type AS type, nullable AS is_nullable
        FROM user_tab_columns
        WHERE table_name = '${cleanTable}'
        ORDER BY column_id ASC
      `,
      mode: 'read-only',
    });

    if (!res.success || !res.rows) {
      throw new Error(`Failed to describe Oracle table: ${res.error}`);
    }

    return res.rows.map((r: any) => ({
      name: String(r.NAME || r.name),
      type: String(r.TYPE || r.type),
      nullable: (r.IS_NULLABLE || r.is_nullable) === 'Y',
    }));
  }

  async explain(query: string, options?: QueryOptions): Promise<ExplainResult> {
    const audit = auditSqlQuery(query, 'read-only');
    if (!audit.allowed) {
      throw new Error(`Explain blocked by SQL guardrails: ${audit.violations.join('; ')}`);
    }

    const explainSql = `EXPLAIN PLAN FOR ${audit.normalizedQuery}`;
    await this.query({ query: explainSql, mode: 'read-only' });
    const planRes = await this.query({
      query: `SELECT PLAN_TABLE_OUTPUT FROM TABLE(DBMS_XPLAN.DISPLAY())`,
      mode: 'read-only',
    });

    return {
      engine: this.engine,
      plan: planRes.rows || [],
      rawText: JSON.stringify(planRes.rows || [], null, 2),
    };
  }
}
