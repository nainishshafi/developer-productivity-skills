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

export class SqlServerAdapter implements DatabaseAdapter {
  readonly engine = 'sqlserver' as const;
  private connection: any = null;
  private connected = false;

  constructor(private config: DatabaseConnectionConfig) {}

  isConnected(): boolean {
    return this.connected && this.connection !== null;
  }

  async connect(): Promise<void> {
    if (this.connected) return;

    try {
      // Tedious is the standard pure-JS TDS driver for SQL Server
      const { Connection } = await import('tedious' as any);
      const host = this.config.host || 'localhost';
      const port = this.config.port || 1433;

      const tediousConfig = {
        server: host,
        authentication: {
          type: 'default',
          options: {
            userName: this.config.user,
            password: this.config.password,
          },
        },
        options: {
          port,
          database: this.config.database,
          trustServerCertificate: true,
          encrypt: this.config.ssl !== false,
          rowCollectionOnRequestCompletion: true,
        },
      };

      await new Promise<void>((resolve, reject) => {
        const conn = new Connection(tediousConfig);
        conn.on('connect', (err: any) => {
          if (err) reject(err);
          else {
            this.connection = conn;
            this.connected = true;
            resolve();
          }
        });
        conn.connect();
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      if (msg.includes("Cannot find package 'tedious'") || msg.includes("Cannot find module 'tedious'")) {
        throw new Error(
          `SQL Server driver ('tedious') is not installed. To execute live queries against Microsoft SQL Server, install the driver:\n  npm install tedious\nConnection config validated successfully.`
        );
      }
      throw err;
    }
  }

  async disconnect(): Promise<void> {
    if (this.connection) {
      this.connection.close();
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
      const { Request } = await import('tedious' as any);

      const queryPromise = new Promise<QueryResult>((resolve) => {
        const rows: Record<string, unknown>[] = [];
        let rowCount = 0;

        const request = new Request(audit.normalizedQuery, (err: any, rowCountResult: number) => {
          const executionTimeMs = Math.round(performance.now() - startTime);
          if (err) {
            resolve({
              success: false,
              engine: this.engine,
              mode,
              executionTimeMs,
              error: err.message,
            });
            return;
          }

          if (audit.isReadOnly) {
            const truncated = rows.length > maxRows;
            const finalRows = truncated ? rows.slice(0, maxRows) : rows;
            const columns = finalRows.length > 0 ? Object.keys(finalRows[0]) : [];

            resolve({
              success: true,
              engine: this.engine,
              mode,
              rows: finalRows,
              rowCount: finalRows.length,
              columns,
              executionTimeMs,
              truncated,
            });
          } else {
            resolve({
              success: true,
              engine: this.engine,
              mode,
              affectedRows: rowCountResult,
              executionTimeMs,
            });
          }
        });

        request.on('row', (columns: any[]) => {
          if (audit.isReadOnly && rows.length <= maxRows) {
            const row: Record<string, unknown> = {};
            for (const col of columns) {
              row[col.metadata.colName] = col.value;
            }
            rows.push(row);
          }
          rowCount++;
        });

        this.connection.execSql(request);
      });

      return await withTimeout(queryPromise, timeoutMs, 'SQL Server query');
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
      query: `
        SELECT TABLE_NAME as name, TABLE_TYPE as type, TABLE_SCHEMA as [schema]
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_TYPE IN ('BASE TABLE', 'VIEW')
        ORDER BY TABLE_NAME ASC;
      `,
      mode: 'read-only',
    });

    if (!res.success || !res.rows) {
      throw new Error(`Failed to list SQL Server tables: ${res.error}`);
    }

    return res.rows.map((r: any) => ({
      name: String(r.name),
      schema: String(r.schema),
      type: r.type === 'VIEW' ? 'VIEW' : 'TABLE',
    }));
  }

  async describeTable(tableName: string): Promise<TableColumnMetadata[]> {
    const cleanTable = tableName.replace(/[^a-zA-Z0-9_]/g, '');
    const res = await this.query({
      query: `
        SELECT COLUMN_NAME as name, DATA_TYPE as type, IS_NULLABLE as is_nullable
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = '${cleanTable}'
        ORDER BY ORDINAL_POSITION ASC;
      `,
      mode: 'read-only',
    });

    if (!res.success || !res.rows) {
      throw new Error(`Failed to describe SQL Server table: ${res.error}`);
    }

    return res.rows.map((r: any) => ({
      name: String(r.name),
      type: String(r.type),
      nullable: r.is_nullable === 'YES',
    }));
  }

  async explain(query: string, options?: QueryOptions): Promise<ExplainResult> {
    const audit = auditSqlQuery(query, 'read-only');
    if (!audit.allowed) {
      throw new Error(`Explain blocked by SQL guardrails: ${audit.violations.join('; ')}`);
    }

    // SQL Server uses SET SHOWPLAN_XML ON or SET SHOWPLAN_ALL ON
    const explainQuery = `
      SET SHOWPLAN_ALL ON;
      ${audit.normalizedQuery};
      SET SHOWPLAN_ALL OFF;
    `;
    const res = await this.query({ query: explainQuery, mode: 'read-only' });
    return {
      engine: this.engine,
      plan: res.rows || [],
      rawText: JSON.stringify(res.rows || [], null, 2),
    };
  }
}
