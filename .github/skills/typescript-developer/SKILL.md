---
name: typescript-developer
description: Architectural and engineering guidance for modern TypeScript and JavaScript development (Node.js, ES2023+, TS 5+). Helps the LLM analyze existing project architecture, adapt to codebase conventions, and apply clean architecture, domain modeling, and testing patterns pragmatically without imposing dogmatic hard rules. Use when designing, writing, reviewing, or refactoring TypeScript/JavaScript code, or when the user asks to "write typescript code", "develop typescript service", "typescript architecture best practices", "design node backend", or "refactor javascript".
version: 1.1.0
---

# TypeScript Developer Skill

An architectural guidance framework for modern TypeScript and JavaScript (Node.js 20+, TS 5+). This skill is **not an inflexible rulebook**; it guides the LLM to inspect, discover, and adapt to the project's existing architecture while applying solid software architecture principles.

---

## 1. Adaptive Architectural Discovery (Find First, Then Align)

Before generating or modifying TypeScript/JavaScript code, the LLM must **inspect the project context**:

1. **Detect Toolchain & Runtime Baseline**:
   - Check `package.json`, `tsconfig.json`, and lockfiles (`pnpm-lock.yaml`, `package-lock.json`, `yarn.lock`).
   - Identify module system: ESM (`"type": "module"`) or CommonJS?
   - Identify TypeScript strictness: `strict: true`, `noImplicitAny: true`, etc.
   - Never introduce dependencies, syntax, or module formats that conflict with the existing project configuration.
2. **Identify the Architecture Style**:
   - **Layered / MVC** (`controllers/` -> `services/` -> `repositories/` -> `models/`): Common in Express, Koa, and Fastify backends.
   - **Modular / Feature-Based** (`modules/<feature>/` containing controllers, services, entities, and tests): Common in NestJS and scalable enterprise services.
   - **Vertical Slice / Next.js Fullstack** (`app/api/`, `components/`, `actions/`): Common in App Router and React Server Component apps.
   - **Hexagonal / Clean Architecture** (`core/domain/`, `core/use-cases/`, `infrastructure/`): Common in domain-heavy backends.
   - *Rule:* Align with the existing structure. Do not impose heavy enterprise classes on a clean functional Express service, and do not bypass NestJS dependency injection in a NestJS codebase.
3. **Assess Conventions & Libraries**:
   - Framework: Express, Fastify, NestJS, Next.js, Remix, Hono, or Electron?
   - Persistence / ORM: Prisma, Drizzle, TypeORM, Kysely, MikroORM, or raw SQL?
   - Validation / Schema: Zod, Valibot, Yup, Joi, or class-validator?
   - Testing: Vitest, Jest, Mocha, or Playwright?

---

## 2. Core Architectural Principles in TypeScript

### A. Separation of Concerns & Boundary Defense
- **Domain Layer (Core)**: Pure business types, domain models, state machines, and business invariants. Keep it independent of frameworks, HTTP headers, and ORM decorators where feasible.
- **Application Layer (Use Cases)**: Coordinates business workflows, transactions, and domain events. Calls outbound ports/interfaces.
- **Infrastructure Layer (Adapters)**: Implements database queries, third-party API clients, message publishers, and cache managers.
- **Presentation Layer (Interfaces)**: HTTP routes, controllers, CLI commands, or tRPC routers. Validates request schemas and translates results into HTTP responses.

### B. Dependency Inversion via Interfaces
Use TypeScript interfaces to decouple application services from external infrastructure:

```typescript
// Core interface (Port)
export interface EmailSender {
  send(to: string, subject: string, bodyHtml: string): Promise<void>;
}

// Service depends on the interface, not on SendGrid / Resend directly
export class NotificationService {
  constructor(private readonly emailSender: EmailSender) {}

  async notifyUserWelcome(email: string): Promise<void> {
    await this.emailSender.send(email, 'Welcome!', '<p>Welcome to our app</p>');
  }
}
```

### C. Type-Driven Modeling (Make Illegal States Unrepresentable)
- Use **Discriminated Unions** to represent domain states instead of optional fields and boolean flags:
  ```typescript
  // Prefer explicit state variants:
  export type Payment =
    | { status: 'PENDING'; paymentId: string; createdAt: Date }
    | { status: 'AUTHORIZED'; paymentId: string; authCode: string }
    | { status: 'FAILED'; paymentId: string; failureReason: string };
  ```
- Use `as const` and literal unions for fixed domain constants instead of raw strings.
- Separate internal Domain Types from external DTOs (Data Transfer Objects) to avoid coupling domain models directly to public API shapes.

### D. Error Architecture & Resilience
- Distinguish between **Expected Operational Errors** (invalid input, resource not found) and **Programmer Defects / System Crashes** (null dereference, database unreachable).
- For expected domain errors, prefer typed `Result<T, E>` returns or custom typed domain exceptions over throwing un-typed strings.
- Always implement timeout and cancellation support via `AbortController` / `AbortSignal` for outbound HTTP requests and database operations.

---

## 3. Practical Architecture Patterns

### Pattern 1: Feature-Based Modular Architecture
```text
src/
├── modules/
│   ├── auth/
│   │   ├── auth.controller.ts  # Presentation
│   │   ├── auth.service.ts     # Application / Use Case
│   │   ├── auth.repository.ts  # Persistence
│   │   ├── auth.schemas.ts     # Validation schemas (Zod / Valibot)
│   │   └── auth.types.ts       # Domain types & interfaces
│   └── billing/
└── shared/
    ├── database/               # Shared DB connection pool / ORM client
    └── errors/                 # Standard application error hierarchy
```

### Pattern 2: Hexagonal / Clean Architecture (Domain-Driven)
```text
src/
├── core/
│   ├── domain/                 # Pure domain entities, value objects, domain events
│   └── ports/                  # Inbound and outbound interfaces
├── application/                # Use case interactor services
├── infrastructure/             # Concrete ORM repositories, external API adapters
└── presentation/               # Express/Fastify routes or NestJS controllers
```

---

## 4. Architectural Pragmatism (Avoid Over-Engineering)

- **Do Not Dogmatically Impose Class Hierarchies**: TypeScript supports both object-oriented and functional paradigms. If the existing codebase uses pure functions and closures for dependency injection, follow that functional style. If it uses NestJS classes and decorators, use classes.
- **Honor Project Simplicity**: For small microservices or CLI utilities, a 2-tier architecture (handlers + db client) is often superior to a 4-tier clean architecture abstraction.
- **Match Existing Testing Patterns**: If the project uses in-memory mocking, follow that; if it uses real testcontainers or SQLite in-memory for testing, align with the existing test infrastructure.

---

## References

- [TypeScript Developer Reference Guide](file:///.github/skills/typescript-developer/references/typescript-developer-reference.md) — Architecture implementations, dependency injection styles, and testing patterns.
