# TypeScript Design Patterns & Dependency Injection Architecture

Comprehensive architectural guide to Dependency Injection (DI) and Modern Design Patterns in TypeScript and Node.js (TS 5+, NestJS, and pure TypeScript).

---

## 1. Dependency Injection Patterns in TypeScript

In TypeScript, Dependency Injection ranges from zero-dependency **Pure DI** (composition root) to full enterprise **IoC containers** (NestJS, TSyringe, InversifyJS).

### 1.1 Pure Dependency Injection (Functional & Class Composition Root)
In modern Node.js/TypeScript, you often do not need a heavyweight reflection container. Wiring dependencies manually in an application **Composition Root** provides maximum type safety, zero runtime overhead, and instant debugging.

#### Approach A: Interface Constructor Injection
```typescript
// 1. Dependency Abstractions (Contracts)
export interface UserRepository {
  findById(id: string): Promise<User | null>;
  save(user: User): Promise<void>;
}

export interface EmailGateway {
  sendWelcomeEmail(email: string): Promise<void>;
}

// 2. Class Consuming Injected Dependencies
export class UserService {
  constructor(
    private readonly userRepo: UserRepository,
    private readonly emailGateway: EmailGateway
  ) {}

  async registerUser(email: string): Promise<User> {
    const user = new User(crypto.randomUUID(), email);
    await this.userRepo.save(user);
    await this.emailGateway.sendWelcomeEmail(email);
    return user;
  }
}

// 3. Composition Root (index.ts / server.ts)
const dbPool = new DatabasePool(process.env.DATABASE_URL!);
const userRepo = new PostgresUserRepository(dbPool);
const emailGateway = new SendgridEmailGateway(process.env.SENDGRID_API_KEY!);

// Single composition wiring point:
const userService = new UserService(userRepo, emailGateway);
```

#### Approach B: Functional Dependency Injection (Factory Closures)
In functional codebases, inject dependencies via higher-order functions:
```typescript
export interface UserDeps {
  db: DatabaseClient;
  mailer: MailerClient;
}

export const createRegisterUserHandler = (deps: UserDeps) => async (email: string) => {
  const user = await deps.db.insertUser({ email });
  await deps.mailer.sendWelcome(email);
  return user;
};
```

---

### 1.2 Enterprise IoC in NestJS

NestJS provides an Angular-style Dependency Injection container built on decorators and metadata.

#### Injection Styles & Custom Providers
```typescript
import { Injectable, Inject } from '@nestjs/common';

// 1. Class Injection
@Injectable()
export class OrderService {
  constructor(
    private readonly paymentGateway: StripePaymentGateway,
    @Inject('CONFIG_OPTIONS') private readonly options: AppOptions // Custom symbol/string token
  ) {}
}

// 2. Custom Provider Definition in Nest Module
@Module({
  providers: [
    OrderService,
    // Value Provider
    {
      provide: 'CONFIG_OPTIONS',
      useValue: { timeoutMs: 5000, retryAttempts: 3 },
    },
    // Factory Provider with Async Initialization
    {
      provide: 'REDIS_CLIENT',
      useFactory: async (config: ConfigService) => {
        const client = createRedisClient(config.get('REDIS_URL'));
        await client.connect();
        return client;
      },
      inject: [ConfigService],
    },
  ],
})
export class OrderModule {}
```

#### NestJS Provider Scopes & Captive Pitfalls

| Scope | Behavior | Performance Impact |
| :--- | :--- | :--- |
| **`Scope.DEFAULT` (Singleton)** | One instance shared across entire app. | **Highest performance**. Default choice. |
| **`Scope.REQUEST`** | New instance created for every incoming HTTP request. | **High GC overhead**: Creating trees of beans per request drops RPS throughput. |
| **`Scope.TRANSIENT`** | New instance created for every consumer that injects it. | Useful for stateful lightweight utilities. |

> **Captive Dependency Gotcha in NestJS**:
> Injecting a `Scope.REQUEST` provider into a `Scope.DEFAULT` (Singleton) service automatically turns the Singleton into a Request-scoped service, recursively bubbling up the tree! Keep Request scope limited strictly to leaf components.

#### Resolving Circular Dependencies with `forwardRef`
When Service A depends on Service B, and Service B depends on Service A:
```typescript
@Injectable()
export class ServiceA {
  constructor(@Inject(forwardRef(() => ServiceB)) private serviceB: ServiceB) {}
}
```

---

## 2. Modern TypeScript Design Patterns

### 2.1 Strategy Pattern (Discriminated Unions & Function Tables)
**Intent**: Define a family of interchangeable algorithms and pick one dynamically at runtime.

