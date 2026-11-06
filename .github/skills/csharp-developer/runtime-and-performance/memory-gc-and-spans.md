# Memory Hygiene, GC & Spans (.NET 8 / .NET 9)

Zero-allocation patterns, garbage collection generational mechanics, `Span<T>`, and buffer pooling in modern .NET.

---

## 1. .NET Garbage Collection Architecture

The .NET CLR employs an Ephemeral Generational Garbage Collector:

```
[ Gen 0 (Short-lived) ] ---> Survives ---> [ Gen 1 (Buffer) ] ---> Survives ---> [ Gen 2 (Long-lived) ]
                                                                                         |
                                                                        [ LOH (>85KB) ]  [ POH (Pinned) ]
```

- **Gen 0**: Microsecond collections. Newly allocated small objects.
- **Gen 1**: Buffer generation balancing ephemeral and long-lived memory.
- **Gen 2**: Expensive, stop-the-world full GC sweeps. Keep Gen 2 allocations near zero in hot paths.
- **Large Object Heap (LOH)**: Objects $\ge$ 85,000 bytes. Allocated directly into Gen 2 without compaction by default (risks memory fragmentation).
- **Pinned Object Heap (POH)**: Dedicated heap for memory pinned during native interop or I/O.

---

## 2. Zero-Allocation Slicing with `ReadOnlySpan<T>`

`Span<T>` is a ref struct representing a contiguous region of arbitrary memory (managed heap, native heap, or stack) without heap allocations:

```csharp
// BAD: Allocates 3 new strings on the managed heap
string rawHeader = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9";
string token = rawHeader.Substring(7); // Heap allocation!

// GOOD: Zero heap allocation using ReadOnlySpan<char>
ReadOnlySpan<char> span = rawHeader.AsSpan();
if (span.StartsWith("Bearer ", StringComparison.OrdinalIgnoreCase))
{
    ReadOnlySpan<char> tokenSpan = span.Slice(7); // Zero-allocation view
    ProcessToken(tokenSpan);
}

// Parsing primitives directly from Spans:
ReadOnlySpan<char> numericSpan = "12345".AsSpan();
if (int.TryParse(numericSpan, out int result))
{
    // result == 12345
}
```

> **Rule:** `Span<T>` is a `ref struct` and cannot cross `await` boundaries or be stored in heap-allocated classes. Use `Memory<T>` / `ReadOnlyMemory<T>` when async suspension is required.

---

## 3. High-Performance Buffer Pooling with `ArrayPool<T>`

Avoid allocating large byte arrays that end up on the LOH:

```csharp
public async Task ProcessLargeStreamAsync(Stream stream, CancellationToken ct)
{
    // Rent a 64KB buffer from the shared pool
    byte[] buffer = ArrayPool<byte>.Shared.Rent(64 * 1024);
    try
    {
        int bytesRead;
        while ((bytesRead = await stream.ReadAsync(buffer.AsMemory(0, buffer.Length), ct)) > 0)
        {
            ProcessBufferChunk(buffer.AsSpan(0, bytesRead));
        }
    }
    finally
    {
        // ALWAYS return buffer in finally block to prevent memory leaks!
        ArrayPool<byte>.Shared.Return(buffer, clearArray: false);
    }
}
```

---

## 4. Preventing Closure Allocations in Lambdas

When a lambda captures an outer local variable or `this`, the C# compiler allocates a hidden display class instance on every execution.

### Static Lambdas (C# 9+)
Mark lambdas as `static` so the compiler guarantees no accidental closures occur:

```csharp
var users = GetUsers();

// BAD: Implicitly captures 'currentTenantId' creating closure allocation
var filtered = users.Where(u => u.TenantId == currentTenantId);

// GOOD: Zero-closure lambda using static modifier and state argument
static bool FilterByTenant(User user, Guid tenantId) => user.TenantId == tenantId;

// Or with LINQ passing state:
var tenant = currentTenantId;
var safeFiltered = users.Where(static (u, t) => u.TenantId == t, tenant);
```

---

## 5. Struct Allocations: `in`, `readonly ref`, and `SearchValues`

### Passing Large Structs by Reference
```csharp
public readonly struct TransactionSnapshot
{
    public required decimal Amount { get; init; }
    public required DateTime Timestamp { get; init; }
    public required Guid AccountId { get; init; }
}

// 'in' modifier passes by read-only reference without copying 32+ bytes on stack
public void RecordMetrics(in TransactionSnapshot snapshot)
{
    // snapshot is read-only
}
```

### Ultra-Fast Vectorized Searching (`SearchValues<T>`) (.NET 8+)
```csharp
// Hardware-accelerated vectorized search (SIMD)
private static readonly SearchValues<char> Base64Chars = 
    SearchValues.Create("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=");

public static bool IsValidBase64(ReadOnlySpan<char> input)
{
    return input.IndexOfAnyExcept(Base64Chars) == -1;
}
```
