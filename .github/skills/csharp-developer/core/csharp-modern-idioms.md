# Modern C# Language Idioms (C# 12 / C# 13, .NET 8 / .NET 9)

Idiomatic syntax, language features, and compiler capabilities for modern .NET development.

---

## 1. Primary Constructors (Classes & Structs)

Declare constructor parameters directly in the class header, eliminating repetitive private field declarations and constructor assignment ceremonies:

```csharp
// Modern C# 12+ Primary Constructor
public class OrderService(
    IOrderRepository repository,
    IPaymentGateway paymentGateway,
    ILogger<OrderService> logger) : IOrderService
{
    public async Task<OrderResponse> ProcessOrderAsync(CreateOrderRequest request, CancellationToken ct = default)
    {
        ArgumentNullException.ThrowIfNull(request);
        logger.LogInformation("Processing order for customer {CustomerId}", request.CustomerId);

        var order = request.ToEntity();
        await repository.SaveAsync(order, ct);
        return order.ToResponse();
    }
}
```

---

## 2. Collection Expressions & Spread Operator (`[..]`)

Unified syntax for initializing arrays, lists, spans, and read-only collections with zero boilerplate:

```csharp
// C# 12+ Collection Expressions
int[] numbers = [1, 2, 3, 4, 5];
List<string> activeRoles = ["Admin", "Manager", "User"];
ReadOnlySpan<byte> magicHeader = [0xFF, 0xD8, 0xFF];

// Spread operator combines collections efficiently
string[] defaultScopes = ["openid", "profile"];
string[] customScopes = ["api.read", "api.write"];
string[] allScopes = [.. defaultScopes, .. customScopes, "offline_access"];
```

---

## 3. Immutability: Records, Record Structs & Required Members

Model domain DTOs, value objects, and events with value equality and compiler-enforced immutability:

```csharp
// Record Class (Reference type with value-based equality)
public record UserDto(Guid Id, string Email, string Role);

// Record Struct (Zero heap allocation value object for high-throughput pipelines)
public readonly record struct Money(decimal Amount, string Currency)
{
    public static Money Zero(string currency) => new(0m, currency);
}

// Required properties with init-only setters
public class CreateCustomerCommand
{
    public required string Email { get; init; }
    public required string FullName { get; init; }
    public string? PhoneNumber { get; init; }
}
```

---

## 4. Advanced Pattern Matching & Switch Expressions

Express complex conditional domain rules concisely without nested `if`/`else` trees:

```csharp
public static decimal CalculateTax(Order order) => order switch
{
    // Property pattern with relational condition
    { Country: "US", State: "CA", Amount: >= 1000m } => order.Amount * 0.09m,
    { Country: "US", State: "CA" } => order.Amount * 0.0725m,
    { Country: "US", State: "NY" } => order.Amount * 0.08875m,
    
    // Positional pattern on tuple or type pattern
    { Country: "EU" } and not { IsB2B: true } => order.Amount * 0.20m,
    { Country: "EU", IsB2B: true } => 0.0m, // Reverse charge
    
    // Discard pattern (default fallback)
    _ => 0.0m
};
```

---

## 5. Frozen Collections (.NET 8+)

For read-only lookup dictionaries or sets configured at application startup, use `FrozenDictionary` and `FrozenSet`. They optimize memory layout and hash lookups for maximum read performance:

```csharp
using System.Collections.Frozen;

public class CountryRegistry
{
    // Read operations are 2-3x faster than standard Dictionary
    private static readonly FrozenDictionary<string, CountryInfo> Countries =
        new Dictionary<string, CountryInfo>
        {
            ["US"] = new("United States", "USD"),
            ["DE"] = new("Germany", "EUR"),
            ["JP"] = new("Japan", "JPY")
        }.ToFrozenDictionary(StringComparer.OrdinalIgnoreCase);

    public static CountryInfo? Find(string code) => Countries.GetValueOrDefault(code);
}
```

