# TypeScript Data Persistence, ORMs & Query Builders

Architectural patterns for database access using Drizzle ORM and Prisma in TypeScript.

---

## 1. Drizzle ORM vs Prisma Decision Matrix

| Dimension | Drizzle ORM | Prisma ORM |
|---|---|---|
| **Paradigm** | SQL-like query builder + relational layer | High-level abstracted DSL (`schema.prisma`) |
| **Performance** | Extremely fast (near raw driver speed, zero engine overhead) | Moderate (Rust query engine binary) |
| **Serverless / Edge** | Native support, sub-millisecond cold start | Requires Prisma Accelerate / edge adapters |
| **Type Safety** | Types inferred directly from TypeScript schemas | Types generated via `prisma generate` CLI |

---

## 2. Drizzle ORM Best Practices

### Schema Definition & Type Inference
```typescript
// db/schema.ts
import { pgTable, uuid, varchar, timestamp, integer } from 'drizzle-orm/pg-core';

export const users = pgTable('users', {
  id: uuid('id').primaryKey().defaultRandom(),
  email: varchar('email', { length: 255 }).notNull().unique(),
  createdAt: timestamp('created_at').defaultNow().notNull(),
});

// Infer types directly without CLI code generation
export type User = typeof users.$inferSelect;
export type NewUser = typeof users.$inferInsert;
```

### Relational Queries & Preventing N+1
```typescript
import { db } from './db';

// Fetches user and their posts in a single optimized SQL join/query
export async function getUserWithPosts(userId: string) {
  return db.query.users.findFirst({
    where: (users, { eq }) => eq(users.id, userId),
    with: {
      posts: {
        limit: 10,
        orderBy: (posts, { desc }) => [desc(posts.createdAt)],
      },
    },
  });
}
```

---

## 3. Prisma Best Practices

### Preventing N+1 Queries
Always use `include` or explicit relation joins rather than looping over parent records with queries:

```typescript
// ❌ ANTI-PATTERN: N+1 query vulnerability
const users = await prisma.user.findMany();
for (const u of users) {
  const posts = await prisma.post.findMany({ where: { authorId: u.id } }); // N database queries!
}

// ✅ BEST PRACTICE: Batch relation fetch
const usersWithPosts = await prisma.user.findMany({
  include: {
    posts: { take: 10 },
  },
});
```

### Transactions
Always wrap multi-step mutations in transactions:

```typescript
export async function transferBalance(senderId: string, receiverId: string, amount: number) {
  return prisma.$transaction(async (tx) => {
    const sender = await tx.account.update({
      where: { id: senderId },
      data: { balance: { decrement: amount } },
    });

    if (sender.balance < 0) {
      throw new Error('Insufficient funds');
    }

    await tx.account.update({
      where: { id: receiverId },
      data: { balance: { increment: amount } },
    });
  });
}
```
