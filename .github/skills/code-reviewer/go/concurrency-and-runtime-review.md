# Go Concurrency, Channels & Runtime Review Guide

Audit guide for Go goroutines, channels, synchronization, and runtime memory hygiene.

---

## 1. Context Propagation & Cancellation

- [ ] **Context First Parameter**:
  - Is `ctx context.Context` the first parameter of any function performing I/O, network requests, or long-running computations?
- [ ] **Context Cancellation Check**:
  - Do long-running loops or worker pools check `ctx.Done()` or `ctx.Err()` to abort when canceled?
- [ ] **Context Value Abuse**:
  - Are domain objects or required function arguments passed via `context.WithValue`?
  - `context.Value` must only be used for request-scoped metadata (request ID, tracing span, authenticated user ID).

---

## 2. Goroutine Leaks & Lifecycle

- [ ] **Guaranteed Termination**:
  - Does every spawned goroutine (`go func() { ... }()`) have a deterministic, guaranteed termination path?
  - If a goroutine is blocked reading from an unbuffered channel or waiting on a lock that never releases, it leaks memory forever.
- [ ] **`sync.WaitGroup` & ErrGroup**:
  - When coordinating concurrent workers, is `sync.WaitGroup` or `golang.org/x/sync/errgroup` used rather than arbitrary sleeps?
  - Is `wg.Add(1)` called **before** launching the goroutine (outside the `go func`)?

---

## 3. Channels & Synchronization

- [ ] **Closing Channels**:
  - Is a channel closed only by the sender, never by the receiver? Closing already closed channels causes runtime panics.
- [ ] **Buffered vs. Unbuffered Channels**:
  - Does unbuffered channel communication have a concurrent receiver ready, or does it cause goroutine deadlocks?
- [ ] **Mutex Hygiene**:
  - Is `mu.Unlock()` called immediately with `defer mu.Unlock()` right after `mu.Lock()`?
  - Is `sync.RWMutex` used when reads vastly outnumber writes?

---

## 4. Resource Management & Memory

- [ ] **`defer` Inside Loops**:
  - Are `defer file.Close()` calls placed inside large loops?
  - Defers are only executed when the outer function returns, not when the loop iteration ends. This exhausts file descriptors.
  - **Resolution**: Wrap the loop body in a helper function or close explicitly.
- [ ] **`sync.Pool` for High-Throughput Buffers**:
  - Are temporary byte buffers pooled using `sync.Pool` in hot network/serialization paths to reduce GC pressure?
