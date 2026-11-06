import { MemoryDatabase, getDatabase } from '../db/database.js';
import { sanitizeMemoryInput } from '../utils/sanitizer.js';
import { MemorySummary, SaveMemoryParams } from '../types.js';

export async function saveMemory(
  params: SaveMemoryParams,
  db?: MemoryDatabase
): Promise<{ success: boolean; memory: MemorySummary; message: string }> {
  const sanitized = sanitizeMemoryInput(params);
  const activeDb = db || getDatabase();

  const memory = activeDb.save({
    category: sanitized.category,
    title: sanitized.title,
    summary: sanitized.summary,
    learnings: sanitized.learnings,
    tags: sanitized.tags,
  });

  const categoryDescriptions = {
    ledger: 'Permanent project truth / architectural decision',
    sidecar: 'Current WIP context / active task focus',
    journal: 'Summary of the current session with learnings',
  };

  return {
    success: true,
    memory,
    message:
      sanitized.category === 'journal'
        ? `Journal memory saved successfully with current session summary and learnings.`
        : `Memory saved successfully under "${sanitized.category}" (${categoryDescriptions[sanitized.category]}).`,
  };
}
