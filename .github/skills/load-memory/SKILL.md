---
name: load-memory
description: Use when the user asks to "load memory", "check project memory", "what was I working on", "retrieve ledger", "search memory", "check past mistakes", "what did we learn", "load project context", "recall decisions", or at the beginning of a complex task to retrieve architectural rules, active WIP context, and past mistakes to avoid.
version: 1.0.0
---

# Load Memory Skill

Load concise, high-signal project memories from the **`project-memory`** MCP server without polluting the LLM context with bloated vectors or raw logs.

---

## When to Load Memory

1. **Session Initialization**: Check what was currently in progress (`sidecar`), past mistakes to avoid (`journal`), and core architecture boundaries (`ledger`).
2. **Before Starting a Non-Trivial Task**: Search memories for past traps and errors in the relevant domain (e.g. database, authentication, build scripts).
3. **When User Asks "What did we decide?" or "What's in progress?"**: Retrieve relevant ledger or sidecar entries.

---

## Capabilities

- **`load_memory`**: Fast retrieval of memory summaries.
  - Without arguments: returns a balanced snapshot containing active `sidecar` (current WIP), recent `journal` (mistakes avoided), and core `ledger` (architecture).
  - With `category`: filters specifically to `"ledger"`, `"sidecar"`, or `"journal"`.
- **`search_memory`**: Hybrid search with **40% semantic cosine search + 60% lexical match**.
  - Matches concepts even with different phrasing (e.g. query "sqlite build crash" finds "node-gyp compilation failure").
  - Always returns clean summaries (never returns raw vector arrays).
- **`clear_sidecar`**: Flushes active task WIP when transitioning tasks while preserving permanent ledger and journal records.

---

## Workflow

### Step 1 — Choose Retrieval Strategy

- **To resume work or inspect active task:**
  ```json
  {
    "name": "load_memory",
    "arguments": {
      "category": "sidecar"
    }
  }
  ```

- **To review past mistakes before implementing a sensitive change:**
  ```json
  {
    "name": "load_memory",
    "arguments": {
      "category": "journal",
      "limit": 5
    }
  }
  ```

- **To find specific knowledge across all memories via 40% semantic hybrid search:**
  ```json
  {
    "name": "search_memory",
    "arguments": {
      "query": "sqlite native compilation windows error",
      "limit": 5
    }
  }
  ```

---

### Step 2 — Process and Act on Memories

1. **Review Journal Session Summaries WITH Learnings**:
   - For `journal` entries, review both the **session summary** (what previous sessions accomplished) and the **learnings** (lessons learned, traps navigated, and mistakes avoided).
   - This keeps you grounded in where previous sessions left off and prevents repeating previous errors.
2. **Review `ledger` constraints**:
   - Ensure the proposed architecture or libraries do not violate existing ledger decisions.
3. **Resume or Update `sidecar`**:
   - Pick up active WIP context. If previous WIP is completed, call `clear_sidecar` to keep working context pristine and prevent outdated task noise.

