import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { DatabaseSync } from 'node:sqlite';
import { MemoryCategory, MemoryRecord, MemorySummary, SkillPromotionStatus } from '../types.js';
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
        updated_at TEXT NOT NULL,
        skill_status TEXT NOT NULL DEFAULT 'pending' CHECK(skill_status IN ('pending', 'promoted', 'skipped')),
        target_skill TEXT,
        promoted_at TEXT
      );
      CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category);
      CREATE INDEX IF NOT EXISTS idx_memories_updated_at ON memories(updated_at DESC);
    `);

    const cols = this.db.prepare('PRAGMA table_info(memories)').all() as Array<{ name: string }>;
    const existingCols = new Set(cols.map((c) => c.name));
    if (!existingCols.has('skill_status')) {
      this.db.exec("ALTER TABLE memories ADD COLUMN skill_status TEXT NOT NULL DEFAULT 'pending'");
    }
    if (!existingCols.has('target_skill')) {
      this.db.exec('ALTER TABLE memories ADD COLUMN target_skill TEXT');
    }
    if (!existingCols.has('promoted_at')) {
      this.db.exec('ALTER TABLE memories ADD COLUMN promoted_at TEXT');
    }
    this.db.exec('CREATE INDEX IF NOT EXISTS idx_memories_skill_status ON memories(skill_status)');
  }

  private rowToSummary(r: any): MemorySummary {
    return {
      id: r.id,
      category: r.category as MemoryCategory,
      title: r.title,
      summary: r.summary,
      learnings: r.learnings,
      tags: JSON.parse(r.tags || '[]'),
      createdAt: r.created_at,
      updatedAt: r.updated_at,
      skillStatus: (r.skill_status || 'pending') as SkillPromotionStatus,
      targetSkill: r.target_skill ?? null,
      promotedAt: r.promoted_at ?? null,
    };
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
      INSERT INTO memories (id, category, title, summary, learnings, tags, embedding, created_at, updated_at, skill_status, target_skill, promoted_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', NULL, NULL)
      ON CONFLICT(id) DO UPDATE SET
        category = excluded.category,
        title = excluded.title,
        summary = excluded.summary,
        learnings = excluded.learnings,
        tags = excluded.tags,
        embedding = excluded.embedding,
        updated_at = excluded.updated_at,
        skill_status = 'pending',
        target_skill = NULL,
        promoted_at = NULL
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
      skillStatus: 'pending',
      targetSkill: null,
      promotedAt: null,
    };
  }

  /**
   * List memories without returning raw vectors.
   */
  public list(category?: MemoryCategory, limit = 5, skillStatus?: SkillPromotionStatus): MemorySummary[] {
    const safeLimit = Math.max(1, Math.min(20, limit));
    const conditions: string[] = [];
    const params: Array<string | number> = [];

    if (category) {
      conditions.push('category = ?');
      params.push(category);
    }
    if (skillStatus) {
      conditions.push('skill_status = ?');
      params.push(skillStatus);
    }

    const whereClause = conditions.length > 0 ? `WHERE ${conditions.join(' AND ')}` : '';
    const stmt = this.db.prepare(`
      SELECT id, category, title, summary, learnings, tags, created_at, updated_at, skill_status, target_skill, promoted_at
      FROM memories
      ${whereClause}
      ORDER BY updated_at DESC
      LIMIT ?
    `);
    const rows = stmt.all(...params, safeLimit);
    return rows.map((r) => this.rowToSummary(r));
  }

  /**
   * Retrieve unprocessed learnings (skill_status = 'pending') for skill-doctor review.
   * Defaults to 'journal' and 'ledger' categories (excludes transient 'sidecar').
   */
  public getUnprocessedLearnings(options: {
    category?: 'ledger' | 'journal';
    tag?: string;
    limit?: number;
  } = {}): MemorySummary[] {
    const safeLimit = Math.max(1, Math.min(50, options.limit ?? 20));
    const conditions: string[] = ["skill_status = 'pending'"];
    const params: Array<string | number> = [];

    if (options.category) {
      conditions.push('category = ?');
      params.push(options.category);
    } else {
      conditions.push("category IN ('journal', 'ledger')");
    }

    const sql = `
      SELECT id, category, title, summary, learnings, tags, created_at, updated_at, skill_status, target_skill, promoted_at
      FROM memories
      WHERE ${conditions.join(' AND ')}
      ORDER BY updated_at DESC
      ${options.tag ? '' : 'LIMIT ?'}
    `;

    const rows = options.tag
      ? this.db.prepare(sql).all(...params)
      : this.db.prepare(sql).all(...params, safeLimit);

    let summaries = rows.map((r) => this.rowToSummary(r));
    if (options.tag) {
      const targetTag = options.tag.trim().toLowerCase();
      summaries = summaries
        .filter((m) => m.tags.some((t) => t.toLowerCase() === targetTag))
        .slice(0, safeLimit);
    }
    return summaries;
  }

  /**
   * Mark memories as promoted or skipped after skill-doctor processing.
   */
  public markLearningPromoted(
    ids: string[],
    status: 'promoted' | 'skipped',
    targetSkill: string
  ): {
    updatedCount: number;
    updatedIds: string[];
    status: 'promoted' | 'skipped';
    targetSkill: string;
    promotedAt: string;
  } {
    const cleanIds = Array.from(new Set(ids.map((id) => id.trim()).filter(Boolean)));
    if (cleanIds.length === 0) {
      throw new Error('At least one valid memory ID is required.');
    }
    const cleanSkill = targetSkill.trim();
    if (!cleanSkill) {
      throw new Error('targetSkill cannot be empty.');
    }

    const now = new Date().toISOString();
    const stmt = this.db.prepare(`
      UPDATE memories
      SET skill_status = ?, target_skill = ?, promoted_at = ?
      WHERE id = ?
    `);

    const updatedIds: string[] = [];
    for (const id of cleanIds) {
      const res: any = stmt.run(status, cleanSkill, now, id);
      if ((res?.changes ?? 0) > 0) {
        updatedIds.push(id);
      }
    }

    return {
      updatedCount: updatedIds.length,
      updatedIds,
      status,
      targetSkill: cleanSkill,
      promotedAt: now,
    };
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
        SELECT id, category, title, summary, learnings, tags, embedding, created_at, updated_at, skill_status, target_skill, promoted_at
        FROM memories
        WHERE category = ?
      `);
      rows = stmt.all(category);
    } else {
      const stmt = this.db.prepare(`
        SELECT id, category, title, summary, learnings, tags, embedding, created_at, updated_at, skill_status, target_skill, promoted_at
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
      skillStatus: (r.skill_status || 'pending') as SkillPromotionStatus,
      targetSkill: r.target_skill ?? null,
      promotedAt: r.promoted_at ?? null,
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
