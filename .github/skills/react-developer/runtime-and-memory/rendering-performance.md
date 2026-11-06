# React Rendering Performance & Virtualization

Optimize component rendering cycles, apply memoization pragmatically, and virtualize large DOM trees.

---

## 1. Pragmatic Memoization (`useMemo`, `useCallback`, `React.memo`)

Modern React is highly optimized for fast re-rendering. Premature or blanket memoization adds memory overhead and dependency tracking overhead without delivering measurable speedups.

### When Memoization IS Warranted:
1. **Passing callbacks to memoized children**: When a child component is wrapped in `React.memo` and renders an expensive DOM tree.
2. **Hook dependency arrays**: When an object or function is fed into `useEffect` or `useMemo` dependency arrays.
3. **Measurably expensive calculations**: CPU-intensive algorithms (filtering/sorting 5,000+ items, complex matrix transforms) taking > 2ms.

```tsx
// ✅ APPROPRIATE USE: Expensive filter on 10,000 items
const filteredProducts = useMemo(() => {
  return rawProducts.filter(p => matchesComplexCriteria(p, query));
}, [rawProducts, query]);

// ❌ ANTI-PATTERN: Premature memoization of trivial operations
const fullName = useMemo(() => `${firstName} ${lastName}`, [firstName, lastName]); // Slower than direct string concatenation!
```

---

## 2. DOM Virtualization for Large Lists

Mounting thousands of DOM nodes in the browser consumes massive heap memory, slows down layout calculation, and causes scroll jitter. Use virtualization (`@tanstack/react-virtual` or `react-window`):

```tsx
import { useVirtualizer } from '@tanstack/react-virtual';
import { useRef } from 'react';

export function VirtualizedList({ items }: { items: string[] }) {
  const parentRef = useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 40, // Height in pixels
    overscan: 5,
  });

  return (
    <div ref={parentRef} className="h-96 overflow-auto border">
      <div
        className="w-full relative"
        style={{ height: `${virtualizer.getTotalSize()}px` }}
      >
        {virtualizer.getVirtualItems().map((virtualRow) => (
          <div
            key={virtualRow.index}
            className="absolute top-0 left-0 w-full px-4 py-2 border-b"
            style={{
              height: `${virtualRow.size}px`,
              transform: `translateY(${virtualRow.start}px)`,
            }}
          >
            {items[virtualRow.index]}
          </div>
        ))}
      </div>
    </div>
  );
}
```

