# Testing Best Practices (.NET 8 / .NET 9)

Robust unit, integration, and containerized testing using xUnit, NSubstitute, FluentAssertions, `WebApplicationFactory`, and Testcontainers.

---

## 1. Test Stack Selection

| Responsibility | Recommended Tool | Why |
| :--- | :--- | :--- |
| **Test Runner** | **xUnit** (v2/v3) | Standard in .NET ecosystem, parallel test execution by default. |
| **Mocking** | **NSubstitute** | Clean, refactoring-safe syntax; avoids legacy Moq issues. |
| **Assertions** | **FluentAssertions** | Highly expressive assertions with descriptive failure messages. |
| **API Integration** | `WebApplicationFactory<Program>` | In-memory integration testing of full ASP.NET Core pipelines. |
| **Real Infrastructure** | **Testcontainers.NET** | Ephemeral Docker containers for real Postgres, Redis, RabbitMQ. |

---

## 2. Fast Unit Tests with NSubstitute & FluentAssertions

```csharp
public class OrderServiceTests
{
    private readonly IOrderRepository _repository = Substitute.For<IOrderRepository>();
    private readonly IPaymentGateway _paymentGateway = Substitute.For<IPaymentGateway>();
    private readonly ILogger<OrderService> _logger = Substitute.For<ILogger<OrderService>>();
    private readonly OrderService _sut; // System Under Test

    public OrderServiceTests()
    {
        _sut = new OrderService(_repository, _paymentGateway, _logger);
    }

    [Fact]
    public async Task ProcessOrderAsync_WhenPaymentFails_ShouldThrowAndNotSave()
    {
        // Arrange
        var request = new CreateOrderRequest(Guid.NewGuid(), 150.00m);
        _paymentGateway.ChargeAsync(request.CustomerId, request.Amount, Arg.Any<CancellationToken>())
            .Returns(PaymentResult.Failed("Insufficient funds"));

        // Act
        Func<Task> act = async () => await _sut.ProcessOrderAsync(request);

        // Assert
        await act.Should().ThrowAsync<PaymentFailedException>()
            .WithMessage("*Insufficient funds*");

        await _repository.DidNotReceiveWithAnyArgs().SaveAsync(default!);
    }
}
```

---

## 3. Integration Testing with `WebApplicationFactory` & Testcontainers

Avoid in-memory databases like EF Core InMemory; use real disposable containers via Testcontainers:

```csharp
public class ApiIntegrationTestFixture : IAsyncLifetime
{
    private readonly PostgreSqlContainer _dbContainer = new PostgreSqlBuilder()
        .WithImage("postgres:16-alpine")
        .WithDatabase("test_db")
        .WithUsername("postgres")
        .WithPassword("postgres")
        .Build();

    public HttpClient Client { get; private set; } = null!;
    public WebApplicationFactory<Program> Factory { get; private set; } = null!;

    public async Task InitializeAsync()
    {
        await _dbContainer.StartAsync();

        Factory = new WebApplicationFactory<Program>().WithWebHostBuilder(builder =>
        {
            builder.ConfigureServices(services =>
            {
                // Replace production DbContext registration with Testcontainer connection
                services.RemoveAll<DbContextOptions<AppDbContext>>();
                services.AddDbContext<AppDbContext>(options =>
                    options.UseNpgsql(_dbContainer.GetConnectionString()));
            });
        });

        Client = Factory.CreateClient();

        // Run migrations
        using var scope = Factory.Services.CreateScope();
        var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
        await db.Database.MigrateAsync();
    }

    public async Task DisposeAsync()
    {
        Client.Dispose();
        await Factory.DisposeAsync();
        await _dbContainer.DisposeAsync();
    }
}

// Test Class
public class CustomerApiTests(ApiIntegrationTestFixture fixture) : IClassFixture<ApiIntegrationTestFixture>
{
    [Fact]
    public async Task CreateCustomer_WithValidPayload_Returns201Created()
    {
        // Arrange
        var request = new CreateCustomerRequest("Jane Doe", "jane@example.com");

        // Act
        var response = await fixture.Client.PostAsJsonAsync("/api/v1/customers", request);

        // Assert
        response.StatusCode.Should().Be(HttpStatusCode.Created);
        var created = await response.Content.ReadFromJsonAsync<CustomerDto>();
        created.Should().NotBeNull();
        created!.Email.Should().Be("jane@example.com");
    }
}
```

---

## 4. Parameterized Tests (`[Theory]`)

Use `[Theory]` and `[InlineData]` or `[MemberData]` for boundary and edge-case testing:

```csharp
public class DiscountCalculatorTests
{
    [Theory]
    [InlineData(0, 0)]
    [InlineData(49.99, 0)]
    [InlineData(50.00, 5)]
    [InlineData(100.00, 10)]
    [InlineData(500.00, 20)]
    public void CalculateDiscount_CalculatesTierAccurately(decimal subtotal, decimal expectedDiscountPercent)
    {
        var discount = DiscountCalculator.GetPercentage(subtotal);
        discount.Should().Be(expectedDiscountPercent);
    }
}
```
