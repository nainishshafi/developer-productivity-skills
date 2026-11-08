import { DatabaseAdapter } from './adapter-interface.js';
import { DatabaseConnectionConfig, DatabaseEngine } from '../types.js';
import { SqliteAdapter } from './sqlite-adapter.js';
import { PostgresAdapter } from './postgres-adapter.js';
import { SqlServerAdapter } from './sqlserver-adapter.js';
import { OracleAdapter } from './oracle-adapter.js';
import { MongoAdapter } from './mongodb-adapter.js';
import { AccessAdapter } from './access-adapter.js';
import { MySqlAdapter } from './mysql-adapter.js';

export class AdapterFactory {
  private static connectionPool: Map<string, DatabaseAdapter> = new Map();

  /**
   * Generates a stable cache key for a given connection config
   */
  public static getConnectionKey(config: DatabaseConnectionConfig): string {
    if (config.connectionString) {
      return `${config.engine}://${config.connectionString}`;
    }
    if (config.filePath) {
      return `${config.engine}://${config.filePath}`;
    }
    return `${config.engine}://${config.user || 'anon'}@${config.host || 'localhost'}:${config.port || 0}/${config.database || 'default'}`;
  }

  /**
   * Gets or creates a connected database adapter instance
   */
  public static async getAdapter(config: DatabaseConnectionConfig): Promise<DatabaseAdapter> {
    const key = this.getConnectionKey(config);

    if (this.connectionPool.has(key)) {
      const existing = this.connectionPool.get(key)!;
      if (existing.isConnected()) {
        return existing;
      }
    }

    const adapter = this.createAdapter(config);
    await adapter.connect();
    this.connectionPool.set(key, adapter);
    return adapter;
  }

  /**
   * Instantiates the matching adapter for an engine
   */
  public static createAdapter(config: DatabaseConnectionConfig): DatabaseAdapter {
    switch (config.engine) {
      case 'sqlite':
        return new SqliteAdapter(config);
      case 'postgres':
        return new PostgresAdapter(config);
      case 'sqlserver':
        return new SqlServerAdapter(config);
      case 'oracle':
        return new OracleAdapter(config);
      case 'mongodb':
        return new MongoAdapter(config);
      case 'msaccess':
        return new AccessAdapter(config);
      case 'mysql':
        return new MySqlAdapter(config);
      default:
        throw new Error(`Unsupported database engine: '${config.engine}'`);
    }
  }

  /**
   * Closes all open connections in the pool
   */
  public static async closeAll(): Promise<void> {
    for (const [key, adapter] of this.connectionPool.entries()) {
      try {
        await adapter.disconnect();
      } catch {}
    }
    this.connectionPool.clear();
  }
}
