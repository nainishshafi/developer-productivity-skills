# React Server Components (RSC) & Next.js App Router

Architectural boundaries, data access, and interactivity guidelines for modern React Server Components and Next.js.

---

## 1. RSC vs Client Components Decision Matrix

| Capability | Server Component (Default) | Client Component (`'use client'`) |
|---|---|---|
| Fetch data directly from DB / filesystem | ✅ Yes (zero client bundle) | ❌ No |
| Keep sensitive API keys / tokens secret | ✅ Yes | ❌ No |
| Reduce JavaScript sent to the browser | ✅ Yes | ❌ No (hydrated on client) |
| Use hooks (`useState`, `useEffect`, `useRef`) | ❌ No | ✅ Yes |
| Attach browser event handlers (`onClick`, `onChange`) | ❌ No | ✅ Yes |
| Use browser-only APIs (`window`, `localStorage`) | ❌ No | ✅ Yes |

---

## 2. Push `'use client'` to the Leaves

Never mark entire page layouts or top-level containers with `'use client'`. Keep the tree server-rendered and isolate client interactivity to leaf components:

```tsx
// ❌ ANTI-PATTERN: Marking entire page client-side
'use client';
export default async function ProductPage() { ... } // Loses all RSC benefits!

// ✅ BEST PRACTICE: Server Component page importing interactive client leaf
// app/products/[id]/page.tsx (Server Component)
import { db } from '@/lib/db';
import { AddToCartButton } from './AddToCartButton'; // 'use client'

export default async function ProductPage({ params }: { params: { id: string } }) {
  const product = await db.product.findUnique({ where: { id: params.id } });
  if (!product) notFound();

  return (
    <div>
      <h1>{product.name}</h1>
      <p>{product.description}</p>
      {/* Only the interactive button ships JavaScript to the client */}
      <AddToCartButton productId={product.id} />
    </div>
  );
}
```

---

## 3. Streaming with Suspense Boundaries

Break slow-loading parts of the page into Suspense boundaries so the initial page shell renders instantly:

```tsx
import { Suspense } from 'react';
import { ProductSkeleton } from '@/components/skeletons';
import { ProductReviews } from './ProductReviews';

export default function Page() {
  return (
    <div>
      <MainProductDetails />
      <Suspense fallback={<ProductSkeleton />}>
        {/* Streams reviews chunk when DB query finishes without blocking main UI */}
        <ProductReviews />
      </Suspense>
    </div>
  );
}
```

