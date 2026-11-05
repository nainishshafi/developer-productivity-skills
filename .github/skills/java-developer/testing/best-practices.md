# Java & Spring Boot Testing Best Practices

A pragmatic guide for writing fast, reliable, and maintainable tests across unit, slice, and integration levels.

---

## 1. Test Pyramid & Scope

| Level | Scope | Frameworks / Tools | Execution Speed |
| :--- | :--- | :--- | :--- |
| **Unit Tests** | Single class / pure functions in isolation | JUnit 5, AssertJ, Mockito | Milliseconds (no Spring context) |
| **Slice Tests** | Single architectural layer | `@WebMvcTest`, `@DataJpaTest`, `@JsonTest` | 1–3 seconds (partial context) |
| **Integration Tests** | End-to-end component flow + real infrastructure | `@SpringBootTest`, Testcontainers | Seconds (full context + Docker) |
| **Architecture Tests**| Package structure and dependency rules | ArchUnit | Fast (bytecode inspection) |

**Rule of thumb**: Push 70–80% of test logic into unit tests. Reserve integration tests for wiring, transactions, and real database contracts.

---

## 2. Unit Testing (JUnit 5 + AssertJ + Mockito)

### Naming & Structure
Use behavior-driven names and the **Arrange-Act-Assert (AAA)** or **Given-When-Then** pattern:
```java
@Test
void shouldCalculateDiscount_whenCustomerIsVip() {
    // Arrange (Given)
    var customer = CustomerFixture.vipCustomer();
    var order = OrderFixture.withAmount(new BigDecimal("100.00"));

    // Act (When)
    var discountedAmount = pricingService.applyDiscount(order, customer);

    // Assert (Then)
    assertThat(discountedAmount).isEqualByComparingTo("80.00");
}
```

### AssertJ Best Practices
- **Fluent & Readable**: Prefer `assertThat(actual).isEqualTo(expected)` over JUnit's `assertEquals`.
- **Collections**: Check elements cleanly without brittle index access:
  ```java
  assertThat(users)
      .hasSize(2)
      .extracting(User::email)
      .containsExactlyInAnyOrder("a@test.com", "b@test.com");
  ```
- **Multiple Assertions**: Use `assertAll` or `SoftAssertions` so all failures report at once:
  ```java
  assertAll(
      () -> assertThat(user.name()).isEqualTo("Alice"),
      () -> assertThat(user.role()).isEqualTo(Role.ADMIN)
  );
  ```

### Mockito Guidelines
- **Use Strict Stubs**: Enable `@ExtendWith(MockitoExtension.class)` (default in Mockito 5+). It fails on unused stubbings.
- **Mock Roles, Not Data**: Never mock DTOs, records, entities, or collections. Mock external dependencies (gateways, remote clients, repositories).
- **Prefer Constructor Injection**: Pass mocks into constructors directly in `@BeforeEach` or let `@InjectMocks` handle it.
- **Verify Specific Interactions**:
  ```java
  verify(notificationService).sendWelcomeEmail(user.email());
  verifyNoMoreInteractions(notificationService);
  ```

### Parameterized Tests
Replace copy-pasted test methods with `@ParameterizedTest`:
```java
@ParameterizedTest
@CsvSource({
    "100.00, VIP,    80.00",
    "100.00, REGULAR, 100.00",
    "0.00,   VIP,    0.00"
})
void shouldApplyDiscountByCustomerType(BigDecimal input, CustomerType type, BigDecimal expected) {
    assertThat(pricingService.calculate(input, type)).isEqualByComparingTo(expected);
}
```

---

## 3. Test Data & Fixtures

- **Object Mother / Test Data Builders**: Centralize test data creation with sensible defaults; override only fields relevant to the test case:
  ```java
  public final class OrderFixture {
      public static Order.Builder aValidOrder() {
          return Order.builder()
              .id(UUID.randomUUID())
              .amount(BigDecimal.TEN)
              .status(OrderStatus.PENDING);
      }
  }
  // In test:
  var order = OrderFixture.aValidOrder().amount(new BigDecimal("500.00")).build();
  ```
- **Zero Shared Mutable State**: Never mutate static collections or shared fixture objects across tests. Each test gets fresh instances.

---

## 4. Time, Async & Concurrency Testing

### Controllable Time
Never call `Instant.now()` or `LocalDate.now()` directly in production code. Inject a `Clock` bean:
```java
// Production service
public class TokenService {
    private final Clock clock;
    public boolean isExpired(Token t) {
        return t.expiresAt().isBefore(Instant.now(clock));
    }
}

// In test: freeze time
Clock fixedClock = Clock.fixed(Instant.parse("2026-01-01T10:00:00Z"), ZoneOffset.UTC);
var service = new TokenService(fixedClock);
```

