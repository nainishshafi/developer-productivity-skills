import { AdapterFactory } from '../adapters/adapter-factory.js';
import { DatabaseConnectionConfig } from '../types.js';

export interface TestConnectionParams {
  connection: DatabaseConnectionConfig;
}

export async function testConnection(params: TestConnectionParams): Promise<{
  success: boolean;
  engine: string;
  latencyMs: number;
  message: string;
  error?: string;
}> {
  const startTime = performance.now();
  try {
    const adapter = await AdapterFactory.getAdapter(params.connection);
    const latencyMs = Math.round(performance.now() - startTime);
    return {
      success: true,
      engine: params.connection.engine,
      latencyMs,
      message: `Successfully connected to ${params.connection.engine} database in ${latencyMs}ms.`,
    };
  } catch (err: unknown) {
    const latencyMs = Math.round(performance.now() - startTime);
    return {
      success: false,
      engine: params.connection.engine,
      latencyMs,
      message: `Failed to connect to ${params.connection.engine} database.`,
      error: err instanceof Error ? err.message : String(err),
    };
  }
}
