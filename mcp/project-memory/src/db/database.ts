import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { DatabaseSync } from 'node:sqlite';
import { MemoryCategory, MemoryRecord, MemorySummary } from '../types.js';
import { generateEmbedding, rankMemories } from '../search/semantic.js';

let defaultInstance: MemoryDatabase | null = null;

/**
 * Returns the singleton database instance.
 */
export function getDatabase(): MemoryDatabase {
  if (!defaultInstance) {
    defaultInstance = new MemoryDatabase();
  }
  return defaultInstance;
}

/**
 * Sets or overrides the singleton database instance (useful for unit tests).
 */
export function setDatabase(db: MemoryDatabase | null): void {
  defaultInstance = db;
}

/**
 * Gracefully closes the singleton database instance.
 */
export function closeDatabase(): void {
  if (defaultInstance) {
    defaultInstance.close();
    defaultInstance = null;
  }
}

/**
 * Validates that target path resides safely within the allowed parent directory.
 * Case-insensitive for Windows compatibility.
 */
function isPathContained(parent: string, target: string): boolean {
  const normParent = path.resolve(parent).toLowerCase();
  const normTarget = path.resolve(target).toLowerCase();
  const rel = path.relative(normParent, normTarget);
  return !rel.startsWith('..') && !path.isAbsolute(rel);
}

export class MemoryDatabase {
  private db: DatabaseSync;
  private dbPath: string;

  constructor(customPath?: string) {
    if (customPath) {
      const resolved = path.resolve(customPath);
      const cwd = process.cwd();
      const tmp = os.tmpdir();

      if (!isPathContained(cwd, resolved) && !isPathContained(tmp, resolved)) {
        throw new Error(`Security Exception: custom dbPath must be located within workspace (${cwd}) or temp directory.`);
      }
      this.dbPath = resolved;
    } else if (process.env.PROJECT_MEMORY_DB_PATH) {
      this.dbPath = path.resolve(process.env.PROJECT_MEMORY_DB_PATH);
    } else {
      // Default to .project-memory/memory.db in the workspace root
      const dir = path.resolve(process.cwd(), '.project-memory');
      if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
      }
      this.dbPath = path.join(dir, 'memory.db');
    }

    const parentDir = path.dirname(this.dbPath);
    if (!fs.existsSync(parentDir)) {
      fs.mkdirSync(parentDir, { recursive: true });
    }

    this.db = new DatabaseSync(this.dbPath);
    this.initSchema();
  }

  private initSchema(): void {
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS memories (
        id TEXT PRIMARY KEY,
        category TEXT NOT NULL CHECK(category IN ('ledger', 'sidecar', 'journal')),
        title TEXT NOT NULL,
        summary TEXT NOT NULL,
        learnings TEXT NOT NULL,
        tags TEXT NOT NULL,
        embedding TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
      );
      CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category);
      CREATE INDEX IF NOT EXISTS idx_memories_updated_at ON memories(updated_at DESC);
    `);
  }

  /**
   * Save or update a memory record.
   * Embeds title + summary + learnings for 40% semantic search.
   * Returns a lean summary without raw vector bloat.
   */
  public save(data: {
    id?: string;
    category: MemoryCategory;
    title: string;
    summary: string;
    learnings: string;
    tags: string[];
  }): MemorySummary {
    const id = data.id || `mem_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
    const now = new Date().toISOString();

    // Compute 256-dim embedding from combined context
    const fullTextForEmbedding = `${data.title} ${data.tags.join(' ')} ${data.summary} ${data.learnings}`;
    const embedding = generateEmbedding(fullTextForEmbedding);

    const stmt = this.db.prepare(`
      INSERT INTO memories (id, category, title, summary, learnings, tags, embedding, created_at, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
      ON CONFLICT(id) DO UPDATE SET
        category = excluded.category,
        title = excluded.title,
        summary = excluded.summary,
        learnings = excluded.learnings,
        tags = excluded.tags,
        embedding = excluded.embedding,
        updated_at = excluded.updated_at
    `);

    stmt.run(
      id,
      data.category,
      data.title,
      data.summary,
      data.learnings,
      JSON.stringify(data.tags),
      JSON.stringify(embedding),
      now,
      now
    );

    return {
      id,
      category: data.category,
      title: data.title,
      summary: data.summary,
      learnings: data.learnings,
      tags: data.tags,
      createdAt: now,
      updatedAt: now,
    };
  }

  /**
   * List memories without returning raw vectors.
   */
  public list(category?: MemoryCategory, limit = 5): MemorySummary[] {
    const safeLimit = Math.max(1, Math.min(20, limit));

    let rows: any[];
    if (category) {
      const stmt = this.db.prepare(`
        SELECT id, category, title, summary, learnings, tags, created_at, updated_at
        FROM memories
        WHERE category = ?
        ORDER BY updated_at DESC
        LIMIT ?
      `);
      rows = stmt.all(category, safeLimit);
    } else {
      const stmt = this.db.prepare(`
        SELECT id, category, title, summary, learnings, tags, created_at, updated_at
        FROM memories
        ORDER BY updated_at DESC
        LIMIT ?
      `);
      rows = stmt.all(safeLimit);
    }

    return rows.map((r) => ({
      id: r.id,
      category: r.category as MemoryCategory,
      title: r.title,
      summary: r.summary,
      learnings: r.learnings,
      tags: JSON.parse(r.tags || '[]'),
      createdAt: r.created_at,
      updatedAt: r.updated_at,
    }));
  }

  /**
   * Hybrid Search: 40% Semantic Cosine + 60% Lexical.
   * Returns ranked summaries only (no vectors).
   */
  public search(
    query: string,
    category?: MemoryCategory,
    limit = 5,
    minScore = 0.25
  ): MemorySummary[] {
    let rows: any[];
    if (category) {
      const stmt = this.db.prepare(`
        SELECT id, category, title, summary, learnings, tags, embedding, created_at, updated_at
        FROM memories
        WHERE category = ?
      `);
      rows = stmt.all(category);
    } else {
      const stmt = this.db.prepare(`
        SELECT id, category, title, summary, learnings, tags, embedding, created_at, updated_at
        FROM memories
      `);
      rows = stmt.all();
    }

    const records: MemoryRecord[] = rows.map((r) => ({
      id: r.id,
      category: r.category as MemoryCategory,
      title: r.title,
      summary: r.summary,
      learnings: r.learnings,
      tags: JSON.parse(r.tags || '[]'),
      embedding: JSON.parse(r.embedding || '[]'),
      createdAt: r.created_at,
      updatedAt: r.updated_at,
    }));

    return rankMemories(query, records, limit, minScore);
  }

  /**
   * Delete a memory by id.
   */
  public delete(id: string): boolean {
    const stmt = this.db.prepare('DELETE FROM memories WHERE id = ?');
    const result: any = stmt.run(id);
    return (result?.changes ?? 0) > 0;
  }

  /**
   * Clear all transient sidecar memories (e.g. on task completion).
   */
  public clearSidecar(): number {
    const stmt = this.db.prepare("DELETE FROM memories WHERE category = 'sidecar'");
    const result: any = stmt.run();
    return result?.changes ?? 0;
  }

  public getDbPath(): string {
    return this.dbPath;
  }

  public close(): void {
    try {
      this.db.close();
    } catch {}
  }
}
