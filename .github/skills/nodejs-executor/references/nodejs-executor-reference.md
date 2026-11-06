# Node.js Executor Reference Guide

Comprehensive reference for the `nodejs-executor` MCP server tools, schemas, security policies, and error handling.

---

## 1. Tool Schemas

### `execute_code`

Execute arbitrary JavaScript or TypeScript code snippets inside an isolated child process.

```typescript
interface ExecuteCodeParams {
  code: string;                          // Required: The code snippet to execute
  language?: 'javascript' | 'typescript';// Default: 'javascript'
  sandboxMode?: 'strict' | 'workspace-write' | 'unrestricted'; // Default: 'strict'
  allowFsWritePaths?: string[];          // Additional paths allowed for writing in sandbox
  timeout?: number;                      // Default: 30000ms (max 300000ms)
  workingDirectory?: string;             // Execution directory context
  environmentVariables?: Record<string, string>; // Custom environment variables
}
```

**Output Schema:**
```typescript
interface ExecutionResult {
  success: boolean;
  exitCode: number | null;
  stdout: string;
  stderr: string;
  durationMs: number;
  timedOut: boolean;
  error?: string;
  sandboxMode?: 'strict' | 'workspace-write' | 'unrestricted';
}
```

---

### `evaluate_expression`

Quickly evaluate a single expression or async expression and inspect its value and type.

```typescript
interface EvaluateExpressionParams {
  expression: string;                    // Required: Expression (e.g. "Math.PI", "crypto.randomUUID()")
  sandboxMode?: 'strict' | 'workspace-write' | 'unrestricted'; // Default: 'strict'
  timeout?: number;                      // Default: 30000ms
  workingDirectory?: string;
  environmentVariables?: Record<string, string>;
}
```

**Output Schema:**
```typescript
interface ExpressionResult {
  success: boolean;
  type?: string;                         // typeof result ('number', 'string', 'object', etc.)
  value?: string;                        // util.inspect formatted string
  stdout?: string;
  stderr?: string;
  durationMs: number;
  timedOut: boolean;
  error?: string;
  sandboxMode?: 'strict' | 'workspace-write' | 'unrestricted';
}
```

---

### `execute_file`

Execute an existing script file on disk.

```typescript
interface ExecuteFileParams {
  filePath: string;                      // Required: Path to .js, .mjs, .cjs, or .ts file
  args?: string[];                       // Command-line arguments passed to process.argv
  sandboxMode?: 'strict' | 'workspace-write' | 'unrestricted'; // Default: 'strict'
  allowFsWritePaths?: string[];
  timeout?: number;                      // Default: 30000ms
  workingDirectory?: string;
  environmentVariables?: Record<string, string>;
}
```

---

### `run_package_script`

Run a script defined in a `package.json` file.

```typescript
interface RunPackageScriptParams {
  script: string;                        // Required: Script name (e.g. 'build', 'test', 'lint')
  packageManager?: 'npm' | 'pnpm' | 'yarn'; // Default: 'npm'
  projectPath?: string;                  // Directory containing package.json
  args?: string[];                       // Extra arguments appended after '--'
  timeout?: number;                      // Default: 60000ms
}
```

---

### `get_runtime_info`

Retrieve system and Node.js runtime diagnostics.

**Output Schema:**
```typescript
interface RuntimeInfo {
  nodeVersion: string;
  v8Version: string;
  platform: string;
  architecture: string;
  osRelease: string;
  cpuCount: number;
  memoryUsageMb: {
    rss: number;
    heapTotal: number;
    heapUsed: number;
    external: number;
  };
  uptimeSeconds: number;
  workingDirectory: string;
  execPath: string;
  typescriptNativeSupport: boolean;
  permissionModelSupport: boolean;
}
```

---

## 2. Sandbox Security Architecture

```
                    +------------------------------------+
                    |        Incoming Tool Call          |
                    +------------------------------------+
                                      |
                                      v
                    +------------------------------------+
                    |  Pre-Execution Safety Linter       |
                    |  (Blocks root deletions/format)    |
                    +------------------------------------+
                                      |
                                      v
                    +------------------------------------+
                    |  Environment Sanitizer             |
                    |  (Scrubs GITHUB_*, AWS_*, *TOKEN*) |
                    +------------------------------------+
                                      |
                                      v
                    +------------------------------------+
                    |  Node.js Permission Model          |
                    |  --experimental-permission         |
                    |  --allow-fs-read=*                 |
                    |  --allow-fs-write=<tempDir>        |
                    |  (child_process BLOCKED)           |
                    +------------------------------------+
                                      |
                                      v
                    +------------------------------------+
                    |  Child Process Sandbox Execution   |
                    |  - 30s Hard Timeout               |
                    |  - 512 KB Output Stream Caps       |
                    |  - Automatic Temp Cleanup          |
                    +------------------------------------+
```

---

## 3. Environment Variable Scrubbing List

In `strict` and `workspace-write` modes, any environment variable matching the following patterns is stripped:

- Keys containing: `TOKEN`, `SECRET`, `KEY`, `PASSWORD`, `AUTH`, `CREDENTIAL`, `PASSWD`, `PRIVATE`, `CERT`, `SESSION`, `COOKIE`, `BEARER`, `PIN`
- Prefixes: `AWS_`, `GITHUB_`, `GH_`, `AZURE_`, `GCP_`, `GOOGLE_`, `OPENAI_`, `ANTHROPIC_`, `SLACK_`, `DISCORD_`, `STRIPE_`, `DATABASE_`, `DB_`, `PG_`, `MONGO_`, `REDIS_`

