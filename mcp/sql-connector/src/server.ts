import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { z } from 'zod';
import { executeQuery } from './tools/execute-query.js';
import { listTables } from './tools/list-tables.js';
import { describeTable } from './tools/describe-table.js';
import { explainQuery } from './tools/explain-query.js';
import { testConnection } from './tools/test-connection.js';
import { auditQuerySafety } from './tools/audit-query-safety.js';
import { DatabaseConnectionConfig } from './types.js';

async function handleToolExecution<T>(
  action: () => Promise<T> | T
): Promise<{ content: Array<{ type: 'text'; text: string }>; isError?: boolean }> {
  try {
    const result = await action();
    const hasSuccess = typeof result === 'object' && result !== null && 'success' in result;
    return {
      content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      ...(hasSuccess ? { isError: !(result as { success: boolean }).success } : {}),
    };
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : String(err);
    return {
      content: [{ type: 'text', text: JSON.stringify({ success: false, error: errorMsg }, null, 2) }],
      isError: true,
    };
  }
}

const connectionSchema = z.object({
  engine: z
    .enum(['sqlserver', 'oracle', 'postgres', 'sqlite', 'mongodb', 'msaccess', 'mysql'])
    .describe('Database dialect/engine: sqlserver, oracle, postgres, sqlite, mongodb, msaccess, mysql'),
  connectionString: z.string().optional().describe('Standard database URI connection string'),
  host: z.string().optional().describe('Database host hostname or IP address'),
  port: z.number().int().optional().describe('Port number (e.g. 5432, 1433, 1521, 27017, 3306)'),
  database: z.string().optional().describe('Database name, catalog, or Oracle service name'),
  user: z.string().optional().describe('Authentication username'),
  password: z.string().optional().describe('Authentication password'),
  filePath: z.string().optional().describe('File path for file-based databases: SQLite (.db) or MS Access (.accdb, .mdb)'),
  ssl: z.boolean().optional().describe('Enable SSL/TLS encryption for database transport'),
});

export function createServer(): McpServer {
  const server = new McpServer({
    name: 'sql-connector',
    version: '1.0.0',
  });

  // Tool 1: execute_query
  server.tool(
    'execute_query',
    'Execute a SQL or MongoDB query with strict safety guardrails preventing DROP TABLE, unbounded DELETE/UPDATE, and destructive DDL. Defaults to read-only mode.',
    {
      connection: connectionSchema,
      query: z.string().describe('The SQL query or MongoDB JSON command to execute'),
      parameters: z.array(z.any()).optional().describe('Positional parameter values for parameterized query execution'),
      mode: z
        .enum(['read-only', 'guarded-write'])
        .default('read-only')
        .describe("Safety mode: 'read-only' (SELECT/find only) or 'guarded-write' (bounded INSERT/UPDATE/DELETE). DROP TABLE and DELETE * are blocked in all modes."),
      maxRows: z.number().int().min(1).max(5000).default(500).optional().describe('Maximum number of rows to return before truncating (default: 500)'),
      timeoutMs: z.number().int().min(100).max(60000).default(15000).optional().describe('Execution timeout in milliseconds (default: 15000)'),
    },
    (params) =>
      handleToolExecution(() =>
        executeQuery({
          connection: params.connection as DatabaseConnectionConfig,
          query: params.query,
          parameters: params.parameters,
          mode: params.mode,
          maxRows: params.maxRows,
          timeoutMs: params.timeoutMs,
        })
      )
  );

  // Tool 2: list_tables
  server.tool(
    'list_tables',
    'List all user tables, views, or MongoDB collections in the target database.',
    {
      connection: connectionSchema,
    },
    (params) =>
      handleToolExecution(() =>
        listTables({
          connection: params.connection as DatabaseConnectionConfig,
        })
      )
  );

  // Tool 3: describe_table
  server.tool(
    'describe_table',
    'Inspect the schema of a specific table, view, or collection (column names, data types, nullability, primary keys).',
    {
      connection: connectionSchema,
      tableName: z.string().describe('Name of the table, view, or collection to inspect'),
    },
    (params) =>
      handleToolExecution(() =>
        describeTable({
          connection: params.connection as DatabaseConnectionConfig,
          tableName: params.tableName,
        })
      )
  );

  // Tool 4: explain_query
  server.tool(
    'explain_query',
    'Inspect the query execution plan (EXPLAIN / SHOWPLAN) without executing mutations or risking data loss.',
    {
      connection: connectionSchema,
      query: z.string().describe('The query whose execution plan should be inspected'),
    },
    (params) =>
      handleToolExecution(() =>
        explainQuery({
          connection: params.connection as DatabaseConnectionConfig,
          query: params.query,
        })
      )
  );

  // Tool 5: test_connection
  server.tool(
    'test_connection',
    'Test database connectivity, latency, authentication, and firewall accessibility.',
    {
      connection: connectionSchema,
    },
    (params) =>
      handleToolExecution(() =>
        testConnection({
          connection: params.connection as DatabaseConnectionConfig,
        })
      )
  );

  // Tool 6: audit_query_safety
  server.tool(
    'audit_query_safety',
    'Dry-run audit of a SQL or MongoDB query string against SQL Connector safety guardrails without executing against a database. Evaluates DROP TABLE, unbounded DELETE/UPDATE, tautologies, comment injections, and risk level.',
    {
      query: z.string().describe('The SQL query or MongoDB JSON string to dry-run analyze'),
      engine: z
        .enum(['sqlserver', 'oracle', 'postgres', 'sqlite', 'mongodb', 'msaccess', 'mysql'])
        .default('postgres')
        .optional()
        .describe('Target database dialect'),
      mode: z
        .enum(['read-only', 'guarded-write'])
        .default('read-only')
        .optional()
        .describe('Intended execution mode'),
    },
    (params) =>
      handleToolExecution(() =>
        auditQuerySafety({
          query: params.query,
          engine: params.engine,
          mode: params.mode,
        })
      )
  );

  return server;
}