### Asynchronous & Event-Driven Testing
Never use `Thread.sleep()` to wait for async tasks. Use **Awaitility**:
```java
Awaitility.await()
    .atMost(Duration.ofSeconds(2))
    .pollInterval(Duration.ofMillis(50))
    .untilAsserted(() -> {
        assertThat(orderRepository.findById(orderId))
            .isPresent()
            .get()
            .extracting(Order::status)
            .isEqualTo(OrderStatus.COMPLETED);
    });
```

---

## 5. Spring Boot Testing Strategy

### 1. Slice Tests (Targeted & Fast)
Test specific web or persistence layers without loading the entire application context:
- **`@WebMvcTest(OrderController.class)`**: Tests HTTP routing, JSON serialization, and `@Valid` constraints.
  ```java
  @WebMvcTest(OrderController.class)
  class OrderControllerTest {
      @Autowired private MockMvc mockMvc;
      @MockitoBean private OrderService orderService; // Spring Boot 3.4+

      @Test
      void shouldReturn201_whenPayloadIsValid() throws Exception {
          when(orderService.create(any())).thenReturn(UUID.randomUUID());

          mockMvc.perform(post("/orders")
                  .contentType(MediaType.APPLICATION_JSON)
                  .content("""{"amount": 100.00}"""))
              .andExpect(status().isCreated());
      }
  }
  ```
- **`@DataJpaTest`**: Tests Spring Data repositories, custom JPQL queries, and database constraints with an active transaction that auto-rolls back.

### 2. Integration Tests with Testcontainers
Test against the real production database engine (PostgreSQL, MySQL) instead of in-memory H2:
```java
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@Testcontainers
class OrderIntegrationTest {

    @Container
    @ServiceConnection // Boot 3.1+ auto-configures JDBC properties
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16-alpine");

    @Autowired private TestRestTemplate restTemplate;

    @Test
    void shouldPersistAndRetrieveOrder() {
        var response = restTemplate.postForEntity("/orders", validPayload(), OrderDto.class);
        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.CREATED);
    }
}
```

### 3. Protecting Context & Container Caching (Speed Up Test Suites)
The Spring test runner caches application contexts across tests. A rebuild occurs whenever context configurations differ:
- **Avoid `@DirtiesContext`**: It forces Spring to discard the context and spin up a fresh one. Clean up test data via DB transactions, `JdbcTestUtils`, or `@BeforeEach` cleanup instead.
- **Share Testcontainers Instances**: Placing `@Testcontainers` + `@Container` on every test class boots a new Docker container per class. Define a shared `static` container in a base integration test class (or `@TestConfiguration` bean with `@ServiceConnection`) so the container starts once per test run.
- **Standardize Mock Sets**: Group `@MockitoBean` definitions into base test classes or configurations rather than introducing unique mock combinations per test file.
- **Prefer `MockMvcTester` (Spring 6.2 / Boot 3.4+)**: Provides AssertJ-native assertions (`assertThat(mvc.post().uri("/orders")...).hasStatus(HttpStatus.CREATED)`) without checked exceptions.

---

## 6. Architecture Testing (ArchUnit)

Ensure architectural rules and layering are automatically validated on every build:
```java
@AnalyzeClasses(packages = "com.example.app")
class ArchitectureTest {

    @ArchTest
    static final ArchRule controllers_should_not_depend_on_repositories =
        noClasses().that().resideInAPackage("..controller..")
            .should().dependOnClassesThat().resideInAPackage("..repository..");

    @ArchTest
    static final ArchRule services_should_be_transactional_at_boundary =
        classes().that().resideInAPackage("..service..")
            .should().onlyBeAccessed().byClassesThat().resideInAnyPackage("..controller..", "..service..");
}
```

---

## 7. Common Anti-Patterns to Avoid

- **Testing Implementation Details**: Don't assert private method calls or internal variable states. Test external behaviors and contracts through public APIs.
- **Over-Mocking**: If you are mocking 8 different classes to test one method, the class under test violates Single Responsibility (SRP). Refactor before testing.
- **Hardcoded File Paths & Hostnames**: Always use dynamic ports (`RANDOM_PORT`), temp directories (`@TempDir`), or virtual file abstractions.
- **Logic Inside Tests**: Keep tests declarative. If a test contains `if`, `switch`, or loop statements, it needs to be simplified or split into parameterized tests.

