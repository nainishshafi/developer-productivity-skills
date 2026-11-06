# Asynchronous Programming & Channels (.NET 8 / .NET 9)

High-throughput asynchronous workflows, producer-consumer channels, and threadpool starvation prevention.

---

## 1. `Task` vs. `ValueTask<T>`

`Task<T>` is a class allocated on the heap for every operation. `ValueTask<T>` is a struct designed for methods that frequently complete synchronously (e.g., from an in-memory cache).

```csharp
public class CachedUserService(IMemoryCache cache, IDbContextFactory<AppDbContext> dbFactory)
{
    // Return ValueTask to eliminate heap allocations when result is cached
    public ValueTask<UserDto?> GetUserByIdAsync(Guid id, CancellationToken ct)
    {
        if (cache.TryGetValue(id, out UserDto? cached))
        {
            return ValueTask.FromResult(cached); // Zero heap allocation!
        }

        return new ValueTask<UserDto?>(FetchFromDatabaseAsync(id, ct));
    }

    private async Task<UserDto?> FetchFromDatabaseAsync(Guid id, CancellationToken ct)
    {
        await using var db = await dbFactory.CreateDbContextAsync(ct);
        var user = await db.Users.FindAsync([id], ct);
        if (user is not null)
        {
            cache.Set(id, user.ToDto(), TimeSpan.FromMinutes(10));
        }
        return user?.ToDto();
    }
}
```

> **Rules for `ValueTask`:**
> 1. Never `await` a `ValueTask` multiple times.
> 2. Never call `.AsTask()` unless strictly necessary.
> 3. Prefer `Task` unless performance profiling shows high allocation pressure from synchronous completions.

---

## 2. High-Throughput Producer-Consumer with `System.Threading.Channels`

`Channel<T>` outperforms `BlockingCollection<T>` and concurrent queues by offering lock-free, zero-allocation asynchronous backpressure:

```csharp
public sealed class EventProcessingPipeline
{
    // Bounded channel prevents out-of-memory errors by pushing back on producers
    private readonly Channel<AuditEvent> _channel = Channel.CreateBounded<AuditEvent>(new BoundedChannelOptions(capacity: 10_000)
    {
        FullMode = BoundedChannelFullMode.Wait, // Apply backpressure when queue is full
        SingleWriter = false,
        SingleReader = true // Optimize lockless reading if consumed by single worker
    });

    // Producer method
    public async ValueTask PublishEventAsync(AuditEvent evt, CancellationToken ct)
    {
        await _channel.Writer.WriteAsync(evt, ct);
    }

    // Consumer background loop
    public async Task StartConsumingAsync(CancellationToken ct)
    {
        var reader = _channel.Reader;

        // Reads items as they arrive; completes when Writer.Complete() is called
        await foreach (var evt in reader.ReadAllAsync(ct))
        {
            await ProcessSingleEventAsync(evt, ct);
        }
    }

    public void Shutdown()
    {
        _channel.Writer.Complete();
    }
}
```

---

## 3. Strict `CancellationToken` Propagation

Every asynchronous method should accept and pass a `CancellationToken` down the call stack to cancel orphaned I/O operations and database queries when clients disconnect:

```csharp
// Program.cs / Endpoint
app.MapGet("/api/reports/sales", async (
    ReportService reports, 
    CancellationToken ct) => // ASP.NET Core automatically cancels ct on HTTP disconnect
{
    var stream = await reports.GenerateSalesStreamAsync(ct);
    return TypedResults.Stream(stream, "application/pdf");
});

// Service method
public async Task<Stream> GenerateSalesStreamAsync(CancellationToken ct)
{
    // Throw early if cancelled
    ct.ThrowIfCancellationRequested();

    await using var client = await clientFactory.CreateClientAsync(ct);
    return await client.GetStreamAsync(reportUrl, ct);
}
```

---

## 4. Preventing ThreadPool Starvation & Deadlocks

### Sync-over-Async (Anti-Pattern)
Calling `.Result`, `.Wait()`, or `.GetAwaiter().GetResult()` blocks the threadpool worker thread waiting for another asynchronous task, leading to thread exhaustion:

```csharp
// FATAL ANTI-PATTERN: Can deadlock or starve thread pool under load
public UserDto GetUserSync(Guid id)
{
    return GetUserAsync(id).Result; // DO NOT DO THIS!
}

// CORRECT: Make the entire execution path asynchronous
public async Task<UserDto> GetUserAsync(Guid id)
{
    return await repository.GetUserAsync(id);
}
```

### Avoiding `Task.Run` inside ASP.NET Core Request Paths
```csharp
// ANTI-PATTERN in ASP.NET Core:
app.MapPost("/api/orders", async (OrderRequest req) =>
{
    // Wastes a threadpool worker thread to offload I/O work!
    var result = await Task.Run(() => ProcessOrderAsync(req)); 
    return TypedResults.Ok(result);
});

// CORRECT: Directly await the asynchronous I/O method
app.MapPost("/api/orders", async (OrderRequest req, CancellationToken ct) =>
{
    var result = await ProcessOrderAsync(req, ct);
    return TypedResults.Ok(result);
});
```

### `ConfigureAwait(false)` in Modern .NET
- **In ASP.NET Core Apps**: ASP.NET Core does not have a `SynchronizationContext`. `ConfigureAwait(false)` is not required in application code.
- **In Reusable Class Libraries**: Always append `.ConfigureAwait(false)` to avoid deadlocking consumers that run on custom synchronization contexts (WPF, WinForms, older ASP.NET).

