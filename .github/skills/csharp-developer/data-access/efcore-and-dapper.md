# Data Access: EF Core & Dapper (.NET 8 / .NET 9)

High-performance data persistence, query optimization, batch operations, and hybrid ORM strategies.

---

## 1. EF Core 8/9 Performance Optimization

### No-Tracking Queries
Always disable change tracking for read-only operations to avoid memory overhead and identity map lookups:

```csharp
// Standard read-only query
var products = await dbContext.Products
    .AsNoTracking()
    .Where(p => p.IsActive)
    .ToListAsync(ct);

// If querying self-referencing or repeated relational graphs without tracking:
var hierarchy = await dbContext.Categories
    .AsNoTrackingWithIdentityResolution()
    .Include(c => c.SubCategories)
    .ToListAsync(ct);
```

---

## 2. Preventing Cartesian Explosion with Split Queries

Loading multiple child collections in a single LINQ query generates massive SQL `LEFT JOIN` results (Cartesian multiplication), causing network saturation and memory spikes:

```csharp
// BAD: Generates huge cross-product SQL join
var order = await dbContext.Orders
    .Include(o => o.Items)
    .Include(o => o.Shipments)
    .Include(o => o.AuditLogs)
    .FirstOrDefaultAsync(o => o.Id == orderId, ct);

// GOOD: Execute separate targeted queries per collection
var order = await dbContext.Orders
    .AsSplitQuery()
    .Include(o => o.Items)
    .Include(o => o.Shipments)
    .Include(o => o.AuditLogs)
    .FirstOrDefaultAsync(o => o.Id == orderId, ct);
```

---

## 3. Bulk Updates & Deletes Without Entity Materialization

Prior to .NET 7/8, updating or deleting entities required loading them into memory first. Modern EF Core executes direct SQL commands:

```csharp
// Direct SQL UPDATE: UPDATE Orders SET Status = 'Archived' WHERE CreatedAt < @date
await dbContext.Orders
    .Where(o => o.CreatedAt < cutoffDate && o.Status == OrderStatus.Completed)
    .ExecuteUpdateAsync(setter => setter
        .SetProperty(o => o.Status, OrderStatus.Archived)
        .SetProperty(o => o.UpdatedAt, DateTime.UtcNow), ct);

// Direct SQL DELETE: DELETE FROM AuditLogs WHERE CreatedAt < @retentionLimit
await dbContext.AuditLogs
    .Where(a => a.CreatedAt < retentionLimit)
    .ExecuteDeleteAsync(ct);
```

---

## 4. `DbContext` Pooling

For high-throughput web APIs, creating and disposing `DbContext` instances puts pressure on the garbage collector. Use pooling:

```csharp
// Program.cs
builder.Services.AddDbContextPool<AppDbContext>(options =>
{
    options.UseNpgsql(builder.Configuration.GetConnectionString("DefaultConnection"), npgsqlOptions =>
    {
        npgsqlOptions.EnableRetryOnFailure(3);
    });
}, poolSize: 1024);
```

> **Warning:** When using DbContext pooling, your `DbContext` must not maintain mutable instance state across requests.

---

## 5. Dapper for High-Throughput Scenarios

When EF Core overhead is unacceptable or complex raw SQL queries are required, use Dapper with ADO.NET:

```csharp
public class OrderDapperRepository(IDbConnectionFactory connectionFactory)
{
    public async Task<OrderDetailsDto?> GetOrderDetailsAsync(Guid orderId, CancellationToken ct)
    {
        using var connection = await connectionFactory.CreateConnectionAsync(ct);

        const string sql = """
            SELECT o.id, o.order_number, o.created_at,
                   i.id, i.sku, i.quantity, i.unit_price
            FROM orders o
            LEFT JOIN order_items i ON o.id = i.order_id
            WHERE o.id = @OrderId;
            """;

        OrderDetailsDto? orderDto = null;

        await connection.QueryAsync<OrderDetailsDto, OrderItemDto, OrderDetailsDto>(
            new CommandDefinition(sql, new { OrderId = orderId }, cancellationToken: ct),
            (order, item) =>
            {
                orderDto ??= order;
                if (item is not null)
                {
                    orderDto.Items.Add(item);
                }
                return orderDto;
            },
            splitOn: "id");

        return orderDto;
    }
}
```

---

## 6. Sharing Transactions Between EF Core and Dapper

When an operation requires both EF Core unit-of-work and a fast Dapper bulk insert:

```csharp
await using var transaction = await dbContext.Database.BeginTransactionAsync(ct);
try
{
    // EF Core operation
    dbContext.Orders.Add(newOrder);
    await dbContext.SaveChangesAsync(ct);

    // Share existing DbTransaction with Dapper
    var dbTransaction = transaction.GetDbTransaction();
    var dbConnection = dbContext.Database.GetDbConnection();

    await dbConnection.ExecuteAsync(
        new CommandDefinition("INSERT INTO audit_log (order_id, action) VALUES (@Id, 'Created')", 
        new { newOrder.Id }, 
        transaction: dbTransaction, 
        cancellationToken: ct));

    await transaction.CommitAsync(ct);
}
catch
{
    await transaction.RollbackAsync(ct);
    throw;
}
```

