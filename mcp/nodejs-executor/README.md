# Node.js Executor MCP Server

A Model Context Protocol (MCP) server that provides a **controlled terminal environment** for CLI command automation (package scripts and hardened child-process execution) alongside sandboxed JavaScript/TypeScript code execution, expression evaluation, and script file execution inside a Node.js runtime.

Designed for AI assistants including **Claude Code**, **Claude Desktop**, **GitHub Copilot**, **Cursor**, and **Antigravity**.

---

## Features

- **Multi-Layer Security Sandbox**:
  - **Filesystem Write/Delete Boundary**: Under `strict` mode (default), file writes and deletions are strictly locked to the OS temp folder (`--allow-fs-write=<tempDir>`). Attempts to delete or modify host files throw `ERR_ACCESS_DENIED` at the Node C++ engine level.
  - **Child Process Execution Block**: Blocks spawning subprocesses (`child_process.spawn/exec/fork` are denied by the runtime).
  - **Secret Sanitization**: Automatically scrubs sensitive host environment variables (`*KEY*`, `*TOKEN*`, `*SECRET*`, `*PASSWORD*`, `AWS_*`, `GITHUB_*`, etc.) before passing environment to child processes.
  - **Pre-execution Static Safety Checks**: Immediately detects and aborts broad root destructive patterns (`rmSync('/')`, `format C:`, etc.).
  - **Safe Package Execution**: Blocks shell metacharacters (`&`, `|`, `;`, `>`, `$`) in package script arguments to prevent command injection.
- **Arbitrary Code Execution (`execute_code`)**: Run JavaScript (ESM) and TypeScript code snippets with top-level await, module imports, and access to Node.js standard libraries.
- **TypeScript Support**: Native TypeScript execution on Node.js 22+ (via `--experimental-strip-types`) with zero transpilation overhead.
- **Expression Evaluation (`evaluate_expression`)**: Quickly evaluate expressions with detailed type inspection and deep object formatting via `node:util.inspect`.
- **File Execution (`execute_file`)**: Run `.js`, `.mjs`, `.cjs`, and `.ts` script files from disk with arguments.
- **Package Scripts & CLI Runner (`run_package_script`)**: Execute `npm`, `pnpm`, or `yarn` lifecycle and run scripts from any project's `package.json` without shell-injection risks.
- **Controlled Terminal Execution (`sandboxMode: "unrestricted"`)**: While `"strict"` (default) and `"workspace-write"` block `child_process`, passing `sandboxMode: "unrestricted"` enables `--allow-child-process` for host CLI commands while **still** enforcing destructive-pattern blocking, host secret scrubbing, and `--allow-fs-write` confinement to the workspace + temp directory.
- **Runtime Diagnostics (`get_runtime_info`)**: Inspect Node.js version, V8 version, platform, architecture, memory usage, CPU count, and native TypeScript status.
- **Robust Process Management**: Configurable execution timeouts, process tree termination, stdout/stderr stream truncation limits (512 KB) to prevent memory exhaustion, and automatic temporary file cleanup.
- **Strict MCP Protocol Compliance**: Communicates over standard I/O (`stdio`) without stdout pollution. All diagnostics and logs route to `stderr`.

---

## Tools

### 1. `execute_code`
Execute JavaScript or TypeScript code in a dedicated Node.js process.

**Parameters:**
- `code` (`string`, required): The code snippet to execute.
- `language` (`"javascript" | "typescript"`, optional, default: `"javascript"`): Syntax language.
- `sandboxMode` (`"strict" | "workspace-write" | "unrestricted"`, optional, default: `"strict"`):
  - `"strict"` (default): Writes/deletions locked to temp directory, `child_process` disabled, host secrets scrubbed.
  - `"workspace-write"`: Allows file writes in current workspace directory, `child_process` disabled, secrets scrubbed.
  - `"unrestricted"`: Enables `--allow-child-process` alongside workspace + temp write access, while **still** enforcing destructive-pattern blocking, host secret scrubbing, and `--allow-fs-write` confinement outside the workspace.
