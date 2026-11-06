# TypeScript Security Guidelines & Boundary Defense

Defend against common TypeScript / Node.js vulnerabilities, prototype pollution, injection, and untrusted inputs.

---

## 1. Prototype Pollution Defense

JavaScript object prototypes (`Object.prototype`) can be polluted if untrusted JSON keys like `__proto__`, `constructor`, or `prototype` are merged recursively without sanitization.

```typescript
// ❌ VULNERABLE: Recursive merge without prototype defense
function unsafeMerge(target: any, source: any) {
  for (const key of Object.keys(source)) {
    if (typeof source[key] === 'object') {
      target[key] = unsafeMerge(target[key] || {}, source[key]);
    } else {
      target[key] = source[key];
    }
  }
}

// ✅ SECURE: Use Object.create(null) or Map, and reject dangerous keys
const DANGEROUS_KEYS = new Set(['__proto__', 'constructor', 'prototype']);

export function safeMerge<T extends object, U extends object>(target: T, source: U): T & U {
  for (const key of Object.keys(source)) {
    if (DANGEROUS_KEYS.has(key)) continue;
    // ...
  }
  return Object.assign(target, source);
}
```

---

## 2. Input Defense with Runtime Validation (Zod / Valibot)

TypeScript types exist only at compile time; runtime JavaScript has no type safety. Validate every external payload (HTTP bodies, query params, environment variables, webhooks) with runtime schemas:

```typescript
import { z } from 'zod';

export const CreateUserSchema = z.object({
  email: z.string().email().max(255),
  age: z.number().int().min(18).max(120),
  role: z.enum(['ADMIN', 'MEMBER']).default('MEMBER'),
});

export type CreateUserInput = z.infer<typeof CreateUserSchema>;

export function parseCreateUser(input: unknown): CreateUserInput {
  return CreateUserSchema.parse(input);
}
```

---

## 3. Timing-Safe Comparisons

When comparing secret tokens, API keys, or HMAC signatures, use constant-time comparison to prevent side-channel timing attacks:

```typescript
import crypto from 'node:crypto';

export function timingSafeTokenEqual(a: string, b: string): boolean {
  const bufA = Buffer.from(a);
  const bufB = Buffer.from(b);
  if (bufA.length !== bufB.length) return false;
  return crypto.timingSafeEqual(bufA, bufB);
}
```

