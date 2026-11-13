import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { z } from 'zod';
import { saveMemory } from './tools/save-memory.js';
import { loadMemory } from './tools/load-memory.js';
import { searchMemory } from './tools/search-memory.js';
import {
  deleteMemory,
  clearSidecar,
  getUnprocessedLearnings,
  markLearningPromoted,
} from './tools/manage-memory.js';

async function handleToolExecution<T>(
  action: () => Promise<T> | T
): Promise<{ content: Array<{ type: 'text'; text: string }>; isError?: boolean }> {
  try {
    const result = await action();
    const hasSuccess = typeof result === 'object' && result !== null && 'success' in result;
    return {
      content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      ...(hasSuccess ? { isError: !(result as { success: boolean }).success } : {}),
    };
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : String(err);
    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify({ success: false, error: errorMsg }, null, 2),
        },
      ],
      isError: true,
    };
  }
}

export function createServer(): McpServer {
  const server = new McpServer({
    name: 'project-memory',
    version: '1.0.0',
  });

  // Tool: save_memory
  server.tool(
    'save_memory',
    'Persist non-bloated project memory categorized into "ledger" (important project truths), "sidecar" (current WIP), or "journal" (summary of the current session with learnings). Both summary and learnings are strictly required.',
    {
      category: z
        .enum(['ledger', 'sidecar', 'journal'])
        .describe(
          'Memory category: "ledger" (high-impact project truths/architecture), "sidecar" (what is currently working on), or "journal" (summary of the current session with learnings)'
        ),
      title: z.string().describe('Concise title for the memory item (max 150 chars)'),
      summary: z
        .string()
        .describe(
          'Crisp, high-signal summary (for journal: summary of the current session; for ledger/sidecar: architecture or WIP summary). No bloated logs or raw code (max 1500 chars)'
        ),
      learnings: z
        .string()
        .describe(
          'Concrete learnings or mistakes encountered/avoided, root causes, and prevention rules (mandatory for all, especially journal)'
        ),
      tags: z
        .array(z.string())
        .optional()
        .describe('Optional search tags (e.g. ["sqlite", "auth", "mcp"])'),
    },
    (params) => handleToolExecution(() => saveMemory(params))
  );

  // Tool: load_memory
  server.tool(
    'load_memory',
    'Load concise project memory summaries. Returns zero bloated vectors or raw dumps. If category is omitted, loads active sidecar WIP, recent session journals, and core ledger truths.',
    {
      category: z
        .enum(['ledger', 'sidecar', 'journal'])
        .optional()
        .describe('Filter by category ("ledger", "sidecar", or "journal"). If omitted, returns balanced context.'),
      limit: z
        .number()
        .int()
        .min(1)
        .max(20)
        .default(5)
        .optional()
        .describe('Maximum number of memory summaries to return (default: 5)'),
      skillStatus: z
        .enum(['pending', 'promoted', 'skipped'])
        .optional()
        .describe('Optional filter by skill-doctor promotion status ("pending", "promoted", or "skipped")'),
    },
    (params) => handleToolExecution(() => loadMemory(params))
  );

  // Tool: search_memory
  server.tool(
    'search_memory',
    'Perform hybrid search (40% semantic cosine + 60% lexical match) across memories. Always returns lean summaries only; vectors are never returned.',
    {
      query: z.string().describe('Search query string'),
      category: z
        .enum(['ledger', 'sidecar', 'journal'])
        .optional()
        .describe('Optional category filter ("ledger", "sidecar", or "journal")'),
      limit: z
        .number()
        .int()
        .min(1)
        .max(20)
        .default(5)
        .optional()
        .describe('Maximum number of results to return (default: 5)'),
      minScore: z
        .number()
        .min(0)
        .max(1)
        .default(0.25)
        .optional()
        .describe('Minimum hybrid relevance score threshold (default: 0.25)'),
    },
    (params) => handleToolExecution(() => searchMemory(params))
  );

  // Tool: delete_memory
  server.tool(
    'delete_memory',
    'Delete a specific memory item by ID.',
    {
      id: z.string().describe('The ID of the memory item to delete'),
    },
    (params) => handleToolExecution(() => deleteMemory(params))
  );

  // Tool: clear_sidecar
  server.tool(
    'clear_sidecar',
    'Flush all transient "sidecar" working context (e.g. after a task is finished). Permanent ledger and journal entries remain untouched.',
    {},
    () => handleToolExecution(() => clearSidecar())
  );

  // Tool: get_unprocessed_learnings
  server.tool(
    'get_unprocessed_learnings',
    'Retrieve journal and ledger memories whose learnings have not yet been reviewed by skill-doctor (skill_status = "pending").',
    {
      category: z
        .enum(['ledger', 'journal'])
        .optional()
        .describe('Optional category filter ("ledger" or "journal"). Defaults to both.'),
      tag: z.string().optional().describe('Optional exact tag filter (e.g. "powershell", "security")'),
      limit: z
        .number()
        .int()
        .min(1)
        .max(50)
        .default(20)
        .optional()
        .describe('Maximum number of unprocessed learnings to return (default: 20, max: 50)'),
    },
    (params) => handleToolExecution(() => getUnprocessedLearnings(params))
  );

  // Tool: mark_learning_promoted
  server.tool(
    'mark_learning_promoted',
    'Mark one or more memory IDs as "promoted" (codified into a skill) or "skipped" after skill-doctor review so they are not re-processed.',
    {
      ids: z.array(z.string()).min(1).describe('Array of memory IDs processed by skill-doctor'),
      status: z
        .enum(['promoted', 'skipped'])
        .describe('Outcome status: "promoted" (updated/created a skill) or "skipped" (already covered or transient)'),
      targetSkill: z
        .string()
        .describe('Target skill name (e.g. "powershell-writer", "new:graphql-developer", or "none")'),
    },
    (params) => handleToolExecution(() => markLearningPromoted(params))
  );

  return server;
}
