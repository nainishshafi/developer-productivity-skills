import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import * as path from 'node:path';
import * as os from 'node:os';
import * as fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

describe('Project Memory MCP Protocol Integration', () => {
  test('should connect over stdio, list tools, and invoke save/load/search', async () => {
    const serverPath = path.resolve(__dirname, '../dist/index.js');
    const testDb = path.join(os.tmpdir(), `mcp_client_test_${Date.now()}.db`);

    const transport = new StdioClientTransport({
      command: process.execPath,
      args: ['--experimental-sqlite', serverPath],
      env: {
        ...process.env,
        PROJECT_MEMORY_DB_PATH: testDb,
      },
    });

    const client = new Client(
      {
        name: 'test-memory-client',
        version: '1.0.0',
      },
      {
        capabilities: {},
      }
    );

    try {
      await client.connect(transport);

      const toolsList = await client.listTools();
      assert.ok(toolsList.tools.length >= 7);

      const toolNames = toolsList.tools.map((t) => t.name);
      assert.ok(toolNames.includes('save_memory'));
      assert.ok(toolNames.includes('load_memory'));
      assert.ok(toolNames.includes('search_memory'));
      assert.ok(toolNames.includes('delete_memory'));
      assert.ok(toolNames.includes('clear_sidecar'));
      assert.ok(toolNames.includes('get_unprocessed_learnings'));
      assert.ok(toolNames.includes('mark_learning_promoted'));

      // 1. Call save_memory (journal session summary with learnings)
      const saveRes = await client.callTool({
        name: 'save_memory',
        arguments: {
          category: 'journal',
          title: 'Session: Scaffolding and Hybrid Search Calibration',
          summary: 'Completed MCP server setup and calibrated 40% semantic hybrid search weights.',
          learnings: 'Execution mistake avoided: dumping raw float vectors into response blows token limits. Always return concise MemorySummary objects.',
          tags: ['bloat', 'token-limits', 'session'],
        },
      });

      assert.equal(saveRes.isError, false);
      const saveContent = JSON.parse((saveRes.content[0] as any).text);
      assert.equal(saveContent.success, true);
      assert.equal(saveContent.memory.category, 'journal');

      // 2. Call load_memory
      const loadRes = await client.callTool({
        name: 'load_memory',
        arguments: {
          category: 'journal',
        },
      });

      assert.equal(loadRes.isError, false);
      const loadContent = JSON.parse((loadRes.content[0] as any).text);
      assert.equal(loadContent.total, 1);
      assert.ok(!('embedding' in loadContent.memories[0]));

      // 3. Call search_memory
      const searchRes = await client.callTool({
        name: 'search_memory',
        arguments: {
          query: 'hybrid search calibration token limits',
        },
      });

      assert.equal(searchRes.isError, false);
      const searchContent = JSON.parse((searchRes.content[0] as any).text);
      assert.ok(searchContent.results.length >= 1);
      assert.equal(searchContent.results[0].category, 'journal');

      // 4. Call get_unprocessed_learnings and mark_learning_promoted
      const unprocessedRes = await client.callTool({
        name: 'get_unprocessed_learnings',
        arguments: { category: 'journal' },
      });
      assert.equal(unprocessedRes.isError, false);
      const unprocessedContent = JSON.parse((unprocessedRes.content[0] as any).text);
      assert.equal(unprocessedContent.total, 1);

      const memId = unprocessedContent.learnings[0].id;
      const markRes = await client.callTool({
        name: 'mark_learning_promoted',
        arguments: {
          ids: [memId],
          status: 'promoted',
          targetSkill: 'load-memory',
        },
      });
      assert.equal(markRes.isError, false);
      const markContent = JSON.parse((markRes.content[0] as any).text);
      assert.equal(markContent.success, true);
      assert.equal(markContent.updatedCount, 1);

      const postMarkRes = await client.callTool({
        name: 'get_unprocessed_learnings',
        arguments: {},
      });
      const postMarkContent = JSON.parse((postMarkRes.content[0] as any).text);
      assert.equal(postMarkContent.total, 0);
    } finally {
      await client.close();
      if (fs.existsSync(testDb)) {
        try {
          fs.unlinkSync(testDb);
        } catch {}
      }
    }
  });
});

