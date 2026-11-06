# Code Reviewer Reference Guide

Advanced code review strategies, cognitive heuristics, and language-specific checklist matrices.

---

## 1. Review Heuristics & Methodologies

A senior code reviewer approaches code with a specific lens:

1. **Verify the Problem First**:
   - Before reading single lines of code, read the user requirements or issue description.
   - Ask: "Does this patch solve the problem it claims to solve?"
2. **Review Tests Before Implementation**:
   - Inspect the test file first. Do the tests prove the new behavior? Do they fail when the behavior is broken?
   - If tests only cover the golden path, flag missing edge cases immediately.
3. **Trace the Data Flow**:
   - Follow external inputs from entrypoint (HTTP controller / CLI command) down to database/disk and back.
   - Look for missing sanitization, unvalidated type casts, and state mutations.
4. **Assume Unhappy Paths**:
   - What happens when network disconnects?
   - What happens if the database returns 0 rows?
   - What happens if disk is full?
   - What happens if concurrent requests arrive with the same ID?

---

## 2. Language-Specific Review Checklist Matrices

### Python Reviews
- **Typing:** Are return types annotated? Are `Optional[T]` or `T | None` used where `None` can be returned?
- **Collections & Caching:** Are dict lookups using `.get()` or catching `KeyError`? Are `@functools.lru_cache` calls bounded with an explicit `maxsize`?
- **Async & Event Loop:** Is `asyncio.sleep()` called instead of blocking `time.sleep()`? Are CPU-bound or sync operations offloaded with `asyncio.to_thread()`?
- **Resource Cleanup:** Are file handles, sockets, and database sessions managed in `with` / `async with` blocks?
- **Closures & Scope:** Are default arguments immutable (no `target=[]` or `target={}`)? Are loop variables in closures bound at definition time (`lambda i=i: i`)?
- **Memory & References:** Are circular references avoided or decoupled via `weakref`? Are generators (`yield`) used for large dataset iteration?

### TypeScript / JavaScript Reviews
- **Strict Typing:** Is `any` used? (Flag as P1). Is `as Type` force-casting without validation?
- **Equality:** Is `===` used instead of `==`?
- **Async & Concurrency:** Are promises awaited or chained? Are there unhandled floating promises? Is `Promise.all` bounded using concurrency throttling (`p-limit`)?
- **Nullish Coalescing:** Is `??` used where falsy values like `0` or `""` are legitimate?
- **Closure & Scope Hygiene:** Do callbacks or event handlers accidentally retain large outer objects or request contexts?
- **Memory & Resource Hygiene:** Are event listeners, intervals, and observers cleaned up (using `AbortSignal`, `.off()`, or `clearInterval`)? Are caches bounded (LRU) rather than unbounded `Map`/`Set`? Are large files streamed rather than buffered in RAM?

### Java Reviews
- **Null Safety:** Are `Optional<T>` methods used properly without blind `.get()` calls?
- **Immutability:** Are DTOs using Java Records (`record User(...)`)?
- **Streams & Memory:** Are stream operations side-effect free? Are large result sets streamed / paginated rather than collected into large heap lists?
- **Memory Leaks:** Are static collections bounded? Are `ThreadLocal` variables cleared in `finally` blocks? Are non-static inner classes avoiding unintended outer reference retention?
- **Concurrency:** Are threads pinned on carrier threads in Virtual Threads (e.g. `synchronized` blocks doing I/O)?
- **Transactions & Resources:** Are `@Transactional` methods public and called from outside the class instance? Are all `AutoCloseable` resources managed in `try-with-resources`?

---

## 3. Review Comment Principles
- **Be Specific:** Always point to the file, line number, and concrete mechanism.
- **Explain the "Why":** Explain the technical reason, performance implication, or bug risk.
- **Provide Drop-In Solutions:** Include a concise diff whenever possible.
- **Distinguish Requirements from Suggestions:** Always prefix comments with `[P0]`, `[P1]`, `[P2]`, or `[P3 - Nit]`.
