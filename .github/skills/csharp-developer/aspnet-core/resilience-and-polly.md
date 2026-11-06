# Resilience & Polly (.NET 8 / .NET 9)

Fault-tolerant HTTP clients, circuit breakers, rate limiting, and health checks using Polly v8 and `Microsoft.Extensions.Resilience`.

---

## 1. Polly v8 Architecture Overview

In .NET 8+, Microsoft collaborated with Polly to create `Microsoft.Extensions.Resilience` and `Polly.Core`. The v8 API uses zero-allocation resilience pipelines instead of the legacy `Policy` objects.

```
Incoming Request -> [Total Request Timeout] -> [Retry] -> [Circuit Breaker] -> [Rate Limiter] -> [Attempt Timeout] -> Target
```

---

## 2. The Standard Resilience Handler

For 90% of microservice outbound calls, Microsoft provides preconfigured enterprise resilience out-of-the-box:

```csharp
// Requires NuGet: Microsoft.Extensions.Http.Resilience
builder.Services.AddHttpClient<IInventoryClient, InventoryClient>(client =>
{
    client.BaseAddress = new Uri("https://inventory.internal.net");
})
.AddStandardResilienceHandler(options =>
{
    // Customize default thresholds
    options.Retry.MaxRetryAttempts = 3;
    options.Retry.BackoffType = DelayBackoffType.Exponential;
    options.Retry.UseJitter = true;

    options.CircuitBreaker.SamplingDuration = TimeSpan.FromSeconds(30);
    options.CircuitBreaker.FailureRatio = 0.2; // Break circuit if > 20% fail
    options.CircuitBreaker.MinimumThroughput = 10;
    options.CircuitBreaker.BreakDuration = TimeSpan.FromSeconds(15);

    options.TotalRequestTimeout.Timeout = TimeSpan.FromSeconds(10);
    options.AttemptTimeout.Timeout = TimeSpan.FromSeconds(2);
});
```

---

## 3. Custom Resilience Pipelines (`ResiliencePipeline`)

When building non-HTTP resilient operations (e.g., database retry, message bus publish, file I/O):

```csharp
builder.Services.AddResiliencePipeline("db-write-pipeline", builder =>
{
    builder
        .AddRetry(new RetryStrategyOptions
        {
            ShouldHandle = new PredicateBuilder().Handle<TimeoutException>().Handle<DbException>(),
            MaxRetryAttempts = 3,
            Delay = TimeSpan.FromMilliseconds(200),
            BackoffType = DelayBackoffType.Exponential,
            UseJitter = true
        })
        .AddCircuitBreaker(new CircuitBreakerStrategyOptions
        {
            FailureRatio = 0.5,
            SamplingDuration = TimeSpan.FromSeconds(10),
            MinimumThroughput = 8,
            BreakDuration = TimeSpan.FromSeconds(30)
        })
        .AddTimeout(TimeSpan.FromSeconds(5));
});

// Consuming in services:
public class OrderRepository(
    [FromKeyedServices("db-write-pipeline")] ResiliencePipeline pipeline,
    AppDbContext dbContext)
{
    public async Task PersistOrderAsync(Order order, CancellationToken ct)
    {
        await pipeline.ExecuteAsync(async token =>
        {
            dbContext.Orders.Add(order);
            await dbContext.SaveChangesAsync(token);
        }, ct);
    }
}
```

---

## 4. Health Checks: Liveness & Readiness Probes

Containerized and Kubernetes applications require split liveness and readiness probes:

```csharp
builder.Services.AddHealthChecks()
    .AddCheck("self", () => HealthCheckResult.Healthy(), tags: ["live"])
    .AddNpgSql(builder.Configuration.GetConnectionString("DefaultConnection")!, tags: ["ready"])
    .AddRedis(builder.Configuration.GetConnectionString("Redis")!, tags: ["ready"]);

var app = builder.Build();

// Liveness: Is the process responsive? (Restarts pod if unhealthy)
app.MapHealthChecks("/healthz/live", new HealthCheckOptions
{
    Predicate = check => check.Tags.Contains("live")
});

// Readiness: Are dependencies ready to receive traffic? (Removes pod from load balancer if unhealthy)
app.MapHealthChecks("/healthz/ready", new HealthCheckOptions
{
    Predicate = check => check.Tags.Contains("ready"),
    ResponseWriter = UIResponseWriter.WriteHealthCheckUIResponse // detailed JSON
});
```

