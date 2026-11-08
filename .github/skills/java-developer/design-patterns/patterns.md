# Modern Java Design Patterns & Architectural Idioms

Comprehensive reference for implementing Gang of Four (GoF) and Enterprise Design Patterns in modern Java (17/21/25 LTS), leveraging modern language capabilities (`record`, `sealed` types, pattern matching, lambdas, and Virtual Threads).

---

## 1. Creational Patterns

### 1.1 Builder Pattern
**Intent**: Separate the construction of a complex object from its representation.

- **When to Use**: Objects with 4+ optional parameters, configuration objects, or immutable entities where constructor overloading leads to "telescoping constructor" anti-patterns.
- **Modern Idiom**:
  - For immutable data carriers, prefer **Lombok `@Builder`** or explicit static inner builders.
  - When all fields are required, prefer a **Java `record`** with compact constructor validation instead of a Builder.

```java
public final class DatabaseConfig {
    private final String url;
    private final String username;
    private final String password;
    private final int poolSize;
    private final Duration timeout;

    private DatabaseConfig(Builder builder) {
        this.url = Objects.requireNonNull(builder.url, "url required");
        this.username = Objects.requireNonNull(builder.username, "username required");
        this.password = Objects.requireNonNull(builder.password, "password required");
        this.poolSize = builder.poolSize;
        this.timeout = builder.timeout;
    }

    public static Builder builder() { return new Builder(); }

    public static final class Builder {
        private String url;
        private String username;
        private String password;
        private int poolSize = 10; // sensible default
        private Duration timeout = Duration.ofSeconds(30);

        public Builder url(String url) { this.url = url; return this; }
        public Builder credentials(String user, String pass) { 
            this.username = user; this.password = pass; return this; 
        }
        public Builder poolSize(int size) { this.poolSize = size; return this; }
        public Builder timeout(Duration timeout) { this.timeout = timeout; return this; }

        public DatabaseConfig build() { return new DatabaseConfig(this); }
    }
}
```

### 1.2 Static Factory Method Pattern
**Intent**: Provide expressive, named constructors and control instance allocation (caching, returning subclasses).

- **When to Use**: Clarifying intent, caching immutable singletons (`Boolean.valueOf`), returning unmodifiable empty collections (`List.of()`), or returning different subtype implementations based on inputs.

```java
public record User(UUID id, String email, UserRole role) {
    // Expressive static factories replacing ambiguous constructor overloads
    public static User ofGuest() {
        return new User(UUID.randomUUID(), "guest@system.local", UserRole.GUEST);
    }

    public static User ofRegistered(String email) {
        return new User(UUID.randomUUID(), Objects.requireNonNull(email), UserRole.CUSTOMER);
    }
}
```

### 1.3 Factory Method & Abstract Factory
**Intent**: Define an interface for creating families of related or dependent objects without specifying concrete classes.

- **Modern Idiom**: Combine with Spring's `FactoryBean<T>` or functional supplier registries:
```java
@Service
public class PaymentGatewayFactory {
    private final Map<PaymentType, PaymentGateway> gateways;

    // Spring injects all PaymentGateway beans mapped by their @Component name or enum
    public PaymentGatewayFactory(List<PaymentGateway> gatewayList) {
        this.gateways = gatewayList.stream()
            .collect(Collectors.toUnmodifiableMap(PaymentGateway::supportedType, Function.identity()));
    }

    public PaymentGateway getGateway(PaymentType type) {
        PaymentGateway gateway = gateways.get(type);
        if (gateway == null) {
            throw new IllegalArgumentException("Unsupported payment type: " + type);
        }
        return gateway;
    }
}
```

### 1.4 Singleton Pattern
**Intent**: Guarantee that a class has only one instance and provide a global point of access.

- **Best Practice**: **Do not hand-roll double-checked locking Singletons**. Let your Dependency Injection container (Spring `@Component` / `@Service`) manage the singleton lifecycle.
- **For standalone utilities without DI**: Use single-element `enum`:
```java
public enum SystemClock {
    INSTANCE;
    public Instant now() { return Instant.now(); }
}
```

---

## 2. Structural Patterns

### 2.1 Adapter Pattern
**Intent**: Convert the interface of an existing class into another interface expected by clients.

- **When to Use**: Integrating third-party SDKs, external APIs, or legacy databases into your clean architecture domain without polluting domain models.

