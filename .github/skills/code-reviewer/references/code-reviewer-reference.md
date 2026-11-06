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
- **Collections:** Are dict lookups using `.get()` with defaults or catching `KeyError`?
- **Async:** Is `asyncio.sleep()` called instead of blocking `time.sleep()`?
- **Resource Cleanup:** Are file handles and database sessions managed in `with` blocks?
- **Mutable Defaults:** Are there functions with `def append_item(item, target=[])`? (Flag as P0 bug).

### TypeScript / JavaScript Reviews
- **Strict Typing:** Is `any` used? (Flag as P1). Is `as Type` force-casting without validation?
- **Equality:** Is `===` used instead of `==`?
- **Async:** Are promises awaited or chained? Are there unhandled floating promises?
- **Nullish Coalescing:** Is `??` used where falsy values like `0` or `""` are legitimate?
- **Memory:** Are event listeners and timeouts cleaned up on component unmount / process exit?

### Java Reviews
- **Null Safety:** Are `Optional<T>` methods used properly without blind `.get()` calls?
- **Immutability:** Are DTOs using Java Records (`record User(...)`)?
- **Streams:** Are stream operations side-effect free?
- **Concurrency:** Are threads pinned on carrier threads in Virtual Threads (e.g. `synchronized` blocks doing I/O)?
- **Transactions:** Are `@Transactional` methods public and called from outside the class instance?

---

## 3. Review Comment Principles
- **Be Specific:** Always point to the file, line number, and concrete mechanism.
- **Explain the "Why":** Explain the technical reason, performance implication, or bug risk.
- **Provide Drop-In Solutions:** Include a concise diff whenever possible.
- **Distinguish Requirements from Suggestions:** Always prefix comments with `[P0]`, `[P1]`, `[P2]`, or `[P3 - Nit]`.
