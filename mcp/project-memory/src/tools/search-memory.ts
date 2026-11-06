import { MemoryDatabase, getDatabase } from '../db/database.js';
import { MemorySummary, SearchMemoryParams } from '../types.js';

export async function searchMemory(
  params: SearchMemoryParams,
  db?: MemoryDatabase
): Promise<{
  success: boolean;
  query: string;
  total: number;
  category?: string;
  searchWeights: string;
  results: MemorySummary[];
}> {
  if (!params.query || !params.query.trim()) {
    throw new Error('Search query cannot be empty.');
  }

  const activeDb = db || getDatabase();
  const limit = Math.max(1, Math.min(params.limit || 5, 20));
  const minScore = params.minScore !== undefined ? params.minScore : 0.25;

  const results = activeDb.search(params.query.trim(), params.category, limit, minScore);

  return {
    success: true,
    query: params.query.trim(),
    total: results.length,
    category: params.category || 'all',
    searchWeights: '40% Semantic Cosine + 60% Lexical Keyword',
    results,
  };
}