```java
// Target Domain Interface
public interface SmsSender {
    void sendSms(String phoneNumber, String message);
}

// Adaptee: Third-party vendor SDK
public class TwilioApiSdk {
    public void dispatchMessage(TwilioRequest req) { /* vendor API */ }
}

// Adapter: Decouples our domain from vendor types
@Component
public class TwilioSmsAdapter implements SmsSender {
    private final TwilioApiSdk twilioClient;

    public TwilioSmsAdapter(TwilioApiSdk twilioClient) {
        this.twilioClient = twilioClient;
    }

    @Override
    public void sendSms(String phoneNumber, String message) {
        twilioClient.dispatchMessage(new TwilioRequest(phoneNumber, message));
    }
}
```

### 2.2 Decorator Pattern
**Intent**: Attach additional responsibilities to an object dynamically without modifying original class code.

- **When to Use**: Adding caching, metrics, logging, retry resilience, or authorization checks transparently.

```java
// Component Interface
public interface OrderRepository {
    Optional<Order> findById(UUID id);
}

// Concrete Component
@Repository
public class JpaOrderRepository implements OrderRepository { /* Database access */ }

// Decorator: Adds transparent caching layer
public class CachedOrderRepositoryDecorator implements OrderRepository {
    private final OrderRepository delegate;
    private final Cache<UUID, Order> cache;

    public CachedOrderRepositoryDecorator(OrderRepository delegate, Cache<UUID, Order> cache) {
        this.delegate = delegate;
        this.cache = cache;
    }

    @Override
    public Optional<Order> findById(UUID id) {
        Order cached = cache.getIfPresent(id);
        if (cached != null) return Optional.of(cached);

        Optional<Order> fresh = delegate.findById(id);
        fresh.ifPresent(o -> cache.put(id, o));
        return fresh;
    }
}
```

### 2.3 Facade Pattern
**Intent**: Provide a unified, high-level interface to a set of interfaces in a subsystem.

- **When to Use**: Simplifying complex orchestration (e.g., checkout involving inventory reservation, payment processing, tax calculation, email confirmation).

```java
@Service
public class CheckoutFacade {
    private final InventoryService inventoryService;
    private final PaymentService paymentService;
    private final NotificationService notificationService;

    public CheckoutFacade(InventoryService inventory, PaymentService payment, NotificationService notification) {
        this.inventoryService = inventory;
        this.paymentService = payment;
        this.notificationService = notification;
    }

    @Transactional
    public OrderReceipt checkout(Cart cart, PaymentDetails payment) {
        inventoryService.reserve(cart.items());
        var charge = paymentService.charge(cart.total(), payment);
        notificationService.sendReceipt(cart.user(), charge.receiptId());
        return new OrderReceipt(charge.id(), Instant.now());
    }
}
```

### 2.4 Proxy Pattern
**Intent**: Provide a surrogate or placeholder for another object to control access to it.

- **Modern Java & Spring Context**:
  - Spring uses **CGLIB proxies** (subclassing) and **JDK dynamic proxies** (`java.lang.reflect.Proxy`) to implement `@Transactional`, `@Cacheable`, `@Async`, and `@Retryable`.
  - **Self-Invocation Gotcha**: Calling a proxied method (`@Transactional`) from inside the same class bypasses the proxy; always call via injected bean reference or move to another service.

---

## 3. Behavioral Patterns

### 3.1 Strategy Pattern (Modern Functional Evolution)
**Intent**: Define a family of algorithms, encapsulate each one, and make them interchangeable at runtime.

- **Traditional Java**: Class per strategy implementing a shared interface.
- **Modern Java**: Use **first-class functions (`Function<T, R>`, `UnaryOperator<T>`)** or inject a strategy map in Spring.

```java
// Strategy interface
@FunctionalInterface
public interface DiscountStrategy {
    BigDecimal applyDiscount(BigDecimal subtotal);
}

// In-line functional strategies
public class DiscountStrategies {
    public static final DiscountStrategy NONE = subtotal -> subtotal;
    public static final DiscountStrategy VIP = subtotal -> subtotal.multiply(new BigDecimal("0.85"));
    public static final DiscountStrategy BLACK_FRIDAY = subtotal -> subtotal.multiply(new BigDecimal("0.70"));
}
```

