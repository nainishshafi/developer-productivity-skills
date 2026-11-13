export type MemoryCategory = 'ledger' | 'sidecar' | 'journal';
export type SkillPromotionStatus = 'pending' | 'promoted' | 'skipped';

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
  skillStatus?: SkillPromotionStatus;
  targetSkill?: string | null;
  promotedAt?: string | null;
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
  skillStatus?: SkillPromotionStatus;
  targetSkill?: string | null;
  promotedAt?: string | null;
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
  skillStatus?: SkillPromotionStatus;
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

export interface GetUnprocessedLearningsParams {
  category?: 'ledger' | 'journal';
  tag?: string;
  limit?: number;
}

export interface MarkLearningPromotedParams {
  ids: string[];
  status: 'promoted' | 'skipped';
  targetSkill: string;
}
