---
name: save-memory
description: Use when the user asks to "save memory", "record memory", "save to ledger", "save to sidecar", "record mistake", "save learning", "remember this decision", "log anti-pattern", "persist task context", or whenever the agent needs to record an architectural decision, active task context, or hard-won lesson learned from mistakes without context bloat.
version: 1.1.1
---

# Save Memory Skill

Persist high-signal, non-bloated project memory into the **`project-memory`** MCP server.

This skill strictly partitions memories into 3 categories (**`ledger`**, **`sidecar`**, **`journal`**), enforces crisp summaries (no raw data or stack traces), and **mandates documenting learnings from mistakes and errors encountered or avoided**.

---

## The 3 Memory Categories

| Category | Purpose | When to Save | Required Structure |
| :--- | :--- | :--- | :--- |
| **`ledger`** | High-impact project truths & architectural decisions | Permanent conventions, tech stack choices, schema rules, security policies | **Summary**: Clear architectural truth or constraint.<br>**Learnings**: Rationale and traps avoided. |
| **`sidecar`** | What the agent is currently working on | Active task state, current WIP, pending refactoring steps | **Summary**: Active WIP status & next steps.<br>**Learnings**: Pitfalls to watch out for during current task. |
| **`journal`** | Summary of the current session with learnings | At checkpoints or conclusion of a working session | **Summary**: What was worked on and accomplished during the session.<br>**Learnings**: Key lessons learned, traps navigated, or mistakes made/avoided during the session. |

> [!IMPORTANT]
> **Journal Entries Require BOTH Session Summary AND Learnings**:
> A journal entry captures the **summary of the current session with learnings**. Never save a journal entry with just learnings alone! An agent reading the journal in a future session needs the context of **what was accomplished/transpired in that session** (`summary`) alongside **what lessons and mistakes were learned/avoided** (`learnings`).

---

## Anti-Bloat Rules (STRICT)

1. **NO Raw Code Dumps**: Never paste entire source files or diffs into `summary`. Use 2–4 concise bullet points.
2. **NO Stack Traces or Logs**: Never dump raw terminal outputs, stack traces, or base64 blobs into memory.
3. **Session Summary WITH Learnings for Journal**: For `journal`, `summary` captures the session's work and progress, and `learnings` captures the lessons learned and mistakes avoided. Both are required and must not be duplicates.
4. **Mandatory Learnings**: Every save MUST detail the specific mistake, trap, or wrong assumption that was made or avoided, why it happened, and how to prevent it. Never write placeholder text like "none" or "n/a".
5. **Summary Limit**: Keep `summary` under 1,500 characters.
6. **Title Limit**: Keep `title` under 150 characters, descriptive and searchable.

---

## Workflow

### Step 1 — Classify the Memory
Select the category:
- Is this a permanent project truth or architecture decision? &rarr; **`ledger`**
- Is this transient context about what is currently being worked on? &rarr; **`sidecar`**
- Is this a session summary with lessons and takeaways? &rarr; **`journal`**

### Step 2 — Construct Summary and Extract Learnings
For a `journal` entry, construct both parts:
1. **`summary` (Current Session Summary)**: What was worked on, accomplished, or altered during the current session?
2. **`learnings` (Takeaways & Mistakes Avoided)**: What key lessons were learned, what errors or traps were encountered, and what rule ensures future sessions succeed?

### Step 3 — Invoke `save_memory` via MCP

```json
{
  "name": "save_memory",
  "arguments": {
    "category": "journal",
    "title": "Session: Scaffolded SQLite MCP Memory Server & Hybrid Search",
    "summary": "Completed initial scaffolding of project-memory MCP server with node:sqlite DatabaseSync and verified 40% semantic hybrid search test suite.",
    "learnings": "Native C++ node addons fail on Windows sandbox without build tools; standardizing on built-in node:sqlite DatabaseSync avoids node-gyp build failures completely.",
    "tags": ["sqlite", "mcp", "session-recap", "hybrid-search"]
  }
}
```

### Step 4 — Verify Output
Ensure the returned response contains:
- `success: true`
- Clean `MemorySummary` object with ID and timestamps
- Confirm that NO vector embeddings or raw payloads are returned

---

## Architecture & Security Invariants (`project-memory` MCP)

- **Zero Native C++ Addon Traps on Windows**: Use Node.js 22+ built-in `node:sqlite` (`DatabaseSync`) instead of `better-sqlite3` to avoid `node-gyp` build failures in sandboxed environments. When invoking `mcp/project-memory` directly with `node` on Node.js `< 22.13.0` (e.g., `v22.12.0`), pass `--experimental-sqlite` or Node will throw `ERR_UNKNOWN_BUILTIN_MODULE: No such built-in module: node:sqlite`.
- **Path Traversal Defense**: Never expose a raw `dbPath` parameter on MCP tools; keep database resolution confined to `.project-memory/memory.db` (or validated workspace/temp paths).
- **SQLite Hygiene & Vector Boundary**: Always use parameterized prepared statements (`?`), maintain a long-lived singleton database connection, and strip 256-dimensional embeddings at the DB boundary so vectors never leak into LLM responses.

