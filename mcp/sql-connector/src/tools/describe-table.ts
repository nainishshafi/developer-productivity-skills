import { AdapterFactory } from '../adapters/adapter-factory.js';
import { DatabaseConnectionConfig, TableColumnMetadata } from '../types.js';

export interface DescribeTableParams {
  connection: DatabaseConnectionConfig;
  tableName: string;
}

export async function describeTable(params: DescribeTableParams): Promise<{
  success: boolean;
  engine: string;
  tableName: string;
  columns: TableColumnMetadata[];
  error?: string;
}> {
  try {
    const adapter = await AdapterFactory.getAdapter(params.connection);
    const columns = await adapter.describeTable(params.tableName);
    return {
      success: true,
      engine: params.connection.engine,
      tableName: params.tableName,
      columns,
    };
  } catch (err: unknown) {
    return {
      success: false,
      engine: params.connection.engine,
      tableName: params.tableName,
      columns: [],
      error: err instanceof Error ? err.message : String(err),
    };
  }
}
