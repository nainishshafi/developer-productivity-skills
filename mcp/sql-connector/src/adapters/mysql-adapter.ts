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

export class MySqlAdapter implements DatabaseAdapter {
  readonly engine = 'mysql' as const;
  private connection: any = null;
  private connected = false;

  constructor(private config: DatabaseConnectionConfig) {}

  isConnected(): boolean {
    return this.connected && this.connection !== null;
  }

  async connect(): Promise<void> {
    if (this.connected) return;

    try {
      const mysql = await import('mysql2/promise' as any);
      const connConfig = this.config.connectionString
        ? { uri: this.config.connectionString }
        : {
            host: this.config.host || 'localhost',
            port: this.config.port || 3306,
            database: this.config.database,
            user: this.config.user,
            password: this.config.password,
          };

      this.connection = await mysql.createConnection(connConfig);
      this.connected = true;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      if (msg.includes("Cannot find package 'mysql2'") || msg.includes("Cannot find module 'mysql2'")) {
        throw new Error(
          `MySQL driver ('mysql2') is not installed. To execute live queries against MySQL, install the driver:\n  npm install mysql2\nConnection config validated successfully.`
        );
      }
      throw err;
    }
  }

  async disconnect(): Promise<void> {
    if (this.connection) {
      await this.connection.end();
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

    try {
      const [results, fields] = await this.connection.execute(audit.normalizedQuery, options.parameters || []);
      const executionTimeMs = Math.round(performance.now() - startTime);

      if (audit.isReadOnly) {
        const rawRows = Array.isArray(results) ? (results as Record<string, unknown>[]) : [];
        const truncated = rawRows.length > maxRows;
        const rows = truncated ? rawRows.slice(0, maxRows) : rawRows;
        const columns = fields ? fields.map((f: any) => f.name) : rows.length > 0 ? Object.keys(rows[0]) : [];

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
          affectedRows: typeof results === 'object' && results && 'affectedRows' in results ? Number((results as any).affectedRows) : 1,
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

    const [rows]: any = await this.connection.query(`
      SELECT TABLE_NAME as name, TABLE_TYPE as type 
      FROM information_schema.tables 
      WHERE table_schema = DATABASE()
      ORDER BY TABLE_NAME ASC;
    `);

    return rows.map((r: any) => ({
      name: r.name,
      type: r.type === 'VIEW' ? 'VIEW' : 'TABLE',
    }));
  }

  async describeTable(tableName: string): Promise<TableColumnMetadata[]> {
    if (!this.connected) await this.connect();

    const cleanTable = tableName.replace(/[^a-zA-Z0-9_]/g, '');
    const [rows]: any = await this.connection.query(`
      SELECT COLUMN_NAME as name, DATA_TYPE as type, IS_NULLABLE as is_nullable
      FROM information_schema.columns 
      WHERE table_schema = DATABASE() AND table_name = '${cleanTable}'
      ORDER BY ORDINAL_POSITION ASC;
    `);

    return rows.map((r: any) => ({
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
    const [rows]: any = await this.connection.query(`EXPLAIN FORMAT=JSON ${audit.normalizedQuery}`);
    return {
      engine: this.engine,
      plan: rows[0],
      rawText: JSON.stringify(rows[0], null, 2),
    };
  }
}
