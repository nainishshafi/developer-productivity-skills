import * as fs from 'node:fs/promises';
import * as os from 'node:os';
import * as path from 'node:path';
import * as crypto from 'node:crypto';
import { runProcess } from '../process/runner.js';
import { getPermissionFlags } from '../security/permissions.js';
import { sanitizeEnvironment } from '../security/sanitizer.js';
import { preExecutionSecurityCheck } from '../security/validator.js';
import type { EvaluateExpressionOptions, ExpressionResult } from '../types.js';

const DEFAULT_TIMEOUT_MS = 30000;
const MAX_TIMEOUT_MS = 300000;

export async function evaluateExpression(options: EvaluateExpressionOptions): Promise<ExpressionResult> {
  const sandboxMode = options.sandboxMode ?? 'strict';
  const timeoutMs = Math.min(Math.max(options.timeout ?? DEFAULT_TIMEOUT_MS, 100), MAX_TIMEOUT_MS);
  const cwd = options.workingDirectory ? path.resolve(options.workingDirectory) : process.cwd();

  const safetyCheck = preExecutionSecurityCheck(options.expression, sandboxMode);
  if (!safetyCheck.allowed) {
    return {
      success: false,
      error: safetyCheck.reason,
      stderr: `Security policy violation: ${safetyCheck.reason}`,
      durationMs: 0,
      timedOut: false,
      sandboxMode,
    };
  }

  const tempDir = await fs.mkdtemp(path.join(os.tmpdir(), 'node-mcp-eval-'));
  const scriptPath = path.join(tempDir, `eval_${crypto.randomUUID()}.mjs`);
  const uniqueId = crypto.randomUUID().replace(/-/g, '');
  const delimiterStart = `__MCP_EVAL_${uniqueId}_START__`;
  const delimiterEnd = `__MCP_EVAL_${uniqueId}_END__`;

  const wrappedCode = `
import * as util from 'node:util';

const DELIMITER_START = '${delimiterStart}';
const DELIMITER_END = '${delimiterEnd}';

(async () => {
  try {
    const __exprValue = await (${options.expression});
    const __type = typeof __exprValue;
    const __inspected = util.inspect(__exprValue, {
      depth: 6,
      maxArrayLength: 100,
      breakLength: 80,
      compact: false,
      colors: false,
      showHidden: false,
      getters: true,
    });

    console.log(DELIMITER_START + JSON.stringify({
      success: true,
      type: __type,
      value: __inspected
    }) + DELIMITER_END);
  } catch (err) {
    const errorDetails = err instanceof Error
      ? { message: err.message, stack: err.stack, name: err.name }
      : { message: String(err) };

    console.error(DELIMITER_START + JSON.stringify({
      success: false,
      error: errorDetails.message,
      stack: errorDetails.stack
    }) + DELIMITER_END);
    process.exitCode = 1;
  }
})();
`;

  try {
    await fs.writeFile(scriptPath, wrappedCode, 'utf8');

    const permFlags = getPermissionFlags(tempDir, cwd, sandboxMode);
    const args = [...permFlags, scriptPath];
    const cleanEnv = sanitizeEnvironment(options.environmentVariables, sandboxMode);

    const res = await runProcess(process.execPath, args, {
      cwd,
      env: cleanEnv,
      timeoutMs,
    });

    const combinedOutput = res.stdout + '\n' + res.stderr;
    const regex = new RegExp(`${delimiterStart}([\\s\\S]*?)${delimiterEnd}`);
    const match = combinedOutput.match(regex);

    const cleanedStdout = res.stdout
      .replace(new RegExp(`${delimiterStart}[\\s\\S]*?${delimiterEnd}\\r?\\n?`), '')
      .trim();
    const cleanedStderr = res.stderr
      .replace(new RegExp(`${delimiterStart}[\\s\\S]*?${delimiterEnd}\\r?\\n?`), '')
      .trim();

    if (match && match[1]) {
      try {
        const parsed = JSON.parse(match[1]);
        if (parsed.success) {
          return {
            success: true,
            type: parsed.type,
            value: parsed.value,
            stdout: cleanedStdout,
            stderr: cleanedStderr,
            durationMs: res.durationMs,
            timedOut: res.timedOut,
            sandboxMode,
          };
        } else {
          return {
            success: false,
            error: parsed.error,
            stdout: cleanedStdout,
            stderr: parsed.stack || cleanedStderr,
            durationMs: res.durationMs,
            timedOut: res.timedOut,
            sandboxMode,
          };
        }
      } catch {}
    }

    return {
      success: res.success,
      stdout: cleanedStdout,
      stderr: cleanedStderr,
      durationMs: res.durationMs,
      timedOut: res.timedOut,
      error: res.error || (res.success ? undefined : 'Expression evaluation failed'),
      sandboxMode,
    };
  } finally {
    try {
      await fs.rm(tempDir, { recursive: true, force: true });
    } catch {}
  }
}

