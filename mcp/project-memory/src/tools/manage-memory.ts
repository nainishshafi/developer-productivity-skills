import { MemoryDatabase, getDatabase } from '../db/database.js';
import { DeleteMemoryParams } from '../types.js';

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