### 3.2 Observer / Publish-Subscribe Pattern
**Intent**: Define a one-to-many dependency so when one object changes state, all dependents are notified automatically.

- **Modern Spring Idiom**: Use `ApplicationEventPublisher` and `@TransactionalEventListener`:

```java
// 1. Immutable Domain Event Record
public record OrderPlacedEvent(UUID orderId, BigDecimal amount, String customerEmail) {}

// 2. Publisher
@Service
public class OrderService {
    private final ApplicationEventPublisher eventPublisher;

    public OrderService(ApplicationEventPublisher publisher) { this.eventPublisher = publisher; }

    @Transactional
    public void placeOrder(Order order) {
        // Save order in DB
        eventPublisher.publishEvent(new OrderPlacedEvent(order.getId(), order.getTotal(), order.getEmail()));
    }
}

// 3. Listener (fires ONLY after the database transaction successfully commits)
@Component
public class NotificationEventListener {
    @Async
    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
    public void onOrderPlaced(OrderPlacedEvent event) {
        // Send email/push notification safely without risking rollback desync
    }
}
```

### 3.3 Visitor Pattern $\to$ Sealed Hierarchies & Record Patterns (Java 21+)
**Intent**: Represent an operation to be performed on elements of an object structure.

- **Classic Problem**: Visitor pattern requires immense ceremony (`accept(Visitor v)`, `visit(ConcreteElement e)`).
- **Modern Solution**: Use **`sealed interface` + Record Patterns + Pattern Matching Switch**. The compiler enforces exhaustive checking at compile time without double-dispatch ceremony:

```java
public sealed interface OrderCommand permits CreateOrder, CancelOrder, ShipOrder {}
public record CreateOrder(UUID orderId, BigDecimal amount) implements OrderCommand {}
public record CancelOrder(UUID orderId, String reason) implements OrderCommand {}
public record ShipOrder(UUID orderId, String trackingNumber) implements OrderCommand {}

public class OrderCommandHandler {
    public void handle(OrderCommand command) {
        // Compiler guarantees all branches are handled. No 'default' branch needed!
        switch (command) {
            case CreateOrder(var id, var amount) -> processCreate(id, amount);
            case CancelOrder(var id, var reason) -> processCancel(id, reason);
            case ShipOrder(var id, var tracking) -> processShip(id, tracking);
        }
    }
}
```

### 3.4 Template Method vs. Functional Composition
**Intent**: Define the skeleton of an algorithm in a base method, deferring some steps to subclasses.

- **Modern Best Practice**: Avoid deep abstract class hierarchies. Prefer **Functional Composition**: pass `Consumer<T>` or `Function<T, R>` hooks into a concrete class instead of subclassing.

```java
@Service
public class DataImporter {
    public <T> ImportSummary executeImport(Path file, Function<String, T> parser, Consumer<List<T>> batchWriter) {
        // 1. Common skeleton: open file, record metrics, start transaction
        long start = System.currentTimeMillis();
        List<T> buffer = new ArrayList<>(1000);

        try (var lines = Files.lines(file)) {
            lines.forEach(line -> {
                buffer.add(parser.apply(line));
                if (buffer.size() >= 1000) {
                    batchWriter.accept(buffer);
                    buffer.clear();
                }
            });
            if (!buffer.isEmpty()) batchWriter.accept(buffer);
        }

        return new ImportSummary(System.currentTimeMillis() - start);
    }
}
```

---

## 4. Enterprise Architecture Patterns

### 4.1 Repository & Unit of Work Pattern
- **Repository**: Encapsulates data access and provides an in-memory collection-like interface to the domain.
- **Unit of Work**: Maintains a list of business objects affected by a business transaction and coordinates writing out changes (implemented natively in Java by the JPA `EntityManager` and Spring's `@Transactional`).

### 4.2 Specification Pattern
Encapsulates query criteria into reusable, combinable business predicates (`Specification.where(active()).and(hasRole("ADMIN"))`) using Spring Data JPA Specifications.

### 4.3 Transactional Outbox Pattern
Guarantees **at-least-once message delivery** to message brokers (Kafka/RabbitMQ) when updating a database:
1. Write business entity changes and the outbound message event into the same database transaction.
2. A separate background poller (or Debezium CDC) reads outbox rows and publishes them to Kafka.
