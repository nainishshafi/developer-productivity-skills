import { AdapterFactory } from '../adapters/adapter-factory.js';
import { DatabaseConnectionConfig, TableMetadata } from '../types.js';

export interface ListTablesParams {
  connection: DatabaseConnectionConfig;
}

export async function listTables(params: ListTablesParams): Promise<{
  success: boolean;
  engine: string;
  tables: TableMetadata[];
  error?: string;
}> {
  try {
    const adapter = await AdapterFactory.getAdapter(params.connection);
    const tables = await adapter.listTables();
    return {
      success: true,
      engine: params.connection.engine,
      tables,
    };
  } catch (err: unknown) {
    return {
      success: false,
      engine: params.connection.engine,
      tables: [],
      error: err instanceof Error ? err.message : String(err),
    };
  }
}
