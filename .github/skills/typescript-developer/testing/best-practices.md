# TypeScript Testing & Quality Best Practices

Strategies for writing fast, deterministic, maintainable tests in modern TypeScript (Vitest / Jest).

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

