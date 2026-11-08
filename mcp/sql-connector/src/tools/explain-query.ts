import { AdapterFactory } from '../adapters/adapter-factory.js';
import { DatabaseConnectionConfig, ExplainResult } from '../types.js';

export interface ExplainQueryParams {
  connection: DatabaseConnectionConfig;
  query: string;
}

export async function explainQuery(params: ExplainQueryParams): Promise<{
  success: boolean;
  engine: string;
  explainResult?: ExplainResult;
  error?: string;
}> {
  try {
    const adapter = await AdapterFactory.getAdapter(params.connection);
    const explainResult = await adapter.explain(params.query);
    return {
      success: true,
      engine: params.connection.engine,
      explainResult,
    };
  } catch (err: unknown) {
    return {
      success: false,
      engine: params.connection.engine,
      error: err instanceof Error ? err.message : String(err),
    };
  }
}
