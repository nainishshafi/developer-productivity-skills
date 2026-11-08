import { DatabaseAdapter } from './adapter-interface.js';
import {
  DatabaseConnectionConfig,
  ExplainResult,
  QueryOptions,
  QueryResult,
  TableColumnMetadata,
  TableMetadata,
} from '../types.js';
import { auditMongoQuery } from '../guardrails/mongo-guardrail.js';
import { withTimeout } from '../utils.js';

export class MongoAdapter implements DatabaseAdapter {
  readonly engine = 'mongodb' as const;
  private client: any = null;
  private db: any = null;
  private connected = false;

  constructor(private config: DatabaseConnectionConfig) {}

  isConnected(): boolean {
    return this.connected && this.client !== null;
  }

  async connect(): Promise<void> {
    if (this.connected) return;

    try {
      const { MongoClient } = await import('mongodb' as any);
      const uri = this.config.connectionString || `mongodb://${this.config.host || 'localhost'}:${this.config.port || 27017}`;
      this.client = new MongoClient(uri);
      await this.client.connect();
      const dbName = this.config.database || 'admin';
      this.db = this.client.db(dbName);
      this.connected = true;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      if (msg.includes("Cannot find package 'mongodb'") || msg.includes("Cannot find module 'mongodb'")) {
        throw new Error(
          `MongoDB driver ('mongodb') is not installed. To execute live queries against MongoDB, install the driver:\n  npm install mongodb\nConnection config validated successfully.`
        );
      }
      throw err;
    }
  }

  async disconnect(): Promise<void> {
    if (this.client) {
      await this.client.close();
      this.client = null;
      this.db = null;
      this.connected = false;
    }
  }

  async query(options: QueryOptions): Promise<QueryResult> {
    const mode = options.mode || 'read-only';
    const audit = auditMongoQuery(options.query, mode);

    if (!audit.allowed) {
      return {
        success: false,
        engine: this.engine,
        mode,
        executionTimeMs: 0,
        error: `MongoDB Guardrails blocked execution:\n- ${audit.violations.join('\n- ')}`,
      };
    }

    if (!this.connected) await this.connect();

    const startTime = performance.now();
    const maxRows = options.maxRows || 500;
    const timeoutMs = options.timeoutMs || 15000;

    try {
      let payload: any;
      try {
        payload = JSON.parse(options.query);
      } catch {
        throw new Error(
          `MongoDB commands must be provided as structured JSON, e.g. {"operation": "find", "collection": "users", "filter": {}}`
        );
      }

      const collectionName = payload.collection;
      if (!collectionName) {
        throw new Error("Missing 'collection' field in MongoDB command payload.");
      }

      const coll = this.db.collection(collectionName);
      const op = (payload.operation || 'find').toLowerCase();

      if (op === 'find') {
        const cursor = coll.find(payload.filter || {}).limit(maxRows).maxTimeMS(timeoutMs);
        const rows = await withTimeout<any[]>(cursor.toArray(), timeoutMs, 'MongoDB find');
        const executionTimeMs = Math.round(performance.now() - startTime);

        return {
          success: true,
          engine: this.engine,
          mode,
          rows,
          rowCount: rows.length,
          columns: rows.length > 0 ? Object.keys(rows[0]) : [],
          executionTimeMs,
          truncated: rows.length >= maxRows,
        };
      } else if (op === 'aggregate') {
        const cursor = coll.aggregate(payload.pipeline || []).maxTimeMS(timeoutMs);
        const rows = await withTimeout<any[]>(cursor.toArray(), timeoutMs, 'MongoDB aggregate');
        const executionTimeMs = Math.round(performance.now() - startTime);

        return {
          success: true,
          engine: this.engine,
          mode,
          rows,
          rowCount: rows.length,
          columns: rows.length > 0 ? Object.keys(rows[0]) : [],
          executionTimeMs,
          truncated: rows.length >= maxRows,
        };
      } else if (op === 'countdocuments' || op === 'count') {
        const count = await coll.countDocuments(payload.filter || {});
        const executionTimeMs = Math.round(performance.now() - startTime);
        return {
          success: true,
          engine: this.engine,
          mode,
          rows: [{ count }],
          rowCount: 1,
          columns: ['count'],
          executionTimeMs,
        };
      } else if (op === 'insertone') {
        const res = await coll.insertOne(payload.document || {});
        const executionTimeMs = Math.round(performance.now() - startTime);
        return {
          success: true,
          engine: this.engine,
          mode,
          affectedRows: res.acknowledged ? 1 : 0,
          rows: [{ insertedId: res.insertedId }],
          executionTimeMs,
        };
      } else if (op === 'updateone') {
        const res = await coll.updateOne(payload.filter, payload.update);
        const executionTimeMs = Math.round(performance.now() - startTime);
        return {
          success: true,
          engine: this.engine,
          mode,
          affectedRows: res.modifiedCount,
          executionTimeMs,
        };
      } else {
        throw new Error(`Unsupported MongoDB operation '${op}' under guarded executor.`);
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
    const collections = await this.db.listCollections().toArray();
    return collections.map((c: any) => ({
      name: c.name,
      type: 'COLLECTION',
    }));
  }

  async describeTable(collectionName: string): Promise<TableColumnMetadata[]> {
    if (!this.connected) await this.connect();
    const coll = this.db.collection(collectionName);
    const sample = await coll.findOne({});
    if (!sample) return [];

    return Object.keys(sample).map((key) => ({
      name: key,
      type: typeof sample[key],
      nullable: true,
      isPrimaryKey: key === '_id',
    }));
  }

  async explain(query: string, options?: QueryOptions): Promise<ExplainResult> {
    const audit = auditMongoQuery(query, 'read-only');
    if (!audit.allowed) {
      throw new Error(`Explain blocked by MongoDB guardrails: ${audit.violations.join('; ')}`);
    }

    if (!this.connected) await this.connect();
    const payload = JSON.parse(query);
    const coll = this.db.collection(payload.collection);
    const plan = await coll.find(payload.filter || {}).explain();

    return {
      engine: this.engine,
      plan,
      rawText: JSON.stringify(plan, null, 2),
    };
  }
}
