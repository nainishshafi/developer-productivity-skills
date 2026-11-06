export type MemoryCategory = 'ledger' | 'sidecar' | 'journal';

export interface MemoryRecord {
  id: string;
  category: MemoryCategory;
  title: string;
  summary: string;
  learnings: string;
  tags: string[];
  embedding: number[];
  createdAt: string;
  updatedAt: string;
}

/**
 * Lean summary returned to agents.
 * Raw vectors and bloated content are strictly omitted.
 */
export interface MemorySummary {
  id: string;
  category: MemoryCategory;
  title: string;
  summary: string;
  learnings: string;
  tags: string[];
  createdAt: string;
  updatedAt: string;
  relevanceScore?: number;
}

export interface SaveMemoryParams {
  category: MemoryCategory;
  title: string;
  summary: string;
  learnings: string;
  tags?: string[];
}

export interface LoadMemoryParams {
  category?: MemoryCategory;
  limit?: number;
}

export interface SearchMemoryParams {
  query: string;
  category?: MemoryCategory;
  limit?: number;
  minScore?: number;
}

export interface DeleteMemoryParams {
  id: string;
}
