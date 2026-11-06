# Node.js Event Loop Health, CPU Offloading & Streams

Prevent event loop starvation, manage CPU-intensive tasks safely, and handle large data volumes using streaming with backpressure.

---

## 1. Protecting the Node.js Event Loop

Node.js executes JavaScript on a single thread. Blocking this thread freezes all incoming HTTP requests, timers, and I/O callbacks across the entire server.

### The Golden Rules
1. **Never use synchronous I/O in server requests**: No `fs.readFileSync`, `fs.writeFileSync`, `child_process.execSync`.
2. **Beware of expensive JSON parsing/serialization**: Parsing a 50MB JSON string synchronously locks the event loop for hundreds of milliseconds.
3. **Beware of Regex Denial of Service (ReDoS)**: Catastrophic backtracking in regex locks the event loop.

```typescript
// ❌ ANTI-PATTERN: Synchronous crypto or JSON blocks the single thread
import crypto from 'node:crypto';

export function hashPasswordSync(password: string) {
  // Freezes the server for 200ms per request!
  return crypto.pbkdf2Sync(password, 'salt', 100_000, 64, 'sha512').toString('hex');
}

// ✅ BEST PRACTICE: Asynchronous non-blocking crypto (uses libuv thread pool)
export function hashPassword(password: string): Promise<string> {
  return new Promise((resolve, reject) => {
    crypto.pbkdf2(password, 'salt', 100_000, 64, 'sha512', (err, derivedKey) => {
      if (err) reject(err);
      else resolve(derivedKey.toString('hex'));
    });
  });
}
```

---

## 2. Offloading CPU-Bound Work with `worker_threads`

For CPU-heavy tasks (image resizing, video compression, PDF generation, cryptographic heavy math), offload to a worker thread:

```typescript
// worker-runner.ts
import { Worker } from 'node:worker_threads';

export function runWorkerTask<TInput, TOutput>(workerScript: string, data: TInput): Promise<TOutput> {
  return new Promise((resolve, reject) => {
    const worker = new Worker(workerScript, { workerData: data });
    worker.on('message', resolve);
    worker.on('error', reject);
    worker.on('exit', (code) => {
      if (code !== 0) reject(new Error(`Worker stopped with exit code ${code}`));
    });
  });
}
```

---

## 3. Streams & Backpressure Management

Loading multi-gigabyte or even 100MB+ files entirely into a RAM `Buffer` causes severe heap pressure, high GC pause times, and potential OOM crashes.

```typescript
// ❌ ANTI-PATTERN: Buffering entire 1GB file into RAM
import fs from 'node:fs/promises';

export async function exportCsv(filePath: string, res: Response) {
  const fileBuffer = await fs.readFile(filePath); // Spikes RAM by 1GB!
  res.send(fileBuffer);
}

// ✅ BEST PRACTICE: Stream with backpressure handling using pipeline()
import { createReadStream } from 'node:fs';
import { pipeline } from 'node:stream/promises';

export async function exportCsv(filePath: string, responseWritable: NodeJS.WritableStream) {
  const sourceStream = createReadStream(filePath);
  // pipeline handles errors, closes streams properly, and respects backpressure
  await pipeline(sourceStream, responseWritable);
}
```