- In TypeScript, avoid complex class hierarchies. Use a **Lookup Table of Functions** or Discriminated Unions:

```typescript
export type CompressionType = 'gzip' | 'brotli' | 'none';

type Compressor = (data: Buffer) => Promise<Buffer>;

export const COMPRESSORS: Record<CompressionType, Compressor> = {
  gzip: async (data) => zlib.gzipSync(data),
  brotli: async (data) => zlib.brotliCompressSync(data),
  none: async (data) => data,
};

export async function compressPayload(type: CompressionType, payload: Buffer): Promise<Buffer> {
  const compressor = COMPRESSORS[type];
  if (!compressor) throw new Error(`Unsupported compression: ${type}`);
  return compressor(payload);
}
```

---

### 2.2 Builder Pattern (Type-Safe Fluent Configuration)
**Intent**: Construct complex configurations safely, preventing invalid partial state at compile time.

```typescript
export class HttpRequestBuilder {
  private url: string = '';
  private method: 'GET' | 'POST' | 'PUT' | 'DELETE' = 'GET';
  private headers: Record<string, string> = {};
  private body?: unknown;

  setUrl(url: string): this { this.url = url; return this; }
  setMethod(method: 'GET' | 'POST' | 'PUT' | 'DELETE'): this { this.method = method; return this; }
  addHeader(key: string, value: string): this { this.headers[key] = value; return this; }
  setJsonBody(body: unknown): this {
    this.body = body;
    this.headers['Content-Type'] = 'application/json';
    return this;
  }

  build(): Request {
    if (!this.url) throw new Error('URL must be specified');
    return new Request(this.url, {
      method: this.method,
      headers: this.headers,
      body: this.body ? JSON.stringify(this.body) : undefined,
    });
  }
}
```

---

### 2.3 Adapter Pattern
**Intent**: Convert the incompatible interface of an external library into an internal domain interface.

```typescript
// Domain Port Interface
export interface KeyValueCache {
  get(key: string): Promise<string | null>;
  set(key: string, value: string, ttlSeconds: number): Promise<void>;
}

// Adapter for ioredis
export class RedisCacheAdapter implements KeyValueCache {
  constructor(private readonly redisClient: import('ioredis').Redis) {}

  async get(key: string): Promise<string | null> {
    return this.redisClient.get(key);
  }

  async set(key: string, value: string, ttlSeconds: number): Promise<void> {
    await this.redisClient.set(key, value, 'EX', ttlSeconds);
  }
}
```

---

### 2.4 Decorator Pattern
**Intent**: Attach additional behaviors (caching, logging, timing) to operations transparently.

```typescript
// Functional Wrapper Decorator (Idiomatic & universal)
export function withTiming<TArgs extends any[], TReturn>(
  fn: (...args: TArgs) => Promise<TReturn>,
  operationName: string
): (...args: TArgs) => Promise<TReturn> {
  return async (...args: TArgs) => {
    const start = performance.now();
    try {
      return await fn(...args);
    } finally {
      const duration = performance.now() - start;
      console.log(`[Timing] ${operationName} executed in ${duration.toFixed(2)}ms`);
    }
  };
}
```

---

### 2.5 Observer / Publish-Subscribe Pattern
**Intent**: Notify multiple decoupled handlers when domain events occur.

```typescript
import { EventEmitter } from 'node:events';

export interface UserRegisteredEvent {
  userId: string;
  email: string;
}

export class DomainEventBus {
  private readonly emitter = new EventEmitter();

  publish<T>(event: string, payload: T): void {
    this.emitter.emit(event, payload);
  }

  subscribe<T>(event: string, handler: (payload: T) => void | Promise<void>): void {
    this.emitter.on(event, async (data) => {
      try {
        await handler(data);
      } catch (err) {
        console.error(`Error processing event ${event}:`, err);
      }
    });
  }
}
```

---

### 2.6 Repository & Unit of Work (Prisma / Drizzle)
**Intent**: Decouple domain logic from SQL queries, and manage transactional integrity.

```typescript
// Unit of Work with Prisma interactive transactions
export class PrismaUnitOfWork {
  constructor(private readonly prisma: PrismaClient) {}

  async runInTransaction<T>(work: (tx: Prisma.TransactionClient) => Promise<T>): Promise<T> {
    return this.prisma.$transaction(async (tx) => {
      return work(tx);
    }, {
      timeout: 10000,
      isolationLevel: Prisma.TransactionIsolationLevel.RepeatableRead,
    });
  }
}
```

