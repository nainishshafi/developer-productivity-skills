# React Server State & Cache Stores (TanStack Query)

Manage server data caching, background revalidation, optimistic updates, and cache synchronization with TanStack Query v5.

---

## 1. Core Principles of Server State

- **Server state is NOT client state**: It is remote, asynchronous, shared across clients, and can become stale without your knowledge.
- **Never duplicate server state into Zustand or `useState`**: Storing query data in a client store creates dual sources of truth and cache desynchronization. Use TanStack Query as the dedicated server cache store.

---

## 2. Query Key Factories (Type-Safe Cache Keys)

Centralize query keys using the **Query Key Factory Pattern** to prevent key typos and enable deterministic cache invalidation:

```typescript
// features/todos/queryKeys.ts
export const todoKeys = {
  all: ['todos'] as const,
  lists: () => [...todoKeys.all, 'list'] as const,
  list: (filters: { status?: string; search?: string }) => [...todoKeys.lists(), filters] as const,
  details: () => [...todoKeys.all, 'detail'] as const,
  detail: (id: string) => [...todoKeys.details(), id] as const,
};
```

---

## 3. Query Configuration & Cache Lifecycles

```typescript
// features/todos/hooks/useTodos.ts
import { useQuery } from '@tanstack/react-query';
import { todoKeys } from '../queryKeys';
import { fetchTodos } from '../api';

export function useTodos(status?: string) {
  return useQuery({
    queryKey: todoKeys.list({ status }),
    queryFn: ({ signal }) => fetchTodos({ status, signal }),
    staleTime: 1000 * 60 * 5,       // Data remains "fresh" for 5 minutes (no refetching on window focus)
    gcTime: 1000 * 60 * 30,         // Unused cache retained in RAM for 30 minutes before garbage collection
    refetchOnWindowFocus: true,     // Revalidate in background when user re-focuses tab
    retry: (failureCount, error) => {
      // Don't retry on 401 or 404 client errors
      if (isHttpError(error) && (error.status === 401 || error.status === 404)) return false;
      return failureCount < 3;
    },
  });
}
```

---

## 4. Optimistic Updates with Rollback on Failure

Provide instant UI responsiveness by updating the query cache immediately and rolling back if the server mutation rejects:

```typescript
// features/todos/hooks/useToggleTodo.ts
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { todoKeys } from '../queryKeys';
import { toggleTodoApi, Todo } from '../api';

export function useToggleTodo() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: toggleTodoApi,
    // Step 1: When mutate is called:
    onMutate: async (todoId: string) => {
      // Cancel outgoing refetches so they don't overwrite optimistic update
      await queryClient.cancelQueries({ queryKey: todoKeys.lists() });

      // Snapshot previous value for rollback
      const previousTodos = queryClient.getQueryData<Todo[]>(todoKeys.lists());

      // Optimistically update cache
      queryClient.setQueryData<Todo[]>(todoKeys.lists(), (old = []) =>
        old.map((todo) =>
          todo.id === todoId ? { ...todo, completed: !todo.completed } : todo
        )
      );

      // Return context with snapshot
      return { previousTodos };
    },
    // Step 2: If mutation fails, rollback to snapshot:
    onError: (err, todoId, context) => {
      if (context?.previousTodos) {
        queryClient.setQueryData(todoKeys.lists(), context.previousTodos);
      }
    },
    // Step 3: Always invalidate and refetch on settle:
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: todoKeys.lists() });
    },
  });
}
```

