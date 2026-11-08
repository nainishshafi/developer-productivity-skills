import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
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

const execFileAsync = promisify(execFile);

export class AccessAdapter implements DatabaseAdapter {
  readonly engine = 'msaccess' as const;
  private connected = false;

  constructor(private config: DatabaseConnectionConfig) {}

  isConnected(): boolean {
    return this.connected;
  }

  async connect(): Promise<void> {
    if (!this.config.filePath && !this.config.connectionString) {
      throw new Error("MS Access adapter requires either 'filePath' (.accdb / .mdb) or 'connectionString'.");
    }
    this.connected = true;
  }

  async disconnect(): Promise<void> {
    this.connected = false;
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

    const startTime = performance.now();
    const maxRows = options.maxRows || 500;
    const dbPath = this.config.filePath || '';

    // On Windows, use ADODB PowerShell automation bridge if node-adodb or ODBC is not installed
    if (process.platform === 'win32') {
      try {
        const psScript = `
          $connStr = "Provider=Microsoft.ACE.OLEDB.16.0;Data Source='${dbPath}';Persist Security Info=False;"
          try {
            $conn = New-Object -ComObject ADODB.Connection
            $conn.Open($connStr)
          } catch {
            $connStr = "Provider=Microsoft.ACE.OLEDB.12.0;Data Source='${dbPath}';Persist Security Info=False;"
            $conn = New-Object -ComObject ADODB.Connection
            $conn.Open($connStr)
          }
          $rs = New-Object -ComObject ADODB.Recordset
          $rs.Open("${audit.normalizedQuery.replace(/"/g, '`"')}", $conn)
          $results = @()
          $count = 0
          while (-not $rs.EOF -and $count -lt ${maxRows}) {
            $row = @{}
            for ($i = 0; $i -lt $rs.Fields.Count; $i++) {
              $field = $rs.Fields.Item($i)
              $row[$field.Name] = $field.Value
            }
            $results += $row
            $count++
            $rs.MoveNext()
          }
          $rs.Close()
          $conn.Close()
          $results | ConvertTo-Json -Depth 5 -Compress
        `;

        const { stdout, stderr } = await execFileAsync('powershell', ['-NoProfile', '-Command', psScript], {
          timeout: options.timeoutMs || 15000,
        });

        const executionTimeMs = Math.round(performance.now() - startTime);

        if (stderr && stderr.trim().length > 0 && !stdout.trim()) {
          return {
            success: false,
            engine: this.engine,
            mode,
            executionTimeMs,
            error: stderr.trim(),
          };
        }

        const trimmed = stdout.trim();
        let rows: Record<string, unknown>[] = [];
        if (trimmed) {
          try {
            const parsed = JSON.parse(trimmed);
            rows = Array.isArray(parsed) ? parsed : [parsed];
          } catch {
            rows = [];
          }
        }

        const columns = rows.length > 0 ? Object.keys(rows[0]) : [];

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
    } else {
      // Non-windows platforms require ODBC driver (e.g. mdb-tools or unixODBC)
      return {
        success: false,
        engine: this.engine,
        mode,
        executionTimeMs: 0,
        error: 'MS Access (.accdb/.mdb) native driver bridge requires Windows ACE OLEDB Provider or unixODBC on Linux.',
      };
    }
  }

  async listTables(): Promise<TableMetadata[]> {
    const res = await this.query({
      query: `SELECT Name AS name, Type AS type FROM MSysObjects WHERE Type IN (1, 5) AND Flags = 0`,
      mode: 'read-only',
    });

    if (!res.success || !res.rows) {
      throw new Error(`Failed to list Access tables: ${res.error}`);
    }

    return res.rows.map((r: any) => ({
      name: String(r.name || r.Name),
      type: 'TABLE',
    }));
  }

  async describeTable(tableName: string): Promise<TableColumnMetadata[]> {
    // Inspection query
    const res = await this.query({
      query: `SELECT TOP 1 * FROM [${tableName.replace(/[^a-zA-Z0-9_]/g, '')}]`,
      mode: 'read-only',
    });

    if (!res.success || !res.columns) {
      return [];
    }

    return res.columns.map((col) => ({
      name: col,
      type: 'VARIANT',
      nullable: true,
    }));
  }

  async explain(query: string, options?: QueryOptions): Promise<ExplainResult> {
    return {
      engine: this.engine,
      plan: 'MS Access Jet/ACE engine does not support interactive query execution plans.',
      rawText: 'Execution plans unavailable in MS Access.',
    };
  }
}