- `allowFsWritePaths` (`string[]`, optional): Specific directories allowed for writes when running in sandbox mode.
- `timeout` (`number`, optional, default: `30000`, max: `300000`): Timeout in milliseconds.
- `workingDirectory` (`string`, optional): Working directory for the process.
- `environmentVariables` (`Record<string, string>`, optional): Custom environment variables.

**Example Request:**
```json
{
  "code": "const res = await fetch('https://api.github.com/zen'); console.log(await res.text());",
  "language": "javascript"
}
```

### 2. `evaluate_expression`
Evaluate a single expression or async expression and inspect its value.

**Parameters:**
- `expression` (`string`, required): JavaScript expression (e.g. `crypto.randomUUID()`, `Buffer.from('hello').toString('base64')`).
- `timeout` (`number`, optional, default: `30000`): Timeout in milliseconds.
- `workingDirectory` (`string`, optional): Working directory context.
- `environmentVariables` (`Record<string, string>`, optional): Environment variables.

**Example Request:**
```json
{
  "expression": "[1, 2, 3, 4, 5].map(x => x ** 2)"
}
```

### 3. `execute_file`
Execute an existing script file with optional CLI arguments.

**Parameters:**
- `filePath` (`string`, required): Relative or absolute path to `.js`, `.mjs`, `.cjs`, or `.ts` file.
- `args` (`string[]`, optional): Command-line arguments.
- `timeout` (`number`, optional, default: `30000`): Timeout in milliseconds.
- `workingDirectory` (`string`, optional): Working directory context.
- `environmentVariables` (`Record<string, string>`, optional): Environment variables.

### 4. `run_package_script`
Run an npm, pnpm, or yarn script defined in a `package.json`.

**Parameters:**
- `script` (`string`, required): Script name (e.g., `"build"`, `"test"`, `"lint"`).
- `packageManager` (`"npm" | "pnpm" | "yarn"`, optional, default: `"npm"`): Package manager binary.
- `projectPath` (`string`, optional): Path to folder containing `package.json`.
- `args` (`string[]`, optional): Additional CLI arguments appended after `--`.
- `timeout` (`number`, optional, default: `60000`): Timeout in milliseconds.

### 5. `run_terminal_command`
Execute an arbitrary non-shell CLI binary in a **controlled terminal environment** (`shell: false`), enforcing blocked-binary checks (`cmd`, `powershell`, `pwsh`, `bash`, `sh`, `diskpart`, `reg`), shell metacharacter rejection, destructive-argument blocking, `workingDirectory` containment (workspace or temp directory), host secret scrubbing, and timeout clamping (`100`–`300000` ms).

**Parameters:**
- `command` *(required)*: Executable name or path (no spaces or shell metacharacters; raw shells are blocked)
- `args` *(optional)*: Array of CLI arguments (shell metacharacters `[&|;><$\n\r]` rejected)
- `workingDirectory` *(optional)*: Execution directory (must be within the workspace or OS temp directory)
- `environmentVariables` *(optional)*: Key-value map of extra environment variables
- `timeout` *(optional)*: Timeout in ms (clamped `100`–`300000`, default `30000`)

**Output:** Returns `ExecutionResult` including `stdoutLogFile`, the path to a timestamped log file (`<os.tmpdir()>/nodejs-executor-logs/stdout-<timestamp>-<pid>.log`) containing the captured `stdout`:
```json
{
  "success": true,
  "exitCode": 0,
  "stdout": "...",
  "stderr": "",
  "durationMs": 42,
  "timedOut": false,
  "stdoutLogFile": "<os.tmpdir>/nodejs-executor-logs/stdout-2026-11-13T08-00-00-000Z-12345.log"
}
```

**Usage Notes & Examples:**
You can run any direct non-shell CLI binary (such as `python`, `node`, `git`, `rg`, `grep`, `npm`, `dotnet`, `docker`, `kubectl`) in a controlled terminal environment:

- **Run a Python script (using workspace `.venv`):**
  ```json
  { "command": ".venv/Scripts/python.exe", "args": ["path/to/script.py", "--flag", "value"] }
  ```
