# TypeScript & Node.js Runtime & Memory Review Guide

Audit guide for Node.js backend runtimes, memory management, and event loop hygiene.

---

## 1. Event Loop Protection

- [ ] **Synchronous File System I/O**:
  - Are `fs.readFileSync()`, `fs.writeFileSync()`, or `fs.existsSync()` called in request paths? Flag as `[P0 - Blocker]`.
  - **Resolution**: Use `fs/promises` (`await fs.readFile()`, `await fs.writeFile()`).
- [ ] **CPU-Intensive Tasks**:
  - Are large JSON parsing operations, cryptographic operations, or recursive graph traversals blocking the main thread?
  - **Resolution**: Offload to `worker_threads` or stream chunked processing using `setImmediate()`.
- [ ] **Synchronous Regex ReDoS**:
  - Are regex patterns vulnerable to catastrophic backtracking when evaluating user inputs?

---

## 2. Memory Leak Prevention

- [ ] **Dangling Event Listeners**:
  - Are event listeners registered on long-lived emitters (`process`, WebSocket servers, event buses) without removal?
  - **Resolution**: Always unregister using `.removeListener()` / `.off()`, or pass `{ signal: abortController.signal }` to automatically unregister.
- [ ] **Unbounded Caches**:
  - Are module-level `Map` or `Set` objects storing unbounded entries without eviction or size caps?
  - **Resolution**: Use bounded LRU caches (e.g. `lru-cache`) with explicit `max` and `ttl`.
- [ ] **Closure Memory Retention**:
  - Do inner functions or callbacks retain outer scope variables containing large objects or entire HTTP request contexts?

---

## 3. Streams & Buffers

- [ ] **Buffer vs. Stream**:
  - Are large file uploads, downloads, or database exports buffered in memory (`Buffer.concat()`)?
  - **Resolution**: Pipe using Node.js streams (`stream.pipeline(readStream, transformStream, writeStream)`).
- [ ] **Stream Error Handling**:
  - Are stream pipelines using `pipeline` from `stream/promises` to guarantee automatic cleanup on failure?

---

## 4. Process & Signal Hygiene

- [ ] **Graceful Shutdown**:
  - Does the service listen for `SIGTERM` and `SIGINT` to close active HTTP servers, drain queues, and close database connection pools?
- [ ] **Unhandled Rejections**:
  - Does the process configure `process.on('unhandledRejection', ...)` and `process.on('uncaughtException', ...)`?
