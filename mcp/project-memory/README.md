# Project Memory MCP Server

A Model Context Protocol (MCP) server providing persistent project memory backed by SQLite (`node:sqlite`), **40% semantic hybrid search**, anti-bloat guards, and strict 3-category memory partitioning:

1. **`ledger`**: Permanent project truths, architecture decisions, technology stacks, constraints.
2. **`sidecar`**: What is currently being worked on (transient task state, WIP context, current focus).
3. **`journal`**: Summary of the current session with learnings (what was accomplished/transpired in the session, paired with lessons learned and mistakes avoided).

---

## Key Features

- **SQLite Persistence**: Stored locally in `.project-memory/memory.db` with zero external native compilation dependencies (uses Node 22 native `DatabaseSync`).
- **40% Semantic Hybrid Search**:
  $$\text{Score} = (0.40 \times \text{Semantic Cosine}) + (0.60 \times \text{Lexical Overlap})$$
  Evaluated across 256-dimensional subword and semantic embeddings.
- **Strict Anti-Bloat Enforcement**:
  - Raw vector embeddings are **never returned** to the client.
  - Summaries are capped at 1,500 characters.
  - Automatically strips stack traces, base64 data, and giant JSON dumps.
  - Mandates clear, high-signal learnings on every save.
- **Transient Sidecar Flushing**: `clear_sidecar` enables clearing active task state when transitioning between features without wiping permanent ledger or journal records.

---

## MCP Tools

| Tool | Parameters | Description |
| :--- | :--- | :--- |
| `save_memory` | `category` (`ledger`\|`sidecar`\|`journal`), `title`, `summary`, `learnings`, `tags?` | Validates, sanitizes, embeds, and saves memory. Requires session summary and learnings. |
| `load_memory` | `category?`, `limit?`, `skillStatus?` | Loads clean summaries (zero vectors). Defaults to balanced sidecar + journal + ledger context. |
| `search_memory` | `query`, `category?`, `limit?`, `minScore?` | Runs 40% semantic + 60% lexical hybrid search across memories. |
| `get_unprocessed_learnings` | `category?` (`ledger`\|`journal`), `tag?`, `limit?` | Retrieves pending learnings (`skill_status = 'pending'`) for periodic `skill-doctor` review. |
| `mark_learning_promoted` | `ids`, `status` (`promoted`\|`skipped`), `targetSkill` | Marks reviewed learnings as promoted into a skill or skipped so they are not re-processed. |
| `delete_memory` | `id` | Deletes a specific memory entry by ID. |
| `clear_sidecar` | None | Flushes all transient sidecar entries. |

---

## Configuration

In `claude_desktop_config.json`, Cursor, or Antigravity configuration:

```json
{
  "mcpServers": {
    "project-memory": {
      "command": "node",
      "args": [
        "--experimental-sqlite",
        "./mcp/project-memory/dist/index.js"
      ]
    }
  }
}
```

Or with an absolute path:

```json
{
  "mcpServers": {
    "project-memory": {
      "command": "node",
      "args": [
        "--experimental-sqlite",
        "/path/to/developer-productivity-skills/mcp/project-memory/dist/index.js"
      ]
    }
  }
}
```

