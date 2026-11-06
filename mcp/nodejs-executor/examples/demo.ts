import * as os from 'node:os';
import * as crypto from 'node:crypto';

interface BenchmarkResult {
  hostname: string;
  uptime: number;
  hash: string;
  fibonacci: number;
  timestamp: string;
}

function fib(n: number): number {
  if (n <= 1) return n;
  let a = 0, b = 1;
  for (let i = 2; i <= n; i++) {
    const c = a + b;
    a = b;
    b = c;
  }
  return b;
}

const hash = crypto.createHash('sha256').update('antigravity-mcp-demo').digest('hex');
const result: BenchmarkResult = {
  hostname: os.hostname(),
  uptime: Math.round(os.uptime()),
  hash: hash.slice(0, 16),
  fibonacci: fib(35),
  timestamp: new Date().toISOString(),
};

console.log('=== TypeScript Script Execution via MCP ===');
console.log(JSON.stringify(result, null, 2));

