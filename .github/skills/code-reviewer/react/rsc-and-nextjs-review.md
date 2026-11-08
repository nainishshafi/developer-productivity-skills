# React Server Components & Next.js Review Guide

Audit guide for Next.js App Router, React Server Components (RSC), and Server Actions.

---

## 1. RSC Boundary Discipline

- [ ] **Pushing `'use client'` to the Leaves**:
  - Is `'use client'` applied at the page or layout level? Flag as `[P2 - Minor]`.
  - **Resolution**: Keep pages and layouts as Server Components. Extract only interactive widgets (buttons, dropdowns, forms) into client component leaf nodes.
- [ ] **Secret Leakage Across Client Boundary**:
  - Are server secrets, database credentials, or private API keys passed as props into `'use client'` components?
  - Flag sensitive props crossing into client bundles as `[P0 - Blocker]`. Use `server-only` package in server modules.

---

## 2. Server Actions & Form Mutations

- [ ] **Authorization on Server Actions**:
  - Do Server Actions (`'use server'`) verify authentication and user permissions before performing mutations?
  - Server Actions are public HTTP endpoints; never assume caller identity without session validation.
- [ ] **Input Validation in Server Actions**:
  - Are action arguments parsed and validated using a schema validator (Zod) before executing database logic?
- [ ] **Revalidation**:
  - Do Server Actions invoke `revalidatePath()` or `revalidateTag()` to purge stale Next.js cache after mutation?

---

## 3. Data Fetching & Waterfalls

- [ ] **Sequential Waterfall Fetches**:
  - Are independent server component fetch calls awaited sequentially?
  ```typescript
  // BAD: Waterfall delay
  const user = await fetchUser();
  const posts = await fetchPosts();

  // GOOD: Parallel fetch
  const [user, posts] = await Promise.all([fetchUser(), fetchPosts()]);
  ```
- [ ] **Suspense Boundaries**:
  - Are slow data dependencies wrapped in `<Suspense fallback={<Skeleton />}>` to enable streaming server rendering?

