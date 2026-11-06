import { MemoryDatabase, getDatabase } from '../db/database.js';
import { LoadMemoryParams, MemorySummary } from '../types.js';

export async function loadMemory(
  params: LoadMemoryParams = {},
  db?: MemoryDatabase
): Promise<{
  success: boolean;
  total: number;
  category?: string;
  memories: MemorySummary[];
  message: string;
}> {
  const activeDb = db || getDatabase();
  const limit = Math.max(1, Math.min(params.limit || 5, 20));
  let memories: MemorySummary[];

  if (params.category) {
    memories = activeDb.list(params.category, limit);
  } else {
    // Balanced load: active sidecar context first, followed by journal session entries and ledger truths
    const sidecars = activeDb.list('sidecar', 3);
    const journals = activeDb.list('journal', 3);
    const ledgers = activeDb.list('ledger', 3);
    memories = [...sidecars, ...journals, ...ledgers].slice(0, limit);
  }

  return {
    success: true,
    total: memories.length,
    category: params.category || 'all',
    memories,
    message: `Loaded ${memories.length} memory summaries. All bloated text and vector embeddings omitted.`,
  };
}
