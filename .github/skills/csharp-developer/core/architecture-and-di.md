# Architecture & Dependency Injection (.NET 8 / .NET 9)

Architectural patterns, modular vertical slices, and enterprise dependency injection mechanics in modern C#.

---

## 1. Clean Architecture vs. Vertical Slice Architecture

### Vertical Slice Architecture (Feature-Centric)
Organize code around user interactions / business capabilities rather than technical layers. Every slice encapsulates its request, validation, database operation, and response:

```
Features/
  Orders/
    CreateOrder/
      CreateOrderEndpoint.cs
      CreateOrderCommand.cs
      CreateOrderValidator.cs
      CreateOrderHandler.cs
    GetOrderById/
      GetOrderByIdEndpoint.cs
      GetOrderByIdQuery.cs
      GetOrderByIdHandler.cs
```

#### MediatR / Handler Pattern
```csharp
public record CreateOrderCommand(Guid CustomerId, List<OrderItemDto> Items) : IRequest<Result<Guid>>;

public class CreateOrderHandler(
    AppDbContext dbContext,
    IInventoryService inventory,
    ILogger<CreateOrderHandler> logger) : IRequestHandler<CreateOrderCommand, Result<Guid>>
{
    public async Task<Result<Guid>> Handle(CreateOrderCommand request, CancellationToken ct)
    {
        var isAvailable = await inventory.CheckStockAsync(request.Items, ct);
        if (!isAvailable)
        {
            return Result.Failure<Guid>(OrderErrors.InsufficientStock);
        }

        var order = Order.Create(request.CustomerId, request.Items);
        dbContext.Orders.Add(order);
        await dbContext.SaveChangesAsync(ct);

        logger.LogInformation("Order {OrderId} successfully placed", order.Id);
        return Result.Success(order.Id);
    }
}
```

---

## 2. Dependency Injection Lifetimes & Captive Dependencies

| Lifetime | Method | Usage | Gotcha |
| :--- | :--- | :--- | :--- |
| **Transient** | `AddTransient<T>` | Lightweight, stateless utilities, validators | Created on every injection. |
| **Scoped** | `AddScoped<T>` | Unit of Work (`DbContext`), current User/Tenant context | Created once per HTTP request / scope. |
| **Singleton** | `AddSingleton<T>` | Caches, telemetry, thread-safe background workers | Never inject a Scoped service directly into a Singleton! |

### Preventing the Captive Dependency Anti-Pattern
A Singleton service capturing a Scoped service (`DbContext`) causes memory leaks, concurrency violations, and stale state.

```csharp
// Program.cs - Enforce strict scope validation in Development & Staging
var builder = WebApplication.CreateBuilder(args);

builder.Host.UseDefaultServiceProvider((context, options) =>
{
    var isDev = context.HostingEnvironment.IsDevelopment();
    options.ValidateScopes = isDev;
    options.ValidateOnBuild = true; // Catches missing or captive DI registrations at startup
});
```

### Safely Consuming Scoped Services in Singleton / Background Tasks
```csharp
public class OrderProcessingWorker(
    IServiceScopeFactory scopeFactory,
    ILogger<OrderProcessingWorker> logger) : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        while (!stoppingToken.IsCancellationRequested)
        {
            // Explicitly create an asynchronous scope
            await using (var scope = scopeFactory.CreateAsyncScope())
            {
                var dbContext = scope.ServiceProvider.GetRequiredService<AppDbContext>();
                await ProcessPendingOrdersAsync(dbContext, stoppingToken);
            }

            await Task.Delay(TimeSpan.FromSeconds(30), stoppingToken);
        }
    }
}
```

---

## 3. Options Pattern: Validation and Startup Checks

Always strongly type configuration sections and validate them at application startup to fail fast on misconfigurations:

```csharp
public sealed class PaymentOptions
{
    public const string SectionName = "PaymentGateway";

    [Required, Url]
    public required string BaseUrl { get; init; }

    [Required, MinLength(16)]
    public required string ApiKey { get; init; }

    [Range(1, 60)]
    public int TimeoutSeconds { get; init; } = 30;
}

// Program.cs registration
builder.Services
    .AddOptions<PaymentOptions>()
    .BindConfiguration(PaymentOptions.SectionName)
    .ValidateDataAnnotations()
    .ValidateOnStart(); // Crashes immediately on boot if configuration is invalid
```

### Lifetime of Options
- `IOptions<T>`: Singleton; bound once on startup.
- `IOptionsSnapshot<T>`: Scoped; re-evaluates configuration per request (useful when configs reload).
- `IOptionsMonitor<T>`: Singleton; supports real-time change notifications (`OnChange`).

---

## 4. Resilient Typed `HttpClient` Factory

Prevent socket exhaustion and DNS caching bugs by registering typed HTTP clients:

```csharp
builder.Services.AddHttpClient<IPaymentGateway, StripePaymentGateway>((sp, client) =>
{
    var options = sp.GetRequiredService<IOptions<PaymentOptions>>().Value;
    client.BaseAddress = new Uri(options.BaseUrl);
    client.Timeout = TimeSpan.FromSeconds(options.TimeoutSeconds);
    client.DefaultRequestHeaders.Add("User-Agent", "App-Backend/2.0");
});
```
