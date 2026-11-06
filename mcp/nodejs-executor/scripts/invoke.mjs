import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const serverPath = path.resolve(__dirname, '../dist/index.js');
const demoScriptPath = path.resolve(__dirname, '../examples/demo.ts');

async function run() {
  console.log('1. Starting Node.js Executor MCP Server over stdio...');
  const transport = new StdioClientTransport({
    command: process.execPath,
    args: [serverPath],
  });

  const client = new Client(
    { name: 'mcp-cli-runner', version: '1.0.0' },
    { capabilities: {} }
  );

  try {
    await client.connect(transport);
    console.log(' Connected to MCP server.\n');

    // Step 1: List tools
    console.log('2. Discovering tools via tools/list...');
    const tools = await client.listTools();
    console.log(` Available tools (${tools.tools.length}):`);
    for (const tool of tools.tools) {
      console.log(`   - ${tool.name}: ${tool.description.slice(0, 70)}...`);
    }
    console.log('');

    // Step 2: Invoke execute_file
    console.log(`3. Invoking tool "execute_file" with script: ${demoScriptPath}`);
    const fileResult = await client.callTool({
      name: 'execute_file',
      arguments: {
        filePath: demoScriptPath,
      },
    });

    console.log(' Result from execute_file:');
    const parsedFileResult = JSON.parse(fileResult.content[0].text);
    console.log(`   Success: ${parsedFileResult.success}`);
    console.log(`   Duration: ${parsedFileResult.durationMs}ms`);
    console.log(`   Exit Code: ${parsedFileResult.exitCode}`);
    console.log('   Stdout:\n' + parsedFileResult.stdout.split('\n').map(l => '     ' + l).join('\n'));
    console.log('');

    // Step 3: Invoke execute_code
    console.log('4. Invoking tool "execute_code" with dynamic async snippet...');
    const codeSnippet = `
      import * as fs from 'node:fs/promises';
      import * as path from 'node:path';
      
      const files = await fs.readdir('.');
      console.log('Current working directory contains:', files.length, 'entries');
      console.log('Top 5 entries:', files.slice(0, 5));
    `;
    const codeResult = await client.callTool({
      name: 'execute_code',
      arguments: {
        code: codeSnippet,
        language: 'javascript',
      },
    });

    console.log(' Result from execute_code:');
    const parsedCodeResult = JSON.parse(codeResult.content[0].text);
    console.log(`   Success: ${parsedCodeResult.success}`);
    console.log(`   Duration: ${parsedCodeResult.durationMs}ms`);
    console.log('   Stdout:\n' + parsedCodeResult.stdout.split('\n').map(l => '     ' + l).join('\n'));
    console.log('');

    // Step 4: Invoke evaluate_expression
    console.log('5. Invoking tool "evaluate_expression" with: [10, 20, 30].reduce((a, b) => a + b, 0)...');
    const evalResult = await client.callTool({
      name: 'evaluate_expression',
      arguments: {
        expression: '[10, 20, 30].reduce((a, b) => a + b, 0)',
      },
    });

    console.log(' Result from evaluate_expression:');
    const parsedEval = JSON.parse(evalResult.content[0].text);
    console.log(`   Success: ${parsedEval.success}`);
    console.log(`   Type: ${parsedEval.type}`);
    console.log(`   Value: ${parsedEval.value}`);
    console.log('');

  } finally {
    console.log('6. Closing MCP transport...');
    await client.close();
    console.log(' Done.');
  }
}

run().catch((err) => {
  console.error('MCP Runner Error:', err);
  process.exit(1);
});

