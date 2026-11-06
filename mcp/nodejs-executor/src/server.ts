import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { z } from 'zod';
import { executeCode } from './tools/execute-code.js';
import { evaluateExpression } from './tools/evaluate-expr.js';
import { executeFile } from './tools/execute-file.js';
import { runPackageScript } from './tools/package-script.js';
import { getRuntimeInfo } from './tools/runtime-info.js';

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
      content: [{ type: 'text', text: JSON.stringify({ success: false, error: errorMsg }, null, 2) }],
      isError: true,
    };
  }
}

export function createServer(): McpServer {
  const server = new McpServer({
    name: 'nodejs-executor',
    version: '1.0.0',
  });

  // Tool: execute_code
  server.tool(
    'execute_code',
    'Execute arbitrary JavaScript or TypeScript code. In "strict" sandbox mode (default), file writes/deletions are locked to temp, child processes are blocked, and host secrets are scrubbed.',
    {
      code: z.string().describe('The JavaScript or TypeScript code snippet to execute'),
      language: z.enum(['javascript', 'typescript']).default('javascript').describe('Language mode: "javascript" or "typescript"'),
      sandboxMode: z.enum(['strict', 'workspace-write', 'unrestricted']).default('strict').describe('Sandbox policy: "strict", "workspace-write", or "unrestricted"'),
      allowFsWritePaths: z.array(z.string()).optional().describe('Optional paths permitted for writes under sandbox'),
      timeout: z.number().int().min(100).max(300000).default(30000).optional().describe('Execution timeout in milliseconds'),
      workingDirectory: z.string().optional().describe('Working directory context'),
      environmentVariables: z.record(z.string(), z.string()).optional().describe('Custom environment variables'),
    },
    (params) => handleToolExecution(() => executeCode(params))
  );

  // Tool: evaluate_expression
  server.tool(
    'evaluate_expression',
    'Evaluate a single JavaScript expression or small async snippet and return the inspected value and type.',
    {
      expression: z.string().describe('The JavaScript expression to evaluate'),
      sandboxMode: z.enum(['strict', 'workspace-write', 'unrestricted']).default('strict').describe('Sandbox policy (defaults to "strict")'),
      timeout: z.number().int().min(100).max(300000).default(30000).optional().describe('Evaluation timeout in milliseconds'),
      workingDirectory: z.string().optional().describe('Working directory context'),
      environmentVariables: z.record(z.string(), z.string()).optional().describe('Custom environment variables'),
    },
    (params) => handleToolExecution(() => evaluateExpression(params))
  );

  // Tool: execute_file
  server.tool(
    'execute_file',
    'Execute a specific .js, .mjs, .cjs, or .ts file on disk with optional command-line arguments.',
    {
      filePath: z.string().describe('Path to the script file to execute'),
      args: z.array(z.string()).optional().describe('Command line arguments to pass to the script'),
      sandboxMode: z.enum(['strict', 'workspace-write', 'unrestricted']).default('strict').describe('Sandbox policy (defaults to "strict")'),
      allowFsWritePaths: z.array(z.string()).optional().describe('Optional paths permitted for writes under sandbox'),
      timeout: z.number().int().min(100).max(300000).default(30000).optional().describe('Execution timeout in milliseconds'),
      workingDirectory: z.string().optional().describe('Working directory to execute from'),
      environmentVariables: z.record(z.string(), z.string()).optional().describe('Custom environment variables'),
    },
    (params) => handleToolExecution(() => executeFile(params))
  );

  // Tool: run_package_script
  server.tool(
    'run_package_script',
    'Run an npm, pnpm, or yarn script defined in a package.json file.',
    {
      script: z.string().describe('Name of the package script to run (e.g. "test", "build")'),
      packageManager: z.enum(['npm', 'pnpm', 'yarn']).default('npm').describe('Package manager ("npm", "pnpm", "yarn")'),
      projectPath: z.string().optional().describe('Path containing package.json'),
      args: z.array(z.string()).optional().describe('Arguments appended after "--"'),
      timeout: z.number().int().min(100).max(300000).default(60000).optional().describe('Timeout in milliseconds'),
    },
    (params) => handleToolExecution(() => runPackageScript(params))
  );

  // Tool: get_runtime_info
  server.tool(
    'get_runtime_info',
    'Get information about the Node.js runtime environment (versions, platform, memory usage, TypeScript & permission support).',
    {},
    () => handleToolExecution(() => getRuntimeInfo())
  );

  return server;
}
