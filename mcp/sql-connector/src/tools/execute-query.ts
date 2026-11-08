import { AdapterFactory } from '../adapters/adapter-factory.js';
import { DatabaseConnectionConfig, QueryOptions, QueryResult } from '../types.js';

export interface ExecuteQueryParams {
  connection: DatabaseConnectionConfig;
  query: string;
  parameters?: unknown[] | Record<string, unknown>;
  mode?: 'read-only' | 'guarded-write';
  maxRows?: number;
  timeoutMs?: number;
}

export async function executeQuery(params: ExecuteQueryParams): Promise<QueryResult> {
  const adapter = await AdapterFactory.getAdapter(params.connection);

  const queryOptions: QueryOptions = {
    query: params.query,
    engine: params.connection.engine,
    parameters: params.parameters,
    mode: params.mode || 'read-only',
    maxRows: params.maxRows || 500,
    timeoutMs: params.timeoutMs || 15000,
  };

  return await adapter.query(queryOptions);
}
