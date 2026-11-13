import { MemoryDatabase, getDatabase } from '../db/database.js';
import {
  DeleteMemoryParams,
  GetUnprocessedLearningsParams,
  MarkLearningPromotedParams,
  MemorySummary,
} from '../types.js';

export async function deleteMemory(
  params: DeleteMemoryParams,
  db?: MemoryDatabase
): Promise<{ success: boolean; deletedId: string; message: string }> {
  if (!params.id || !params.id.trim()) {
    throw new Error('Memory ID is required for deletion.');
  }

  const activeDb = db || getDatabase();
  const deleted = activeDb.delete(params.id.trim());

  return {
    success: deleted,
    deletedId: params.id.trim(),
    message: deleted
      ? `Memory "${params.id.trim()}" successfully deleted.`
      : `Memory "${params.id.trim()}" not found or already deleted.`,
  };
}

export async function clearSidecar(
  db?: MemoryDatabase
): Promise<{ success: boolean; clearedCount: number; message: string }> {
  const activeDb = db || getDatabase();
  const clearedCount = activeDb.clearSidecar();

  return {
    success: true,
    clearedCount,
    message: `Cleared ${clearedCount} transient sidecar WIP entries. Ledger and journal remain intact.`,
  };
}

export async function getUnprocessedLearnings(
  params: GetUnprocessedLearningsParams = {},
  db?: MemoryDatabase
): Promise<{
  success: boolean;
  total: number;
  learnings: MemorySummary[];
  message: string;
}> {
  const activeDb = db || getDatabase();
  const learnings = activeDb.getUnprocessedLearnings({
    category: params.category,
    tag: params.tag,
    limit: params.limit,
  });

  return {
    success: true,
    total: learnings.length,
    learnings,
    message:
      learnings.length > 0
        ? `Found ${learnings.length} unprocessed learning(s) ready for skill-doctor review.`
        : 'No unprocessed learnings found; all journal and ledger learnings are already processed.',
  };
}

export async function markLearningPromoted(
  params: MarkLearningPromotedParams,
  db?: MemoryDatabase
): Promise<{
  success: boolean;
  updatedCount: number;
  updatedIds: string[];
  status: 'promoted' | 'skipped';
  targetSkill: string;
  promotedAt: string;
  message: string;
}> {
  const activeDb = db || getDatabase();
  const result = activeDb.markLearningPromoted(params.ids, params.status, params.targetSkill);

  return {
    success: result.updatedCount > 0,
    ...result,
    message:
      result.updatedCount > 0
        ? `Marked ${result.updatedCount} learning(s) as "${result.status}" for skill "${result.targetSkill}".`
        : 'No matching memory IDs were updated.',
  };
}
