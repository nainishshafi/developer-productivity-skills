import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import * as path from 'node:path';
import * as fs from 'node:fs/promises';
import * as os from 'node:os';
import { fileURLToPath } from 'node:url';
import {
  executeCode,
  evaluateExpression,
  executeFile,
  runPackageScript,
  getRuntimeInfo,
  supportsNativeTypeScript,
} from '../dist/executor.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);


describe('Node.js Executor MCP Test Suite', () => {
  describe('executeCode', () => {
    test('should execute standard JavaScript with console.log output', async () => {
      const result = await executeCode({
        code: 'console.log("Hello from MCP Node.js Executor!");',
      });

      assert.equal(result.success, true);
      assert.equal(result.exitCode, 0);
      assert.match(result.stdout, /Hello from MCP Node\.js Executor!/);
      assert.equal(result.timedOut, false);
      assert(result.durationMs >= 0);
    });

    test('should execute asynchronous JavaScript with top-level await', async () => {
      const result = await executeCode({
        code: `
          const delay = (ms) => new Promise(res => setTimeout(res, ms));
          await delay(20);
          console.log("Async completed");
        `,
      });

      assert.equal(result.success, true);
      assert.match(result.stdout, /Async completed/);
    });

    test('should execute TypeScript when native support is present', async () => {
      if (!supportsNativeTypeScript()) {
        console.log('Skipping TypeScript native test (requires Node 22+)');
        return;
      }

      const result = await executeCode({
        code: `
          interface User {
            id: number;
            name: string;
          }
          const user: User = { id: 101, name: "Alice" };
          console.log(\`User: \${user.name} (\${user.id})\`);
        `,
        language: 'typescript',
      });

      assert.equal(result.success, true);
      assert.match(result.stdout, /User: Alice \(101\)/);
    });

    test('should capture runtime exceptions and stderr', async () => {
      const result = await executeCode({
        code: 'throw new Error("Intentional error test");',
      });

      assert.equal(result.success, false);
      assert.notEqual(result.exitCode, 0);
      assert.match(result.stderr, /Intentional error test/);
    });

    test('should enforce execution timeout', async () => {
      const result = await executeCode({
        code: 'setInterval(() => {}, 1000);',
        timeout: 500,
      });

      assert.equal(result.success, false);
      assert.equal(result.timedOut, true);
      assert.match(result.error ?? '', /timed out/i);
    });

    test('should pass custom environment variables', async () => {
      const result = await executeCode({
        code: 'console.log("ENV_VAL:" + process.env.MY_TEST_KEY);',
        environmentVariables: {
          MY_TEST_KEY: 'antigravity-mcp-test-secret',
        },
      });

      assert.equal(result.success, true);
      assert.match(result.stdout, /ENV_VAL:antigravity-mcp-test-secret/);
    });
  });

  describe('evaluateExpression', () => {
    test('should evaluate synchronous arithmetic expressions', async () => {
      const result = await evaluateExpression({
        expression: '7 * 6',
      });

      assert.equal(result.success, true);
      assert.equal(result.type, 'number');
      assert.equal(result.value, '42');
    });

    test('should evaluate objects and format with util.inspect', async () => {
      const result = await evaluateExpression({
        expression: '({ name: "MCP", active: true, list: [1, 2, 3] })',
      });

      assert.equal(result.success, true);
      assert.equal(result.type, 'object');
      assert.match(result.value ?? '', /name: 'MCP'/);
      assert.match(result.value ?? '', /active: true/);
    });

    test('should evaluate async expressions', async () => {
      const result = await evaluateExpression({
        expression: 'Promise.resolve({ status: "ok" })',
      });

      assert.equal(result.success, true);
      assert.match(result.value ?? '', /status: 'ok'/);
    });

    test('should capture evaluation errors cleanly', async () => {
      const result = await evaluateExpression({
        expression: 'nonExistentVariable.someProperty',
      });

      assert.equal(result.success, false);
      assert.match(result.error ?? '', /nonExistentVariable is not defined/);
    });
  });

  describe('executeFile', () => {
    test('should run an existing JavaScript file with CLI arguments', async () => {
      const tempDir = await fs.mkdtemp(path.join(os.tmpdir(), 'mcp-file-test-'));
      const testFile = path.join(tempDir, 'sample.mjs');
      try {
        await fs.writeFile(
          testFile,
          'console.log("Args:", process.argv.slice(2).join(", "));',
          'utf8'
        );

        const result = await executeFile({
          filePath: testFile,
          args: ['foo', 'bar', 'baz'],
        });

        assert.equal(result.success, true);
        assert.match(result.stdout, /Args: foo, bar, baz/);
      } finally {
        await fs.rm(tempDir, { recursive: true, force: true });
      }
    });

    test('should return error when file does not exist', async () => {
      const result = await executeFile({
        filePath: 'non-existent-file-12345.js',
      });

      assert.equal(result.success, false);
      assert.match(result.error ?? '', /File not found/i);
    });
  });

  describe('runPackageScript', () => {
    test('should run npm build or test in package.json', async () => {
      // Run the current package's "build" script
      const packageDir = path.resolve(__dirname, '..');
      const result = await runPackageScript({
        script: 'build',
        projectPath: packageDir,
        packageManager: 'npm',
      });

      assert.equal(result.success, true);
      assert.equal(result.exitCode, 0);
    });

    test('should report error for non-existent script in package.json', async () => {
      const packageDir = path.resolve(__dirname, '..');
      const result = await runPackageScript({
        script: 'non_existent_script_xyz',
        projectPath: packageDir,
      });

      assert.equal(result.success, false);
      assert.match(result.error ?? '', /not found in package\.json/i);
    });

    test('should reject package script with shell metacharacters', async () => {
      const result = await runPackageScript({
        script: 'build',
        args: ['arg1; echo injected'],
      });

      assert.equal(result.success, false);
      assert.match(result.stderr, /forbidden shell metacharacters/i);
    });
  });

  describe('Security & Hardening Sandbox Suite', () => {
    test('should block unauthorized file write outside temp under strict sandbox', async () => {
      const targetPath = path.resolve(__dirname, 'should_never_exist.txt');
      const result = await executeCode({
        code: `
          import * as fs from 'node:fs';
          try {
            fs.writeFileSync(${JSON.stringify(targetPath)}, "malicious payload");
            console.log("FAIL: WROTE FILE");
          } catch (e) {
            console.log("SUCCESSFULLY BLOCKED:", e.code || e.message);
          }
        `,
        sandboxMode: 'strict',
      });

      assert.match(result.stdout, /SUCCESSFULLY BLOCKED.*ERR_ACCESS_DENIED/);
      let fileExists = false;
      try {
        await fs.access(targetPath);
        fileExists = true;
      } catch {}
      assert.equal(fileExists, false, 'File must not be created on disk');
    });

    test('should block unauthorized file deletion outside temp under strict sandbox', async () => {
      // Create a test file in current project directory
      const tempTarget = path.resolve(__dirname, 'protected_file.txt');
      await fs.writeFile(tempTarget, 'important content', 'utf8');

      try {
        const result = await executeCode({
          code: `
            import * as fs from 'node:fs';
            import * as path from 'node:path';
            try {
              const p = path.resolve(${JSON.stringify(__dirname)}, "protected_file.txt");
              fs.unlinkSync(p);
              console.log("FAIL: DELETED FILE");
            } catch (e) {
              console.log("SUCCESSFULLY BLOCKED DELETE:", e.code || e.message);
            }
          `,
          sandboxMode: 'strict',
        });

        assert.match(result.stdout, /SUCCESSFULLY BLOCKED DELETE.*ERR_ACCESS_DENIED/);
        const stillExists = await fs.readFile(tempTarget, 'utf8');
        assert.equal(stillExists, 'important content', 'Protected file must remain untouched');
      } finally {
        try {
          await fs.rm(tempTarget, { force: true });
        } catch {}
      }
    });

    test('should block child_process execution under strict sandbox', async () => {
      const result = await executeCode({
        code: `
          try {
            const { spawnSync } = await import('node:child_process');
            spawnSync('cmd.exe');
            console.log("FAIL: SPAWNED PROCESS");
          } catch (e) {
            console.log("SUCCESSFULLY BLOCKED PROCESS:", e.code || e.message);
          }
        `,
        sandboxMode: 'strict',
      });

      assert.match(result.stdout, /SUCCESSFULLY BLOCKED PROCESS.*ERR_ACCESS_DENIED/);
    });

    test('should scrub sensitive host environment secrets from executed code', async () => {
      // Simulate host containing sensitive tokens
      process.env.GITHUB_TOKEN = 'ghp_secret_token_12345';
      process.env.AWS_SECRET_ACCESS_KEY = 'aws_super_secret_key_67890';
      process.env.MY_DATABASE_PASSWORD = 'super_secret_db_pass';

      try {
        const result = await executeCode({
          code: `
            console.log("GITHUB_TOKEN:" + process.env.GITHUB_TOKEN);
            console.log("AWS_SECRET:" + process.env.AWS_SECRET_ACCESS_KEY);
            console.log("DB_PASS:" + process.env.MY_DATABASE_PASSWORD);
          `,
          sandboxMode: 'strict',
        });

        assert.match(result.stdout, /GITHUB_TOKEN:undefined/);
        assert.match(result.stdout, /AWS_SECRET:undefined/);
        assert.match(result.stdout, /DB_PASS:undefined/);
      } finally {
        delete process.env.GITHUB_TOKEN;
        delete process.env.AWS_SECRET_ACCESS_KEY;
        delete process.env.MY_DATABASE_PASSWORD;
      }
    });

    test('should reject destructive root deletion via pre-execution safety check', async () => {
      const result = await executeCode({
        code: 'import * as fs from "node:fs"; fs.rmSync("C:\\\\", { recursive: true });',
        sandboxMode: 'strict',
      });

      assert.equal(result.success, false);
      assert.match(result.stderr, /pre-execution safety policy/i);
    });
  });

  describe('getRuntimeInfo', () => {
    test('should return valid runtime details', () => {
      const info = getRuntimeInfo();

      assert.ok(info.nodeVersion.startsWith('v'));
      assert.ok(info.v8Version);
      assert.ok(info.platform);
      assert.ok(info.architecture);
      assert.ok(info.cpuCount > 0);
      assert.ok(info.memoryUsageMb.rss > 0);
      assert.equal(typeof info.typescriptNativeSupport, 'boolean');
    });
  });
});
