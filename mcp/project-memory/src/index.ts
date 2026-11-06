#!/usr/bin/env node

import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { createServer } from './server.js';
import { closeDatabase } from './db/database.js';

const server = createServer();

async function main() {
  const transport = new StdioServerTransport();

  let isExiting = false;
  const gracefulExit = async (code = 0, reason?: string) => {
    if (isExiting) return;
    isExiting = true;

    if (reason) {
      process.stderr.write(`Project Memory MCP server shutting down: ${reason}\n`);
    }

    try {
      await server.close();
    } catch {}

    try {
      closeDatabase();
    } catch {}

    process.exit(code);
  };

  transport.onclose = () => {
    gracefulExit(0, 'transport closed');
  };

  transport.onerror = (err) => {
    process.stderr.write(`MCP transport error: ${err instanceof Error ? err.message : String(err)}\n`);
    gracefulExit(1, 'transport error');
  };

  process.on('SIGINT', () => gracefulExit(0, 'received SIGINT'));
  process.on('SIGTERM', () => gracefulExit(0, 'received SIGTERM'));
  if (process.platform === 'win32') {
    process.on('SIGBREAK', () => gracefulExit(0, 'received SIGBREAK'));
  }

  process.stdin.on('close', () => gracefulExit(0, 'stdin closed'));
  process.stdin.on('end', () => gracefulExit(0, 'stdin ended'));

  await server.connect(transport);
  process.stderr.write('Project Memory MCP server running on stdio (SQLite + 40% Semantic Hybrid Search)\n');
}

process.on('uncaughtException', (err) => {
  process.stderr.write(`Uncaught exception: ${err?.stack || err}\n`);
  process.exit(1);
});

process.on('unhandledRejection', (reason) => {
  process.stderr.write(`Unhandled rejection: ${reason}\n`);
});

main().catch((error) => {
  process.stderr.write(`Fatal MCP server error: ${error instanceof Error ? error.stack : error}\n`);
  process.exit(1);
});

