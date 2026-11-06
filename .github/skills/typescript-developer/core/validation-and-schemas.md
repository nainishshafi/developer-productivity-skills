# TypeScript Runtime Validation & Schema Architecture (Zod / Valibot)

Bridge compile-time TypeScript types with runtime validation using Zod and Valibot.

---

## 1. Why Runtime Validation is Mandatory

TypeScript types exist strictly during compilation and are completely erased in emitted JavaScript. Runtime payloads (HTTP request bodies, URL query parameters, environment variables, Webhook events) must be validated with runtime schemas to guarantee type safety and prevent injection/malformed data attacks.

---

## 2. Zod Enterprise Patterns

### Safe Parsing & Error Formatting
Never use `.parse()` in web request handlers without catching exceptions. Use `.safeParse()` for ergonomic error handling:

```typescript
import { z } from 'zod';

export const CreateProductSchema = z.object({
  name: z.string().trim().min(2).max(100),
  priceCents: z.number().int().positive(),
  tags: z.array(z.string().toLowerCase()).default([]),
  status: z.enum(['DRAFT', 'PUBLISHED']).default('DRAFT'),
});

export type CreateProductInput = z.infer<typeof CreateProductSchema>;

export function validateCreateProduct(input: unknown) {
  const result = CreateProductSchema.safeParse(input);
  if (!result.success) {
    // Format error into field-level map
    const fieldErrors = result.error.flatten().fieldErrors;
    return { ok: false as const, errors: fieldErrors };
  }
  return { ok: true as const, data: result.data };
}
```

### Discriminated Unions in Schemas
Validate complex polymorphic payloads deterministically:

```typescript
export const ActionPayloadSchema = z.discriminatedUnion('type', [
  z.object({
    type: z.literal('EMAIL'),
    recipient: z.string().email(),
    body: z.string(),
  }),
  z.object({
    type: z.literal('SMS'),
    phoneNumber: z.string().regex(/^\+[1-9]\d{1,14}$/),
    message: z.string().max(160),
  }),
]);

export type ActionPayload = z.infer<typeof ActionPayloadSchema>;
```

### Refinements & Transformations
Transform strings into dates or add custom cross-field validation:

```typescript
export const DateRangeSchema = z
  .object({
    startDate: z.coerce.date(),
    endDate: z.coerce.date(),
  })
  .refine((data) => data.endDate >= data.startDate, {
    message: 'End date must be after start date',
    path: ['endDate'],
  });
```

---

## 3. Valibot (Lightweight Alternative for Frontend / Edge)

For client-side bundles or Cloudflare Workers where bundle size is critical, Valibot offers a modular, tree-shakeable API that is 90% smaller than Zod:

```typescript
import * as v from 'valibot';

export const UserSchema = v.object({
  email: v.pipe(v.string(), v.email()),
  age: v.pipe(v.number(), v.minValue(18)),
});

export type User = v.InferOutput<typeof UserSchema>;
```

