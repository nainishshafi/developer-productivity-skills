import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

describe('MCP Protocol Integration', () => {
  test('should connect to nodejs-executor and list tools', async () => {
    const serverPath = path.resolve(__dirname, '../dist/index.js');

    const transport = new StdioClientTransport({
      command: process.execPath,
      args: [serverPath],
    });

    const client = new Client(
      {
        name: 'test-client',
        version: '1.0.0',
      },
      {
        capabilities: {},
      }
    );

    try {
      await client.connect(transport);

      const toolsList = await client.listTools();
      assert.ok(toolsList.tools.length >= 6);

      const toolNames = toolsList.tools.map((t) => t.name);
      assert.ok(toolNames.includes('execute_code'));
      assert.ok(toolNames.includes('evaluate_expression'));
      assert.ok(toolNames.includes('execute_file'));
      assert.ok(toolNames.includes('run_package_script'));
      assert.ok(toolNames.includes('run_terminal_command'));
      assert.ok(toolNames.includes('get_runtime_info'));

      // Call get_runtime_info
      const runtimeResult = await client.callTool({
        name: 'get_runtime_info',
        arguments: {},
      });

      assert.equal(runtimeResult.isError, undefined);
      const textContent = runtimeResult.content[0];
      assert.equal(textContent.type, 'text');
      const parsedInfo = JSON.parse(textContent.text);
      assert.ok(parsedInfo.nodeVersion.startsWith('v'));

      // Call execute_code
      const execResult = await client.callTool({
        name: 'execute_code',
        arguments: {
          code: 'console.log("MCP JSON-RPC SUCCESS!");',
        },
      });

      assert.equal(execResult.isError, false);
      const execContent = execResult.content[0];
      const parsedExec = JSON.parse(execContent.text);
      assert.equal(parsedExec.success, true);
      assert.match(parsedExec.stdout, /MCP JSON-RPC SUCCESS!/);

      const termResult = await client.callTool({
        name: 'run_terminal_command',
        arguments: {
          command: 'node',
          args: ['--version'],
        },
      });
      assert.equal(termResult.isError, false);
      const termContent = termResult.content[0];
      const parsedTerm = JSON.parse(termContent.text);
      assert.equal(parsedTerm.success, true);
      assert.match(parsedTerm.stdout.trim(), /^v\d+\.\d+\.\d+/);
    } finally {
      await client.close();
    }
  });
});

