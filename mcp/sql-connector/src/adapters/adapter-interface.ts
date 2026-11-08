import {
  DatabaseEngine,
  QueryOptions,
  QueryResult,
  TableMetadata,
  TableColumnMetadata,
  ExplainResult,
} from '../types.js';

export interface DatabaseAdapter {
  readonly engine: DatabaseEngine;
  isConnected(): boolean;
  connect(): Promise<void>;
  disconnect(): Promise<void>;
  query(options: QueryOptions): Promise<QueryResult>;
  listTables(): Promise<TableMetadata[]>;
  describeTable(tableName: string): Promise<TableColumnMetadata[]>;
  explain(query: string, options?: QueryOptions): Promise<ExplainResult>;
}
