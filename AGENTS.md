# Project Guidelines & Agent Instructions

## Python Execution Standard (STRICT)

> [!IMPORTANT]
> **ALWAYS use the local virtual environment for running Python scripts in this workspace:**
> - **Windows (PowerShell / CMD)**: `.\.venv\Scripts\python.exe <script> <args>`
> - **Linux / macOS (Bash / Zsh)**: `.venv/bin/python <script> <args>`

### Why This Rule Exists:
- **Never invoke bare `python` or `py`**: On Windows machines with Microsoft Store redirection aliases, invoking `python` directly launches the WindowsApp stub which fails inside sandboxes with `ApplicationFailedException` / `NativeCommandFailed`. Invoking `py` fails with `No suitable Python runtime found`.
- The workspace has a fully configured virtual environment located at `.\.venv` containing Python 3.13 and all necessary project dependencies.
- Every script execution, test runner, linting task, and tool command requiring Python must use `.\.venv\Scripts\python.exe`.

---

## Memory & Sub-Agent Tracking

- Use the **`project-memory`** MCP server and skills (`save-memory` and `load-memory`) to track project truths, active WIP, and lessons learned.
- Database location: `.project-memory/memory.db`.
- The 3 memory categories:
  - **`ledger`**: Permanent architectural decisions, conventions, and security policies.
  - **`sidecar`**: Active task state and WIP handoffs.
  - **`journal`**: Session and stage completion recaps requiring **BOTH** `summary` (work done) and `learnings` (mistakes made or avoided).
