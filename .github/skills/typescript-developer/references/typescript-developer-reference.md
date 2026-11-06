# TypeScript Developer Architectural Reference Guide

Deep-dive patterns, architectural trade-offs, and reference implementations for TypeScript / Node.js codebases.

---

## 1. Architectural Style Comparison Matrix

| Architecture Style | Ideal When | Drawbacks / Risks | TypeScript Implementation Mechanism |
|---|---|---|---|
| **Layered / MVC** | Standard REST APIs, Express/Fastify apps, fast developer onboarding. | Easy for controllers to bloat; leaky abstractions if ORM models leak into HTTP responses. | `routes/` -> `controllers/` -> `services/` -> `repositories/` -> `models/`. |
| **Modular / Feature-Based** | Medium to large apps, NestJS projects, teams owning separate domain modules. | Module boundaries require discipline to avoid circular dependencies. | `modules/<feature>/` encapsulating all domain files, schemas, and routes. |
| **Hexagonal (Ports & Adapters)** | Rich business logic, high automated test requirement, decoupled from database choice. | Boilerplate mapping between domain entities and persistence/ORM models. | Interface Ports (`src/core/ports/`); concrete adapters (`src/infra/adapters/`). |
| **Functional / Service Functions** | Serverless functions (AWS Lambda), Next.js Server Actions, light microservices. | Less suitable when complex stateful domain transactions span multiple entities. | Pure exported functions, closures for dependency injection, `Result` types. |

---

## 2. Implementing Ports & Adapters in TypeScript

### The Domain & Port (Pure TypeScript)
```typescript
// core/domain/user.ts
export interface User {
  readonly id: string;
  readonly email: string;
  readonly role: 'ADMIN' | 'MEMBER';
  readonly isActive: boolean;
}

export function canPromoteToAdmin(user: User): boolean {
  return user.isActive && user.role !== 'ADMIN';
}

// core/ports/user-repository.port.ts
import { User } from '../domain/user';

export interface UserRepositoryPort {
  findById(id: string): Promise<User | null>;
  save(user: User): Promise<void>;
}
```

### The Application Use Case
```typescript
// application/promote-user.use-case.ts
import { UserRepositoryPort } from '../core/ports/user-repository.port';
import { canPromoteToAdmin, User } from '../core/domain/user';

export class PromoteUserUseCase {
  constructor(private readonly userRepo: UserRepositoryPort) {}

  async execute(userId: string): Promise<User> {
    const user = await this.userRepo.findById(userId);
    if (!user) {
      throw new Error(`User with ID ${userId} not found`);
    }

    if (!canPromoteToAdmin(user)) {
      throw new Error('User cannot be promoted to admin');
    }

    const updatedUser: User = { ...user, role: 'ADMIN' };
    await this.userRepo.save(updatedUser);
    return updatedUser;
  }
}
```

### The Infrastructure Adapter (e.g. Prisma or Drizzle)
```typescript
// infra/adapters/prisma-user-repository.ts
import { PrismaClient } from '@prisma/client';
import { UserRepositoryPort } from '../../core/ports/user-repository.port';
import { User } from '../../core/domain/user';

export class PrismaUserRepository implements UserRepositoryPort {
  constructor(private readonly prisma: PrismaClient) {}

  async findById(id: string): Promise<User | null> {
    const record = await this.prisma.user.findUnique({ where: { id } });
    if (!record) return null;
    return {
      id: record.id,
      email: record.email,
      role: record.role as 'ADMIN' | 'MEMBER',
      isActive: record.isActive,
    };
  }

  async save(user: User): Promise<void> {
    await this.prisma.user.upsert({
      where: { id: user.id },
      update: { role: user.role, isActive: user.isActive },
      create: { id: user.id, email: user.email, role: user.role, isActive: user.isActive },
    });
  }
}
```

---

## 3. Functional Dependency Injection Pattern

For codebases preferring functional composition over classes:

```typescript
export interface Dependencies {
  findUserById: (id: string) => Promise<User | null>;
  saveUser: (user: User) => Promise<void>;
}

export function createPromoteUserHandler(deps: Dependencies) {
  return async function promoteUser(userId: string): Promise<User> {
    const user = await deps.findUserById(userId);
    if (!user) throw new Error('User not found');
    const updated = { ...user, role: 'ADMIN' as const };
    await deps.saveUser(updated);
    return updated;
  };
}
```

---

## 4. Discovery Guide for LLMs

When analyzing an existing TypeScript codebase:

```typescript
// 1. Check package.json:
// - Check for "type": "module" -> Use ESM import/export with .js extensions if required.
// - Look for framework: @nestjs/core, express, fastify, next.
// - Look for ORM: @prisma/client, drizzle-orm, typeorm.

// 2. Check directory layout:
// - If NestJS modules exist: write standard Nest controllers and @Injectable() providers.
// - If src/routes exists: write standard route handlers matching existing style.
// - If Zod is present: write schema validation matching existing schema naming.
```
