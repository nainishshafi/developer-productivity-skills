# ASP.NET Core: Minimal APIs & MVC Controllers (.NET 8 / .NET 9)

High-performance HTTP endpoint design, typed results, OpenAPI compliance, and middleware pipeline mechanics.

---

## 1. Minimal APIs vs. MVC Controllers

| Attribute | Minimal APIs | MVC Controllers |
| :--- | :--- | :--- |
| **Performance** | Lowest allocations, fastest routing, AOT-friendly | Higher reflection overhead and filter allocations |
| **Best For** | Microservices, REST APIs, high-throughput endpoints | Large enterprise monoliths, Razor Views, server-rendered apps |
| **Structure** | Route Groups, endpoint extension methods | Controller classes inheriting `ControllerBase` |

---

## 2. Idiomatic Minimal APIs with `TypedResults` & Route Groups

Prefer `TypedResults` over `Results` because `TypedResults` provides compile-time type safety and automatically decorates OpenAPI/Swagger specifications:

```csharp
public static class CustomerEndpoints
{
    public static RouteGroupBuilder MapCustomerEndpoints(this RouteGroupBuilder group)
    {
        group.MapGet("/", GetAllCustomers)
             .WithName("GetAllCustomers")
             .Produces<List<CustomerDto>>(StatusCodes.Status200OK);

        group.MapGet("/{id:guid}", GetCustomerById)
             .WithName("GetCustomerById");

        group.MapPost("/", CreateCustomer)
             .WithName("CreateCustomer")
             .AddEndpointFilter<ValidationFilter<CreateCustomerRequest>>();

        return group;
    }

    private static async Task<Ok<List<CustomerDto>>> GetAllCustomers(
        ICustomerService service, 
        CancellationToken ct)
    {
        var customers = await service.ListAllAsync(ct);
        return TypedResults.Ok(customers);
    }

    private static async Task<Results<Ok<CustomerDto>, NotFound>> GetCustomerById(
        Guid id, 
        ICustomerService service, 
        CancellationToken ct)
    {
        var customer = await service.FindByIdAsync(id, ct);
        return customer is not null 
            ? TypedResults.Ok(customer) 
            : TypedResults.NotFound();
    }

    private static async Task<CreatedAtRoute<CustomerDto>> CreateCustomer(
        CreateCustomerRequest request, 
        ICustomerService service, 
        CancellationToken ct)
    {
        var created = await service.CreateAsync(request, ct);
        return TypedResults.CreatedAtRoute(created, "GetCustomerById", new { id = created.Id });
    }
}

// In Program.cs:
app.MapGroup("/api/v1/customers")
   .MapCustomerEndpoints()
   .RequireAuthorization()
   .WithTags("Customers");
```

---

## 3. RFC 7807 Global Error Handling (`IExceptionHandler`)

In .NET 8+, avoid custom middleware try-catch blocks for global exceptions. Implement `IExceptionHandler`:

```csharp
public sealed class GlobalExceptionHandler(ILogger<GlobalExceptionHandler> logger) : IExceptionHandler
{
    public async ValueTask<bool> TryHandleAsync(
        HttpContext httpContext, 
        Exception exception, 
        CancellationToken cancellationToken)
    {
        logger.LogError(exception, "Unhandled exception occurred: {Message}", exception.Message);

        var problemDetails = new ProblemDetails
        {
            Status = exception switch
            {
                ValidationException => StatusCodes.Status400BadRequest,
                KeyNotFoundException => StatusCodes.Status404NotFound,
                UnauthorizedAccessException => StatusCodes.Status401Unauthorized,
                _ => StatusCodes.Status500InternalServerError
            },
            Title = exception switch
            {
                ValidationException => "Bad Request",
                KeyNotFoundException => "Resource Not Found",
                UnauthorizedAccessException => "Unauthorized",
                _ => "Server Error"
            },
            Detail = exception.Message,
            Instance = httpContext.Request.Path
        };

        httpContext.Response.StatusCode = problemDetails.Status.Value;
        await httpContext.Response.WriteAsJsonAsync(problemDetails, cancellationToken);

        return true; // Marked as handled
    }
}

// Program.cs registration
builder.Services.AddExceptionHandler<GlobalExceptionHandler>();
builder.Services.AddProblemDetails();

// Pipeline registration (must be near the top)
app.UseExceptionHandler();
```

---

## 4. Output Caching (.NET 8+)

Output caching caches entire HTTP responses across requests, bypassing endpoint execution:

```csharp
builder.Services.AddOutputCache(options =>
{
    options.AddBasePolicy(builder => builder.Expire(TimeSpan.FromMinutes(2)));
    options.AddPolicy("CatalogCache", builder => 
        builder.Expire(TimeSpan.FromMinutes(10))
               .Tag("catalog")
               .SetVaryByQuery("page", "category"));
});

// Endpoint application
app.MapGet("/api/products", GetProducts)
   .CacheOutput("CatalogCache");

// Evict cache on mutation
app.MapPost("/api/products", async (IOutputCacheStore cacheStore, ProductDto product) =>
{
    await SaveProductAsync(product);
    await cacheStore.EvictByTagAsync("catalog", default);
    return TypedResults.Created($"/api/products/{product.Id}", product);
});
```

---

## 5. Correct Middleware Pipeline Ordering

Middleware executes in the order it is defined. Incorrect order breaks authentication, CORS, or error handling:

```csharp
var app = builder.Build();

// 1. Exception handling & Diagnostics (First)
app.UseExceptionHandler();
if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}

// 2. Security headers & HTTPS redirection
app.UseHttpsRedirection();
app.UseHsts();

// 3. Routing
app.UseRouting();

// 4. CORS (Must be after UseRouting and before UseAuthentication)
app.UseCors("AllowedOrigins");

// 5. Authentication & Authorization (Authentication BEFORE Authorization)
app.UseAuthentication();
app.UseAuthorization();

// 6. Caching & Compression
app.UseOutputCache();
app.UseResponseCompression();

// 7. Endpoints execution
app.MapControllers();
app.MapGroup("/api").MapEndpoints();

app.Run();
```

