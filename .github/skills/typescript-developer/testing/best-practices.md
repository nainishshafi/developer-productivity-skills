# TypeScript Testing & Quality Best Practices

Strategies for writing fast, deterministic, maintainable tests in modern TypeScript (Vitest / Jest).

## Typechecking test source and mocking Node APIs

- Inspect the test command and TypeScript project coverage separately. Runners such as `tsx` transpile without typechecking; a production `tsconfig.json` may exclude tests. Passing runtime tests and production `tsc` then leave test-source diagnostics unchecked.
- Use the existing test TypeScript project when available. Otherwise run the installed compiler against affected tests with explicit options matching the project's target, module resolution, strictness and interop. For a strict ES2022 NodeNext project:
  ```powershell
  node node_modules/typescript/bin/tsc --noEmit --target ES2022 --module NodeNext --moduleResolution NodeNext --strict --esModuleInterop --skipLibCheck tests/example.test.ts
  ```
  Replace the example path with affected tests. Require exit code 0 and no diagnostics; this focused command does not inherit project aliases or other omitted options.
- Prefer the runner's native mock/spy API over assignment to imported module members. A Node member such as `fs.lstatSync` can be readonly in TypeScript declarations even when writable at runtime. With `node:test`, use `t.mock.method` and restore through the mock API in cleanup or `finally`. Verify the target is mockable for the actual module format; do not cast away readonly errors to force assignment.

---

## 1. Testing Pyramid & Boundaries

- **Pure Domain Unit Tests (70%)**: Test business logic and entities in-memory. Zero network, zero database, zero file I/O. Extremely fast (sub-millisecond).
- **Integration Tests (20%)**: Test persistence adapters and external clients against real or containerized services (e.g. `testcontainers` with real PostgreSQL / Redis).
- **End-to-End Contract Tests (10%)**: Test HTTP endpoints and full request pipelines using `supertest` or HTTP clients against the real application instance.

---

## 2. In-Memory Mocking of Port Interfaces

Because application services depend on interface ports (Dependency Inversion), unit testing requires zero heavy mocking frameworks:

```typescript
// tests/mocks/in-memory-user-repository.ts
import { UserRepositoryPort } from '../../src/core/ports/user-repository.port';
import { User } from '../../src/core/domain/user.entity';

export class InMemoryUserRepository implements UserRepositoryPort {
  private users = new Map<string, User>();

  async findById(id: string): Promise<User | null> {
    return this.users.get(id) ?? null;
  }

  async save(user: User): Promise<void> {
    this.users.set(user.id, user);
  }
}
```

---

## 3. Fake Timers for Time-Dependent Logic

Never use `setTimeout` or `await new Promise(r => setTimeout(r, 1000))` in unit tests. Use fake timers:

```typescript
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';

describe('TokenExpiryService', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('marks token expired after TTL passes', () => {
    const service = new TokenExpiryService();
    service.createToken('token-123', 60_000); // 1 minute

    vi.advanceTimersByTime(61_000);

    expect(service.isExpired('token-123')).toBe(true);
  });
});
```
