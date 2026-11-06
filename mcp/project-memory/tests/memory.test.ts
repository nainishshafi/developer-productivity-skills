import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { MemoryDatabase, setDatabase, closeDatabase } from '../dist/db/database.js';
import { sanitizeMemoryInput } from '../dist/utils/sanitizer.js';
import { saveMemory } from '../dist/tools/save-memory.js';
import { loadMemory } from '../dist/tools/load-memory.js';
import { searchMemory } from '../dist/tools/search-memory.js';
import { clearSidecar, deleteMemory } from '../dist/tools/manage-memory.js';
import { generateEmbedding, cosineSimilarity, rankMemories } from '../dist/search/semantic.js';

async function runTests() {
  console.log('--- Starting Project Memory Test Suite ---\n');

  const tempDbPath = path.join(os.tmpdir(), `test_memory_${Date.now()}.db`);
  const db = new MemoryDatabase(tempDbPath);
  setDatabase(db); // Register test singleton instance

  try {
    // 1. Sanitizer & Anti-Bloat Tests
    console.log('[Test 1] Testing Bloat Prevention and Category Validation...');
    assert.throws(
      () =>
        sanitizeMemoryInput({
          category: 'invalid_cat',
          title: 'Test',
          summary: 'Summary',
          learnings: 'Learned something',
        }),
      /Invalid category "invalid_cat"/
    );

    // Rejects empty or placeholder learnings
    assert.throws(
      () =>
        sanitizeMemoryInput({
          category: 'journal',
          title: 'Bad Save',
          summary: 'Summary',
          learnings: 'none',
        }),
      /Learnings field cannot be empty/
    );

    // Rejects journal with identical summary and learnings
    assert.throws(
      () =>
        sanitizeMemoryInput({
          category: 'journal',
          title: 'Duplicate fields',
          summary: 'Made a mistake and fixed it.',
          learnings: 'Made a mistake and fixed it.',
        }),
      /Journal entry needs a distinct session summary/
    );

    // Strips stack traces
    const sanitizedWithStack = sanitizeMemoryInput({
      category: 'journal',
      title: 'Crash fix',
      summary: 'Encountered error during async evaluation\n   at Object.run (file.js:10:5)\nFixed by checking null.',
      learnings: 'Always validate null input before property access to prevent crash.',
    });
    assert.ok(!sanitizedWithStack.summary.includes('at Object.run'));
    console.log('✓ Sanitizer correctly validates categories, enforces summary with learnings, and strips bloat.');

    // 2. Semantic Embedding & Cosine Similarity Tests
    console.log('[Test 2] Testing 256-dim Semantic Embedding & Cosine Similarity...');
    const v1 = generateEmbedding('SQLite database persistence engine');
    const v2 = generateEmbedding('SQLite db persistent storage system');
    const v3 = generateEmbedding('Frontend CSS flexbox layout styling');

    assert.equal(v1.length, 256);
    const simClose = cosineSimilarity(v1, v2);
    const simFar = cosineSimilarity(v1, v3);

    console.log(`  Similarity (SQLite vs Storage): ${simClose.toFixed(3)}`);
    console.log(`  Similarity (SQLite vs CSS):     ${simFar.toFixed(3)}`);
    assert.ok(simClose > simFar, 'Related concepts should have higher cosine similarity');
    console.log('✓ Semantic embeddings and cosine similarity functioning as expected.');

    // 3. Save Memory Tests (ledger, sidecar, journal)
    console.log('[Test 3] Testing save_memory for ledger, sidecar, and journal...');
    const resLedger = await saveMemory({
      category: 'ledger',
      title: 'Database Architecture Decision',
      summary: 'Use embedded SQLite (node:sqlite) for local zero-dependency storage.',
      learnings: 'Native C++ packages like better-sqlite3 often fail compilation on Windows; native node:sqlite avoids node-gyp build failures.',
      tags: ['sqlite', 'database', 'architecture'],
    });
    assert.equal(resLedger.success, true);
    assert.equal(resLedger.memory.category, 'ledger');

    const resSidecar = await saveMemory({
      category: 'sidecar',
      title: 'Active Task: Implementing Search Scoring',
      summary: 'Currently calibrating hybrid 40% semantic and 60% lexical search weights.',
      learnings: 'Avoid returning full vectors in API responses to prevent LLM context exhaustion.',
      tags: ['search', 'wip', 'weights'],
    });
    assert.equal(resSidecar.success, true);
    assert.equal(resSidecar.memory.category, 'sidecar');

    const resJournal = await saveMemory({
      category: 'journal',
      title: 'Mistake: Hardcoded Vector Dumps in Response',
      summary: 'Agent previously returned raw Float64Array vectors, blowing up token limits.',
      learnings: 'Execution mistake: dumped 256 raw vector floats into chat. Fix: strictly return lean MemorySummary and filter vectors at the DB boundary.',
      tags: ['mistake', 'tokens', 'vectors'],
    });
    assert.equal(resJournal.success, true);
    assert.equal(resJournal.memory.category, 'journal');
    console.log('✓ Successfully saved items across ledger, sidecar, and journal categories.');

    // 4. Load Memory Tests (Summary only, NO vectors)
    console.log('[Test 4] Testing load_memory and verifying summary-only contract...');
    const loadedAll = await loadMemory();
    assert.equal(loadedAll.success, true);
    assert.equal(loadedAll.memories.length, 3);

    for (const mem of loadedAll.memories) {
      assert.ok(!('embedding' in mem), 'Vectors must NEVER be returned in loaded memories');
      assert.ok(mem.title);
      assert.ok(mem.summary);
      assert.ok(mem.learnings);
    }
    console.log('✓ load_memory returned clean summaries with zero vector bloat.');

    // 5. 40% Semantic Hybrid Search Tests
    console.log('[Test 5] Testing 40% Semantic Hybrid Search...');
    const searchRes = await searchMemory({
      query: 'token exhaustion from raw floats',
    });
    assert.equal(searchRes.success, true);
    assert.ok(searchRes.results.length > 0);
    assert.equal(searchRes.results[0].category, 'journal');
    assert.ok(searchRes.results[0].relevanceScore! > 0.3);
    assert.ok(!('embedding' in searchRes.results[0]), 'Vectors must NEVER be returned in search results');
    console.log(`✓ Hybrid search matched top result: "${searchRes.results[0].title}" (score: ${searchRes.results[0].relevanceScore})`);

    // 6. Manage Sidecar & Deletion
    console.log('[Test 6] Testing clear_sidecar and delete_memory...');
    const clearRes = await clearSidecar();
    assert.equal(clearRes.clearedCount, 1);

    const postClearLoaded = await loadMemory();
    assert.equal(postClearLoaded.memories.length, 2);
    assert.ok(!postClearLoaded.memories.some((m) => m.category === 'sidecar'));

    const delRes = await deleteMemory({ id: resLedger.memory.id });
    assert.equal(delRes.success, true);
    console.log('✓ clear_sidecar flushed WIP, delete_memory deleted item successfully.');

    // 7. Security: Path Traversal Containment Check
    console.log('[Test 7] Testing Path Traversal Containment...');
    assert.throws(
      () => new MemoryDatabase('C:\\Windows\\System32\\unauthorized.db'),
      /Security Exception/
    );
    console.log('✓ Path traversal attempts rejected with Security Exception.');

    console.log('\n--- All Project Memory Tests Passed Successfully! ---');
  } finally {
    closeDatabase();
    if (fs.existsSync(tempDbPath)) {
      try {
        fs.unlinkSync(tempDbPath);
      } catch {}
    }
  }
}

runTests().catch((err) => {
  console.error('Test Suite Failed:', err);
  process.exit(1);
});
