# Dependency Injection Patterns & Architecture in Java & Spring

Comprehensive architectural guide to Dependency Injection (DI), Inversion of Control (IoC), bean scopes, and lifecycle management in modern Java and Spring Boot.

---

## 1. Core Principles: IoC vs. DIP vs. DI

| Term | Definition | Role in System Architecture |
| :--- | :--- | :--- |
| **Inversion of Control (IoC)** | General architectural principle where the framework controls program execution flow rather than custom code. | The framework calls your code (Hollywood Principle: *"Don't call us, we'll call you"*). |
| **Dependency Inversion Principle (DIP)** | High-level modules should not depend on low-level modules; both should depend on abstractions (interfaces). | Decouples domain logic from concrete database or network clients. |
| **Dependency Injection (DI)** | A specific design pattern implementing IoC: an external entity (assembler or container) supplies dependencies to an object. | Eliminates `new ConcreteService()` inside business classes. |

---

## 2. The Three Injection Styles

### 2.1 Constructor Injection (Mandatory Standard)
Dependencies are provided through the class constructor.

```java
@Service
public class OrderService {
    private final OrderRepository repository;
    private final PaymentClient paymentClient;

    // Explicit constructor (or Lombok @RequiredArgsConstructor)
    public OrderService(OrderRepository repository, PaymentClient paymentClient) {
        this.repository = Objects.requireNonNull(repository, "repository required");
        this.paymentClient = Objects.requireNonNull(paymentClient, "paymentClient required");
    }
}
```

**Why Constructor Injection is Mandatory**:
1. **Immutability**: Dependencies are stored in `private final` fields.
2. **Fail-Fast at Startup**: Missing dependencies cause immediate instantiation failure at startup (`NoSuchBeanDefinitionException`), preventing silent runtime `NullPointerException`s.
3. **Pure Unit Testing**: Can be instantiated in vanilla JUnit tests (`new OrderService(mockRepo, mockPayment)`) without needing Spring Context or `@ExtendWith(SpringExtension.class)`.
4. **Detects God Classes Early**: If a constructor takes 8+ arguments, it immediately signals a Single Responsibility Principle (SRP) violation.

---

### 2.2 Field Injection (`@Autowired` on Fields) — STRICT ANTI-PATTERN

```java
// ❌ ANTI-PATTERN: DO NOT USE IN PRODUCTION CODE
@Service
public class BadOrderService {
    @Autowired
    private OrderRepository repository;
}
```

**Why Field Injection is Banned**:
- **Cannot be made `final`**: Objects are mutable and can be modified after initialization.
- **Hides Dependencies**: The class hides what it needs to function; users calling `new BadOrderService()` find all fields are `null`.
- **Requires Spring or Reflection to Test**: Cannot test without firing up a heavyweight Spring context or using dirty reflection hacks.
- **Masks Circular Dependencies**: Makes circular dependencies easy to introduce accidentally.

---

### 2.3 Setter / Method Injection (Optional Dependencies Only)
Used strictly for optional dependencies or configurable properties that have sensible defaults:

```java
@Component
public class MetricsReporter {
    private MetricsFilter filter = MetricsFilter.ALLOW_ALL; // sensible default

    @Autowired(required = false)
    public void setFilter(MetricsFilter filter) {
        this.filter = filter;
    }
}
```

---

## 3. Spring Bean Lifetimes & Scope Management

| Scope | Annotation | Lifecycle Duration | Thread Safety Requirement |
| :--- | :--- | :--- | :--- |
| **Singleton** (Default) | `@Scope("singleton")` | Exactly one instance per `ApplicationContext`. | **Mandatory Thread-Safe**: Accessed concurrently by all requests. Must be stateless. |
| **Prototype** | `@Scope("prototype")` | A new instance is created every time the bean is requested. | State can be mutable if confined to one thread. |
| **Request** | `@RequestScope` | One instance per HTTP request lifecycle. Destroyed when request completes. | Safe for current HTTP request state (tenant, user auth). |
| **Session** | `@SessionScope` | One instance per HTTP session. | Session-bound state (cart, user preferences). |

---

## 4. The Captive Dependency Pitfall & Solutions

A **Captive Dependency** occurs when a bean with a longer lifetime captures a bean with a shorter lifetime.

```text
❌ CAPTIVE DEPENDENCY BUG:
[ SingletonBean ] (Created once at startup)
       └──> Injected with: [ RequestScopedUserContext ] (Created per HTTP request)
```
*Failure*: The Singleton holds onto the first request's `UserContext` forever! Subsequent requests from other users see the original user's data, causing severe data leaks and race conditions.

### Solution A: Scoped Proxies (`proxyMode`)
Spring injects a dynamic CGLIB proxy instead of the real target. When the singleton calls a method on the proxy, the proxy looks up the actual bean for the *current thread's request*:
```java
@Component
@RequestScope(proxyMode = ScopedProxyMode.TARGET_CLASS)
public class UserContext {
    private String tenantId;
    // getters and setters
}

@Service
public class OrderService { // Singleton
    private final UserContext userContext; // Safe! Injected with a dynamic proxy

    public OrderService(UserContext userContext) {
        this.userContext = userContext;
    }
}
```

### Solution B: `ObjectProvider<T>` / `Provider<T>`
For on-demand creation of prototype beans:
```java
@Service
public class ReportGenerator {
    private final ObjectProvider<ReportWorker> workerProvider;

    public ReportGenerator(ObjectProvider<ReportWorker> workerProvider) {
        this.workerProvider = workerProvider;
    }

    public void generateReports(List<ReportSpec> specs) {
        for (var spec : specs) {
            // Generates a brand new ReportWorker instance for each task
            ReportWorker worker = workerProvider.getObject();
            worker.execute(spec);
        }
    }
}
```

---

## 5. Factory Injection & Assisted Injection

When an object requires both **container-managed dependencies** (services, repositories) AND **runtime parameters** (user ID, transaction payload):

```java
// Target Domain Class
public class PaymentTransaction {
    private final PaymentGateway gateway; // container managed
    private final BigDecimal amount;       // runtime parameter
    private final UUID transactionId;      // runtime parameter

    public PaymentTransaction(PaymentGateway gateway, BigDecimal amount, UUID id) {
        this.gateway = gateway;
        this.amount = amount;
        this.transactionId = id;
    }

    public void process() { gateway.charge(amount, transactionId); }
}

// Factory Pattern with DI
@Component
public class PaymentTransactionFactory {
    private final PaymentGateway gateway;

    public PaymentTransactionFactory(PaymentGateway gateway) {
        this.gateway = gateway;
    }

    public PaymentTransaction create(BigDecimal amount, UUID transactionId) {
        return new PaymentTransaction(this.gateway, amount, transactionId);
    }
}
```

---

## 6. Pure Dependency Injection (No Framework Overhead)

In CLI tools, micro-benchmarks, or ultra-low-latency engines, avoid Spring container overhead. Construct dependencies manually in a **Composition Root**:

```java
public class Application {
    public static void main(String[] args) {
        // Composition Root: Pure DI wiring at the application entry point
        DatabaseConfig config = DatabaseConfig.fromEnv();
        DataSource dataSource = new HikariDataSource(config.toHikariConfig());
        UserRepository userRepository = new JdbcUserRepository(dataSource);
        PasswordEncoder passwordEncoder = new Argon2PasswordEncoder();
        
        UserService userService = new UserService(userRepository, passwordEncoder);
        ApiServer server = new ApiServer(userService, 8080);
        server.start();
    }
}
```

