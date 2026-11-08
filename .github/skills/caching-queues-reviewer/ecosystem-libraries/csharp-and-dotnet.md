# C# & .NET: Caching & Queue Ecosystem

Comprehensive architectural guidance for .NET 8 LTS and .NET 9 when architecting and reviewing in-memory caches, distributed Redis clusters, multi-tier hybrid caches, background channels, and enterprise messaging systems.

---

## 1. Library & Abstraction Selection Matrix

| Category | Recommended Abstraction / Library | Alternative | When to Choose What |
|---|---|---|---|
| **In-Memory Cache (L1)** | **`IMemoryCache`** | `MemoryCache` directly | Standard dependency-injected in-process cache. Always set `SizeLimit` and configure compaction callbacks to prevent unbounded heap consumption. |
| **Distributed Cache (L2)** | **`StackExchange.Redis`** | `IDistributedCache` (`AddStackExchangeRedisCache`) | `IDistributedCache` is limited to basic `byte[]` Get/Set operations. Use `StackExchange.Redis` directly for Hashes, Sets, Sorted Sets, Pub/Sub, Pipelining, and atomic Lua scripting. |
| **Multi-Tier Hybrid Cache** | **`HybridCache`** (.NET 9+) | Custom L1+L2 orchestrator | .NET 9 `Microsoft.Extensions.Caching.HybridCache` combines fast in-memory L1 with Redis L2, automatically providing **out-of-the-box Cache Stampede defense** (single-flight locking) and tag-based invalidation. |
| **Local In-Process Queue** | **`System.Threading.Channels`** (`Channel<T>`) | `BlockingCollection<T>` / `ConcurrentQueue<T>` | Lock-free, non-blocking asynchronous backpressure for background workers (`IHostedService` / `BackgroundService`). |
| **Enterprise Message Bus** | **`MassTransit`** | Direct driver code | Clean domain abstraction over RabbitMQ, Kafka, Azure Service Bus, and Amazon SQS with built-in retries, outbox pattern, and saga state machines. |
| **Apache Kafka Driver** | **`Confluent.Kafka`** | MassTransit Rider | Official high-throughput librdkafka wrapper with support for consumer groups, manual commit, and Avro/Protobuf schema registry. |

---

## 2. Multi-Tier Caching with .NET 9 `HybridCache`

`HybridCache` solves the dual challenges of Redis network latency and cache stampedes.

```csharp
using Microsoft.Extensions.Caching.Hybrid;

public class ProductCatalogService(HybridCache cache, AppDbContext db)
{
    public async Task<ProductDto> GetProductByIdAsync(int id, CancellationToken ct = default)
    {
        // Automatically checks L1 memory, falls back to L2 Redis,
        // and uses a single-flight mutex lock so only ONE request hits the database on a miss.
        return await cache.GetOrCreateAsync(
            key: $"product:{id}",
            factory: async cancelToken =>
            {
                var product = await db.Products.FindAsync([id], cancelToken)
                    ?? throw new KeyNotFoundException($"Product {id} not found");
                return new ProductDto(product.Id, product.Name, product.Price);
            },
            options: new HybridCacheEntryOptions
            {
                Expiration = TimeSpan.FromMinutes(30),       // L2 Redis TTL
                LocalCacheExpiration = TimeSpan.FromMinutes(5) // L1 In-Memory TTL
            },
            tags: ["catalog", $"product-{id}"],
            cancellationToken: ct
        );
    }

    public async Task InvalidateProductAsync(int id, CancellationToken ct = default)
    {
        // Evicts from both L1 and distributed L2 atomically
        await cache.RemoveByTagAsync($"product-{id}", ct);
    }
}
```

---

## 3. High-Performance Redis & Lua with `StackExchange.Redis`

`ConnectionMultiplexer` is designed to be a thread-safe **singleton** shared across the entire application lifecycle. Never create a new multiplexer per request.

```csharp
using StackExchange.Redis;

public class RedisDistributedLockService(IConnectionMultiplexer muxer)
{
    private readonly IDatabase _db = muxer.GetDatabase();

    private static readonly LuaScript ReleaseLockScript = LuaScript.Prepare(@"
        if redis.call('GET', @key) == @ownerToken then
            return redis.call('DEL', @key)
        else
            return 0
        end
    ");

    public async Task<bool> AcquireLockAsync(string key, string ownerToken, TimeSpan expiry)
    {
        // SET key ownerToken NX PX expiry_ms
        return await _db.StringSetAsync(
            key,
            ownerToken,
            expiry,
            When.NotExists
        );
    }

    public async Task<bool> ReleaseLockAsync(string key, string ownerToken)
    {
        // Executes via EVALSHA automatically
        var result = await _db.ScriptEvaluateAsync(ReleaseLockScript, new { key = (RedisKey)key, ownerToken });
        return (int)result == 1;
    }
}
```

---

## 4. Local Asynchronous Producer-Consumer with `Channel<T>`

```csharp
using System.Threading.Channels;

public class AuditQueue
{
    // Bounded capacity prevents unbounded memory growth under load
    private readonly Channel<AuditEvent> _channel = Channel.CreateBounded<AuditEvent>(new BoundedChannelOptions(10_000)
    {
        FullMode = BoundedChannelFullMode.Wait, // Applies backpressure
        SingleReader = true,
        SingleWriter = false
    });

    public ValueTask EnqueueAsync(AuditEvent evt, CancellationToken ct = default) =>
        _channel.Writer.WriteAsync(evt, ct);

    public IAsyncEnumerable<AuditEvent> ReadAllAsync(CancellationToken ct = default) =>
        _channel.Reader.ReadAllAsync(ct);
}

// Background Worker consuming from channel
public class AuditWorker(AuditQueue queue, IServiceProvider serviceProvider) : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        await foreach (var auditEvent in queue.ReadAllAsync(stoppingToken))
        {
            using var scope = serviceProvider.CreateScope();
            var db = scope.ServiceProvider.GetRequiredService<AuditDbContext>();
            db.AuditLogs.Add(auditEvent);
            await db.SaveChangesAsync(stoppingToken);
        }
    }
}
```

---

## 5. Kafka High-Throughput Consumer with `Confluent.Kafka`

```csharp
using Confluent.Kafka;
using System.Text.Json;

public class OrderKafkaConsumerService : BackgroundService
{
    private readonly ConsumerConfig _config = new()
    {
        BootstrapServers = "localhost:9092",
        GroupId = "dotnet-order-processors",
        AutoOffsetReset = AutoOffsetReset.Earliest,
        EnableAutoCommit = false, // Enforce manual commit after processing
        EnableAutoOffsetStore = false
    };

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        await Task.Yield(); // Free startup thread
        using var consumer = new ConsumerBuilder<string, string>(_config).Build();
        consumer.Subscribe("orders.v1");

        try
        {
            while (!stoppingToken.IsCancellationRequested)
            {
                var consumeResult = consumer.Consume(stoppingToken);
                if (consumeResult?.Message is null) continue;

                try
                {
                    var order = JsonSerializer.Deserialize<OrderEvent>(consumeResult.Message.Value);
                    await ProcessOrderAsync(order, stoppingToken);

                    // Commit offset strictly after successful business processing
                    consumer.Commit(consumeResult);
                }
                catch (JsonException ex)
                {
                    // Poison pill handling: Route to DLQ before moving offset forward
                    await RouteToDeadLetterQueueAsync(consumeResult.Message, ex);
                    consumer.Commit(consumeResult);
                }
            }
        }
        finally
        {
            consumer.Close();
        }
    }
}
```