- **Search code with `rg` / `grep` / `git grep`:**
  ```json
  { "command": "rg", "args": ["-n", "runTerminalCommand", "mcp/nodejs-executor/src"] }
  ```
  ```json
  { "command": "git", "args": ["grep", "-n", "runTerminalCommand", "mcp/nodejs-executor/src"] }
  ```
  *(Note: regex patterns containing `|` or `$` are rejected by the `[&|;><$\n\r]` metacharacter guard.)*
- **Run Git / build / CLI tools:**
  ```json
  { "command": "git", "args": ["status", "-s"] }
  ```
- **Shell built-ins & pipelines:** Commands that rely on a shell (`cmd`, `powershell`, `pwsh`, `bash`, `sh`), pipes (`|`), redirects (`>`), or command chaining (`&&`) are blocked by design. Split multi-step work into separate `run_terminal_command` calls or use `execute_code` (`sandboxMode: "unrestricted"` with Node `fs` / `child_process`).

---

### 6. `get_runtime_info`
Retrieve Node.js host environment diagnostics.

**Parameters:** None.

---

## Installation & Setup

### Prerequisites
- Node.js >= 18.0.0 (Node.js 22+ recommended for native TypeScript support)
- npm >= 9.0.0

### Build from Source

```bash
cd mcp/nodejs-executor
npm install
npm run build
npm test
```

---

## Client Configuration

### Claude Desktop

Add the server to your `claude_desktop_config.json`:

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "nodejs-executor": {
      "command": "node",
      "args": [
        "/path/to/developer-productivity-skills/mcp/nodejs-executor/dist/index.js"
      ]
    }
  }
}
```

### Claude Code

Add via the Claude Code CLI:

```bash
claude mcp add nodejs-executor node /path/to/developer-productivity-skills/mcp/nodejs-executor/dist/index.js
```

Or configure in `.mcp.json` at your project root:

```json
{
  "mcpServers": {
    "nodejs-executor": {
      "command": "node",
      "args": ["./mcp/nodejs-executor/dist/index.js"]
    }
  }
}
```

### Cursor / VS Code

In `.cursor/mcp.json` or `.vscode/settings.json`:

```json
{
  "mcpServers": {
    "nodejs-executor": {
      "command": "node",
      "args": ["./mcp/nodejs-executor/dist/index.js"]
    }
  }
}
```

---

## Project Structure

```
mcp/nodejs-executor/
├── src/
│   ├── process/
│   │   ├── runner.ts          # Child process execution, stdio streaming & timeouts
│   │   └── terminator.ts      # Graceful process tree termination & signals
│   ├── security/
│   │   ├── permissions.ts     # Node.js permission flags & sandbox isolation
│   │   ├── sanitizer.ts       # Host environment secret scrubbing
│   │   └── validator.ts       # Pre-execution safety linter (destructive actions)
│   ├── tools/
│   │   ├── evaluate-expr.ts   # evaluate_expression tool handler
│   │   ├── execute-code.ts    # execute_code tool handler
│   │   ├── execute-file.ts    # execute_file tool handler
│   │   ├── package-script.ts  # run_package_script tool handler
│   │   ├── terminal-command.ts # run_terminal_command tool handler
│   │   └── runtime-info.ts    # get_runtime_info tool handler
│   ├── executor.ts            # Public API Facade
│   ├── index.ts               # CLI executable & stdio transport entrypoint
│   ├── server.ts              # MCP Server definition & tool registration
│   └── types.ts               # TypeScript types, interfaces & Zod schemas
├── tests/
│   ├── executor.test.ts       # Execution, security sandbox & timeout test suite
│   └── mcp-client.test.ts     # MCP JSON-RPC protocol compliance tests
├── examples/
│   └── demo.ts                # Programmatic Facade usage example
├── scripts/
│   └── invoke.mjs             # Interactive manual testing harness
├── package.json
├── tsconfig.json
└── README.md
```

---

## License

MIT

