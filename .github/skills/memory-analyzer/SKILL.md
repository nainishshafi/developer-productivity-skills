---
name: memory-analyzer
description: Analyze memory risks across languages. Use for OOM, stack overflow, memory leaks, unbounded collections or buffers, and high peak memory usage.
version: 1.1.0
---

# Memory Analyzer (Language-Independent)

Perform a systematic, language-independent analysis of code to detect and prevent
**Out-of-Memory (OOM)** errors, **Stack Overflow** crashes, **memory leaks**,
and **unbounded heap/stack growth**.

---

## Analysis Workflow

### 1. Establish Scope & Constraints
Before scanning code, identify:
- **Execution model**: One-shot CLI/script vs. long-running daemon/server/event-loop/tick-handler.
- **Hot paths & entry points**: Loops, request/message handlers, `OnTick`/`OnCalculate`, stream processors, and recursive functions.
- **Memory boundaries**: Expected max input sizes, concurrency limits, container/process RAM limits, and call-stack size limits.

---

### 2. Stack Overflow Analysis (Call Stack & Frame Size)

Inspect for anything that can exhaust the thread or process call stack:

1. **Unbounded or Input-Controlled Recursion**
   - Direct or mutual/indirect recursion where depth scales with input size, tree/graph depth, or external data rather than a small constant bound.
   - Missing, unreachable, or non-converging base cases.
   - Graph/tree traversal without visited tracking (cycles cause infinite recursion).
   - **Fix**: Convert to an explicit heap-allocated stack/queue (iterative traversal), or enforce an explicit `max_depth` guard.

2. **Oversized Stack Frames**
   - Large fixed-size local arrays, structs, or buffers allocated on the stack inside functions (especially recursive or deeply nested ones).
   - Dynamic stack allocations (`alloca`, variable-length arrays) driven by untrusted or large sizes.
   - **Fix**: Allocate large buffers on the heap, reuse a preallocated scratch buffer, or pass by reference/slice.

3. **Re-entrant / Cascading Call Chains**
   - Event emitters, observers, signal handlers, or callbacks that synchronously trigger themselves or re-enter the same handler.
   - **Fix**: Defer re-entrant work to an event queue / trampoline, or guard with a re-entrancy flag.

---

### 3. OOM & Unbounded Heap Growth Analysis

Inspect for patterns that cause heap exhaustion or severe memory spikes:

1. **Unbounded Collections, Caches & Buffers**
   - Lists, maps, sets, queues, logs, or memoization tables that grow on every request/tick/message without eviction, TTL, or a hard capacity cap (`max_size`).
   - **Fix**: Use bounded ring buffers, LRU/TTL caches, or periodic compaction/pruning.

2. **Full-Payload Buffering Instead of Streaming**
   - Reading entire files, HTTP bodies, database query results, or IPC payloads into memory at once (`read_all`, `fetchall`, loading full history arrays).
   - A bounded sample or final output does not bound upstream loading. Trace full-corpus queries, source-text payloads, intermediate copies and retained rows through the workflow before claiming memory depends only on sample size.
   - **Fix**: Stream in fixed-size chunks, paginate queries, or process line-by-line / record-by-record.

3. **Unbounded Concurrency / Fan-Out**
   - Spawning tasks, threads, goroutines, or async futures per item in an unbounded loop without a semaphore, worker pool, or backpressure.
   - **Fix**: Bound concurrency with a worker pool / semaphore and apply backpressure to producers.

4. **Quadratic Allocation & Copy Spikes**
   - Repeated concatenation of immutable strings, arrays, or byte buffers inside loops.
   - Deep-copying large objects/arrays on every iteration or function call instead of passing views/references.
   - **Fix**: Use a mutable builder/buffer with preallocated capacity, or pass read-only views/references.

5. **Retained References & Hidden Leaks**
   - **Closures / lambdas**: Capturing large outer-scope objects or buffers that outlive their need.
   - **Subscriptions / registries**: Event listeners, timers, or global maps where items are registered but never removed on cleanup/error paths.
   - **Slicing / sub-views**: Keeping a small slice/substring that pins a huge backing array/buffer in memory.
   - **Circular references**: Reference cycles in reference-counted runtimes without weak references.
   - **Manual / native / handle leaks**: Heap allocations, file/socket handles, FFI buffers, or platform handles (e.g., indicators, graphic objects, DB cursors) missing deterministic release on all exit/error paths.

---

### 4. Dynamic Verification (When Code Can Be Executed)

If tests or a runtime environment are available, verify empirically:
1. **Steady-State Leak Check**: Run the hot path or handler for $N$ iterations (e.g., 1,000 -> 10,000 -> 50,000) and verify resident memory (RSS) / heap stabilizes ($O(1)$ growth) rather than rising monotonically.
2. **Peak Memory / Large Input Check**: Feed worst-case or oversized inputs (deeply nested structures, large files, high concurrency) under a constrained memory/stack limit to confirm graceful bounding or streaming.

---

### 5. Output Format

Present findings ordered by severity (`Critical` -> `High` -> `Medium` -> `Low`). For each finding, report:

- **Severity & Category**: e.g., `[Critical] Stack Overflow` or `[High] Unbounded Heap Growth`
- **Location**: `file_path:line` and symbol/function name
- **Mechanism**: Why memory or stack grows (include growth order, e.g., $O(N)$ per tick, $O(D)$ stack frames)
- **Trigger**: Specific input, duration, or state that causes OOM or stack overflow
- **Remediation**: Concrete, minimal code change to bound memory/stack usage

If no issues are found in a category, explicitly state what was checked and why it is bounded.

---

## Quick Review Checklist
- [ ] All recursion has a guaranteed, small bounded depth (or is iterative).
- [ ] No large buffers/arrays are allocated on the call stack.
- [ ] All caches, queues, and history buffers have explicit size/TTL limits.
- [ ] Large files, streams, and query results are processed in bounded chunks.
- [ ] Concurrency/fan-out has bounded worker/queue limits and backpressure.
- [ ] Subscriptions, timers, closures, and native/manual handles are released on all paths (including errors).
