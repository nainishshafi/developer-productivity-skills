# TypeScript Architectural Styles & Discovery

Guidance on identifying, choosing, and implementing architectural patterns in modern TypeScript and Node.js applications.

---

## 1. Architectural Style Comparison Matrix

| Architecture Style | Ideal When | Drawbacks / Risks | TypeScript Implementation Pattern |
|---|---|---|---|
| **Layered / MVC** | Standard REST APIs, Express/Fastify backends, rapid MVP development. | Controllers tend to bloat; risk of ORM models leaking into HTTP responses. | `routes/` -> `controllers/` -> `services/` -> `repositories/` -> `models/`. |
| **Modular / Feature-Based** | Medium to large applications, NestJS projects, domain teams. | Boundary discipline required to avoid circular dependencies across modules. | `modules/<feature>/` containing controllers, services, repositories, and schemas. |
| **Hexagonal (Ports & Adapters)** | Complex domain logic, high automated test requirement, decoupled from DB/ORM. | Mapping boilerplate between domain entities and persistence/DTO models. | Core Ports (`core/ports/`); concrete adapters (`infra/adapters/`); pure domain. |
| **Functional / Service Functions** | Serverless functions (AWS Lambda), Next.js Server Actions, lightweight APIs. | Less suitable for complex entity state transitions across multiple aggregate roots. | Pure exported functions, closures/parameter objects for DI, `Result` types. |

---

## 2. Implementing Ports & Adapters (Clean Architecture)

### A. The Domain & Port (Pure TypeScript, Zero Frameworks)
```typescript
// core/domain/user.entity.ts
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
import { User } from '../domain/user.entity';

export interface UserRepositoryPort {
  findById(id: string): Promise<User | null>;
  save(user: User): Promise<void>;
}
```

### B. The Application Use Case (Coordinates Business Logic)
```typescript
// application/promote-user.use-case.ts
import { UserRepositoryPort } from '../core/ports/user-repository.port';
import { canPromoteToAdmin, User } from '../core/domain/user.entity';

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

### C. The Infrastructure Adapter (Prisma / Drizzle / TypeORM)
```typescript
// infra/adapters/prisma-user-repository.ts
import { PrismaClient } from '@prisma/client';
import { UserRepositoryPort } from '../../core/ports/user-repository.port';
import { User } from '../../core/domain/user.entity';

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

## 3. Directory Layouts

### Feature-Based Modular Layout
```text
src/
├── modules/
│   ├── auth/
│   │   ├── auth.controller.ts  # Presentation (HTTP/REST)
│   │   ├── auth.service.ts     # Application Use Case
│   │   ├── auth.repository.ts  # Persistence Adapter
│   │   ├── auth.schemas.ts     # Validation schemas (Zod/Valibot)
│   │   └── auth.types.ts       # Domain types & interfaces
│   └── billing/
└── shared/
    ├── database/               # Shared DB client & connection pool
    └── errors/                 # Domain & HTTP error hierarchies
```

---

## 4. Discovery Guide for Codebases

When inspecting an unfamiliar codebase:
1. **Module System**: Check `package.json` for `"type": "module"`. If ESM, ensure `.js` extensions are used in imports when required by `tsconfig.json` (`NodeNext` / `Node16`).
2. **Framework Alignment**:
   - NestJS (`@nestjs/core`) -> Use decorators, modules, and class-based providers.
   - Express / Fastify -> Use functional middleware, typed route handlers, and schema validation hooks.
3. **ORM / Persistence**:
   - Prisma (`prisma`) -> Map Prisma models to domain interfaces at repository boundaries.
   - Drizzle (`drizzle-orm`) -> Use schema inference and typed relational queries.

