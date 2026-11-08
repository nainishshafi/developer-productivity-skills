import { DatabaseAdapter } from './adapter-interface.js';
import { DatabaseConnectionConfig, DatabaseEngine } from '../types.js';
import { SqliteAdapter } from './sqlite-adapter.js';
import { PostgresAdapter } from './postgres-adapter.js';
import { SqlServerAdapter } from './sqlserver-adapter.js';
import { OracleAdapter } from './oracle-adapter.js';
import { MongoAdapter } from './mongodb-adapter.js';
import { AccessAdapter } from './access-adapter.js';
import { MySqlAdapter } from './mysql-adapter.js';

interface PoolEntry {
  adapter: DatabaseAdapter;
  lastUsed: number;
}

export class AdapterFactory {
  private static connectionPool: Map<string, PoolEntry> = new Map();
  public static readonly MAX_POOL_SIZE: number = 20;
  public static readonly DEFAULT_IDLE_TIMEOUT_MS: number = 600000; // 10 minutes

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
   * Gets or creates a connected database adapter instance with LRU eviction
   */
  public static async getAdapter(config: DatabaseConnectionConfig): Promise<DatabaseAdapter> {
    const key = this.getConnectionKey(config);

    if (this.connectionPool.has(key)) {
      const entry = this.connectionPool.get(key)!;
      if (entry.adapter.isConnected()) {
        entry.lastUsed = Date.now();
        // Refresh Map insertion order for LRU tracking
        this.connectionPool.delete(key);
        this.connectionPool.set(key, entry);
        return entry.adapter;
      } else {
        this.connectionPool.delete(key);
      }
    }

    // Enforce LRU capacity cap before adding new connection
    if (this.connectionPool.size >= this.MAX_POOL_SIZE) {
      await this.evictOldest();
    }

    const adapter = this.createAdapter(config);
    await adapter.connect();
    this.connectionPool.set(key, {
      adapter,
      lastUsed: Date.now(),
    });
    return adapter;
  }

  /**
   * Evicts and disconnects the least-recently used adapter
   */
  public static async evictOldest(): Promise<void> {
    let oldestKey: string | null = null;
    let oldestTime = Infinity;

    for (const [key, entry] of this.connectionPool.entries()) {
      if (entry.lastUsed < oldestTime) {
        oldestTime = entry.lastUsed;
        oldestKey = key;
      }
    }

    if (oldestKey) {
      const entry = this.connectionPool.get(oldestKey);
      this.connectionPool.delete(oldestKey);
      if (entry?.adapter) {
        try {
          await entry.adapter.disconnect();
        } catch {}
      }
    }
  }

  /**
   * Scans and evicts idle connections older than the specified duration
   */
  public static async evictIdle(maxIdleMs: number = AdapterFactory.DEFAULT_IDLE_TIMEOUT_MS): Promise<number> {
    const now = Date.now();
    const toEvict: string[] = [];

    for (const [key, entry] of this.connectionPool.entries()) {
      if (now - entry.lastUsed >= maxIdleMs) {
        toEvict.push(key);
      }
    }

    for (const key of toEvict) {
      const entry = this.connectionPool.get(key);
      this.connectionPool.delete(key);
      if (entry?.adapter) {
        try {
          await entry.adapter.disconnect();
        } catch {}
      }
    }

    return toEvict.length;
  }

  /**
   * Returns current active pool size
   */
  public static getPoolSize(): number {
    return this.connectionPool.size;
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
    for (const [key, entry] of this.connectionPool.entries()) {
      try {
        await entry.adapter.disconnect();
      } catch {}
    }
    this.connectionPool.clear();
  }
}
