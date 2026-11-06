# React Memory Safety, Closures & Lifecycle Teardown

Prevent stale closures, memory leaks in unmounted components, and subscription leaks in modern React.

---

## 1. Stale Closure Bugs in Effects and Callbacks

In JavaScript and React, a closure captures variables from the render cycle in which it was declared. If dependency arrays omit variables, handlers will operate on stale state indefinitely:

```tsx
// ❌ ANTI-PATTERN: Stale closure in interval handler
export function Counter() {
  const [count, setCount] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setCount(count + 1); // Traps `count = 0` forever! Count never increases beyond 1
    }, 1000);
    return () => clearInterval(timer);
  }, []); // Missing count dependency

  return <div>{count}</div>;
}

// ✅ BEST PRACTICE: Functional state updater operates on current value without dependencies
export function Counter() {
  const [count, setCount] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setCount(prev => prev + 1); // Always gets the latest state
    }, 1000);
    return () => clearInterval(timer);
  }, []); // Clean empty dependency array

  return <div>{count}</div>;
}
```

---

## 2. Preventing Memory Leaks from In-Flight Async Operations

When a user navigates away before an asynchronous request completes, resolving promises that update unmounted component state can cause memory leaks and errors:

```tsx
// ❌ ANTI-PATTERN: Continues async work after unmount
export function BadSearch({ query }: { query: string }) {
  const [results, setResults] = useState([]);

  useEffect(() => {
    fetchUsers(query).then(res => setResults(res));
  }, [query]);
}

// ✅ BEST PRACTICE: AbortController cancels network request immediately on unmount
export function GoodSearch({ query }: { query: string }) {
  const [results, setResults] = useState<User[]>([]);

  useEffect(() => {
    const ac = new AbortController();

    async function execute() {
      try {
        const res = await fetchUsers(query, { signal: ac.signal });
        setResults(res);
      } catch (err) {
        if ((err as Error).name !== 'AbortError') throw err;
      }
    }

    void execute();
    return () => ac.abort(); // Cancels fetch on re-render or component unmount
  }, [query]);
}
```

---

## 3. Subscribing to External Stores with `useSyncExternalStore`

Instead of rolling manual `useEffect` + `useState` subscriptions to window events or external publishers (which suffer from tearing in concurrent React and memory leak risks), use React 18+'s `useSyncExternalStore`:

```tsx
import { useSyncExternalStore } from 'react';

function subscribeOnlineStatus(callback: () => void) {
  window.addEventListener('online', callback);
  window.addEventListener('offline', callback);
  return () => {
    window.removeEventListener('online', callback);
    window.removeEventListener('offline', callback);
  };
}

export function useIsOnline(): boolean {
  return useSyncExternalStore(
    subscribeOnlineStatus,
    () => navigator.onLine,
    () => true // SSR fallback snapshot
  );
}
```

---

## 4. Teardown of Heavy Mutable Instances (`useRef`)

When integrating third-party libraries (Chart.js, Leaflet, Three.js, WebGL canvases, AudioContext) that attach directly to the DOM, always destroy instances in the cleanup function:

```tsx
export function CanvasChart({ data }: { data: DataPoint[] }) {
  const chartRef = useRef<ChartInstance | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    if (!canvasRef.current) return;
    chartRef.current = new ChartInstance(canvasRef.current, data);

    return () => {
      // Crucial: dispose and release GPU memory/listeners
      chartRef.current?.destroy();
      chartRef.current = null;
    };
  }, [data]);

  return <canvas ref={canvasRef} />;
}
```

