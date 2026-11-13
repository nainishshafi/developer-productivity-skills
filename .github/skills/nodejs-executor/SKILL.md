---
name: nodejs-executor
description: Use when the user asks to "run nodejs code", "execute javascript", "execute typescript", "run js snippet", "run node script", "evaluate expression", "execute node file", "run package script", "run terminal command", "test node snippet", or wants to execute JavaScript/TypeScript code or CLI commands safely using the nodejs-executor MCP server with multi-layered sandbox security.
version: 1.1.0
---

# Node.js Executor Skill

Execute JavaScript and TypeScript code, evaluate expressions, run script files, and automate CLI commands/package scripts in a controlled terminal environment using the `nodejs-executor` MCP server with multi-layered security sandboxing.

---

## Capabilities

- **`execute_code`**: Execute multi-line JavaScript (ESM) or TypeScript snippets with top-level await and Node standard modules.
- **`evaluate_expression`**: Evaluate a single expression or async expression with deep object introspection and type detection.
- **`execute_file`**: Run an existing `.js`, `.mjs`, `.cjs`, or `.ts` file on disk with command-line arguments.
- **`run_package_script`**: Execute `npm`, `pnpm`, or `yarn` run scripts from any `package.json` with argument injection protections.
- **`run_terminal_command`**: Execute non-shell CLI binaries directly (`shell: false`) with blocked-shell enforcement, metacharacter rejection, destructive-argument blocking, `workingDirectory` containment, host secret scrubbing, and automatic timestamped `stdoutLogFile` output.
- **`get_runtime_info`**: Inspect Node.js version, V8 version, platform, architecture, memory usage, CPU count, and permission model support.

---

## Security Sandbox Policies

Every execution defaults to **`strict`** mode for defense-in-depth protection:

| Mode | Filesystem Permissions | Process Spawning | Environment Variables | Intended Use |
| :--- | :--- | :--- | :--- | :--- |
| **`strict`** (default) | Writes/deletes locked to OS temp folder (`--allow-fs-write=<tempDir>`). Host files cannot be modified or deleted. | **BLOCKED** (`child_process` disabled). | Sensitive keys scrubbed (`*KEY*`, `*TOKEN*`, `*SECRET*`, `AWS_*`, `GITHUB_*`, etc.). | Safe execution of untrusted snippets, calculations, tests, and data parsing. |
| **`workspace-write`** | Writes/deletes permitted in temp and current working directory. Files outside workspace remain protected. | **BLOCKED** (`child_process` disabled). | Sensitive keys scrubbed. | File generation tasks, building artifacts, or transforming project files. |
| **`unrestricted`** | Writes/deletes confined to temp and workspace (`--allow-fs-write`); host-wide writes remain blocked. | Allowed (`--allow-child-process`); destructive root patterns still blocked. | Sensitive host keys still scrubbed (`*KEY*`, `*TOKEN*`, etc.). | Controlled CLI command automation or child-process execution when explicitly requested. |

---

## Workflow

### Step 1 — Select the Right Tool and Sandbox Mode

1. **Quick expression inspection** (e.g., `Math.hypot(3, 4)`, `crypto.randomUUID()`):
   - Use `evaluate_expression`
   - Mode: `sandboxMode: "strict"`
2. **Multi-line code snippet / async algorithm / data processing**:
   - Use `execute_code`
   - Set `language: "typescript"` if type annotations or TypeScript syntax are used (native Node 22+ type stripping).
   - Mode: `sandboxMode: "strict"` (default)
3. **Running an existing script file**:
   - Use `execute_file` with `filePath: "path/to/script.ts"`
   - Pass optional `args: ["arg1", "arg2"]`
4. **Running npm / pnpm / yarn lifecycle scripts**:
   - Use `run_package_script` with `script: "build"` or `script: "test"`
   - Ensure arguments do not contain shell metacharacters (`&`, `|`, `;`, `>`, `$`).
5. **Running direct non-shell CLI binaries (e.g., Python, `rg`, `git`, `dotnet`)**:
   - Use `run_terminal_command` with `command` set to the executable (no spaces, e.g., `".venv/Scripts/python.exe"` or `"rg"`) and `args: [...]`.
   - Captured `stdout` is also written to a timestamped log file (`<os.tmpdir()>/nodejs-executor-logs/stdout-<timestamp>-<pid>.log`), returned as `stdoutLogFile` in the tool response.
   - Raw shells (`cmd`, `powershell`, `pwsh`, `bash`, `sh`), shell built-ins, pipes (`|`), redirects (`>`), and `args` containing `[&|;><$\n\r]` (including regexes with `|` or `$`) are blocked. For multi-step pipelines or shell-like processing, use `execute_code` with `sandboxMode: "unrestricted"` instead.

---

### Step 2 — Invocation Methods

#### Method A: Direct MCP Tool Invocation (inside AI sessions)
When connected to the `nodejs-executor` MCP server in Claude Code, Claude Desktop, Cursor, Copilot, or Antigravity:

```json
{
  "name": "execute_code",
  "arguments": {
    "code": "const res = await fetch('https://api.github.com/zen'); console.log(await res.text());",
    "language": "javascript",
    "sandboxMode": "strict"
  }
}
```

#### Method B: Automated Runner Script
You can trigger execution programmatically from terminal or scripts:

```bash
node mcp/nodejs-executor/scripts/invoke.mjs
```

---

### Step 3 — Handling Results and Security Errors

Responses return structured JSON:
- `success`: `boolean` indicating if the execution succeeded.
- `stdout`: Captured standard output stream (capped at 512 KB).
- `stderr`: Captured standard error stream.
- `durationMs`: Process run duration in milliseconds.
- `timedOut`: `true` if the 30-second timeout was triggered.
- `sandboxMode`: Sandbox policy applied during execution.

#### Security Policy Errors
If code attempts an unauthorized operation:
- **Unauthorized write/delete outside temp**:
  ```
  Error: Access to this API has been restricted (code: 'ERR_ACCESS_DENIED', permission: 'FileSystemWrite')
  ```
- **Unauthorized process spawning**:
  ```
  Error: Access to this API has been restricted (code: 'ERR_ACCESS_DENIED', permission: 'ChildProcess')
  ```
- **Pre-execution safety rejection**:
  ```
  Security policy violation: Blocked by pre-execution safety policy: broad destructive root filesystem operation detected.
  ```

---

## Prerequisites & Setup

- **Node.js**: `>= 20.0.0` (Node 22+ recommended for native TypeScript support)
- **Server build**:
  ```bash
  cd mcp/nodejs-executor
  npm install
  npm run build
  npm test
  ```
- **MCP Registration**:
  ```bash
  claude mcp add nodejs-executor node <path-to-repo>/mcp/nodejs-executor/dist/index.js
  ```

