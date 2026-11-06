# TypeScript Error Architecture & Resilience

Design robust error handling by separating operational business errors from system bugs, using typed Result types, and supporting graceful cancellation.

---

## 1. Operational Errors vs System Defects

- **Operational Errors**: Expected failure modes during normal system execution (user not found, validation failed, card declined). Represent these with typed `Result<T, E>` or structured domain exceptions.
- **System Defects**: Bugs or unexpected environmental failures (uncaught null pointer, memory exhaustion, network connection pool exhausted). Let these fail fast or throw uncaught exceptions to boundary interceptors.

---

## 2. Typed `Result<T, E>` Pattern

For core domain logic, prefer explicit typed results over throwing un-typed exceptions:

```typescript
export type Result<T, E = Error> =
  | { ok: true; value: T }
  | { ok: false; error: E };

export const Result = {
  ok: <T>(value: T): Result<T, never> => ({ ok: true, value }),
  err: <E>(error: E): Result<never, E> => ({ ok: false, error }),
};

// Domain service returns explicit failure variants
export type RegistrationError =
  | { code: 'EMAIL_ALREADY_EXISTS'; email: string }
  | { code: 'WEAK_PASSWORD'; reason: string };

export async function registerUser(input: RegisterInput): Promise<Result<User, RegistrationError>> {
  const existing = await userRepo.findByEmail(input.email);
  if (existing) {
    return Result.err({ code: 'EMAIL_ALREADY_EXISTS', email: input.email });
  }

  const user = await userRepo.create(input);
  return Result.ok(user);
}
```

---

## 3. Structured Error Hierarchy

When throwing exceptions (e.g., in REST controllers or RPC handlers), use a formal typed class hierarchy:

```typescript
export abstract class AppError extends Error {
  abstract readonly statusCode: number;
  abstract readonly errorCode: string;

  constructor(message: string, public readonly context?: Record<string, unknown>) {
    super(message);
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

export class NotFoundError extends AppError {
  readonly statusCode = 404;
  readonly errorCode = 'NOT_FOUND';
}

export class ConflictError extends AppError {
  readonly statusCode = 409;
  readonly errorCode = 'CONFLICT';
}
```

---

## 4. Timeout & Cancellation Support with `AbortSignal`

Every async outbound call (HTTP request, external API, database query) should support cancellation:

```typescript
export async function fetchWithTimeout(url: string, timeoutMs = 5000, parentSignal?: AbortSignal): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(new Error(`Request timed out after ${timeoutMs}ms`)), timeoutMs);

  if (parentSignal) {
    parentSignal.addEventListener('abort', () => controller.abort(parentSignal.reason), { once: true });
  }

  try {
    return await fetch(url, { signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}
```

