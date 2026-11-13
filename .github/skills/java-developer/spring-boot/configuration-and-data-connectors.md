# Modular Configuration & Data Connectors in Spring Boot 3+

Externalized configuration is one of the primary mechanisms for keeping Spring Boot services modular. When implemented with **feature-scoped `@ConfigurationProperties` records** and dedicated **connector `@Configuration` classes**, each module owns its own typed settings contract and swaps implementations or environments without touching business logic.

---

## 1. How `@ConfigurationProperties` Makes Code Modular

Scattered `@Value("${...}")` fields couple business services to global property key strings, break silently on typos until runtime, and force unit tests to spin up Spring or use reflection.

By contrast, `@ConfigurationProperties` enforces **feature-level encapsulation**:

| Modularity Benefit | How It Works |
| :--- | :--- |
| **Feature-Scoped Contracts** | Each module defines its own `record` (e.g., `ReportingDbProperties` in `reporting/`, `PaymentConnectorProperties` in `payment/`), avoiding a single monolithic `AppConfig` God class. |
| **Fail-Fast Validation** | Pairing `@ConfigurationProperties` with `@Validated` and Jakarta Bean Validation (`@NotBlank`, `@Positive`, `@NotNull`) rejects missing or malformed config at startup rather than mid-request. |
| **Environment Independence** | Modules depend only on their typed Java `record`, decoupled from whether values come from `application.yml`, Kubernetes ConfigMaps, env vars, or test properties. |
| **Context-Free Unit Testing** | Because a properties `record` is a plain immutable Java object, tests pass `new PaymentConnectorProperties(...)` directly without `@SpringBootTest`. |
| **Conditional Module Activation** | `@ConditionalOnProperty` lets configuration enable, disable, or swap connector beans cleanly without `if/else` flags inside `@Service` classes. |

### Anti-Pattern vs. Modular Pattern

```java
// ❌ Anti-pattern: scattered @Value strings inside business logic
@Service
public class InvoiceExportService {
    @Value("${app.reporting.url}")
    private String url;

    @Value("${app.reporting.timeout-ms:3000}")
    private int timeoutMs;
}
```

```java
// ✅ Modular: feature-owned, validated, immutable record
@Validated
@ConfigurationProperties(prefix = "app.reporting")
public record ReportingProperties(
    @NotBlank String url,
    @DefaultValue("3000ms") @DurationMin(millis = 100) Duration timeout,
    @DefaultValue("true") boolean enabled
) {}
```

Enable discovery once on your main application class (or per-config with `@EnableConfigurationProperties`):

```java
@SpringBootApplication
@ConfigurationPropertiesScan
public class Application {
    public static void main(String[] args) {
        SpringApplication.run(Application.class, args);
    }
}
```

---

## 2. Implementing a Modular Database Data Connector (Multi-DataSource)

When a service connects to a secondary analytical or legacy database alongside its primary store, isolate the secondary connector in its own package (`reporting/config/`) so primary JPA repositories and transactions remain unaffected.

### Step 1: Externalized Config (`application.yml`)

```yaml
# Primary store (auto-configured by Spring Boot)
spring:
  datasource:
    url: jdbc:postgresql://localhost:5432/orders_db
    username: ${ORDERS_DB_USER}
    password: ${ORDERS_DB_PASS}
    hikari:
      maximum-pool-size: 20
      connection-timeout: 3000

# Secondary modular data connector
app:
  datasource:
    reporting:
      jdbc-url: jdbc:postgresql://analytics-ro:5432/reporting_db
      username: ${REPORTING_DB_USER}
      password: ${REPORTING_DB_PASS}
      maximum-pool-size: 10
      connection-timeout: 5000
      leak-detection-threshold: 10000
```

### Step 2: Typed Connector Properties (`record`)

```java
package com.example.app.reporting.config;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.context.properties.bind.DefaultValue;
import org.springframework.validation.annotation.Validated;

@Validated
@ConfigurationProperties(prefix = "app.datasource.reporting")
public record ReportingDataSourceProperties(
    @NotBlank String jdbcUrl,
    @NotBlank String username,
    @NotBlank String password,
    @DefaultValue("10") @Min(1) @Max(100) int maximumPoolSize,
    @DefaultValue("5000") @Min(500) long connectionTimeout,
    @DefaultValue("10000") long leakDetectionThreshold
) {}
```

### Step 3: Isolated Connector Configuration (`@Configuration`)

> [!IMPORTANT]
> As soon as you declare a custom `DataSource` `@Bean`, Spring Boot backs off its auto-configured primary `DataSource` unless you explicitly mark your primary store `@Primary` (or configure both explicitly).

```java
package com.example.app.reporting.config;

import com.zaxxer.hikari.HikariConfig;
import com.zaxxer.hikari.HikariDataSource;
import javax.sql.DataSource;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.transaction.PlatformTransactionManager;

@Configuration(proxyBeanMethods = false)
public class ReportingDataSourceConfig {

    @Bean(name = "reportingDataSource")
    public DataSource reportingDataSource(ReportingDataSourceProperties props) {
        HikariConfig config = new HikariConfig();
        config.setPoolName("reporting-hikari-pool");
        config.setJdbcUrl(props.jdbcUrl());
        config.setUsername(props.username());
        config.setPassword(props.password());
        config.setMaximumPoolSize(props.maximumPoolSize());
        config.setConnectionTimeout(props.connectionTimeout());
        config.setLeakDetectionThreshold(props.leakDetectionThreshold());
        config.setReadOnly(true);
        return new HikariDataSource(config);
    }

    @Bean(name = "reportingJdbcClient")
    public JdbcClient reportingJdbcClient(
            @Qualifier("reportingDataSource") DataSource dataSource) {
        return JdbcClient.create(dataSource);
    }

    @Bean(name = "reportingTransactionManager")
    public PlatformTransactionManager reportingTransactionManager(
            @Qualifier("reportingDataSource") DataSource dataSource) {
        return new DataSourceTransactionManager(dataSource);
    }
}
```

### Step 4: Why `@Qualifier("reportingJdbcClient")` Is Needed (and Where to Isolate It)

Spring resolves constructor dependencies **by type** first. Because this application has **two `DataSource` beans** and **two `JdbcClient` beans** (one for the primary `orders` DB and one for `reporting`), asking for `JdbcClient` alone throws `NoUniqueBeanDefinitionException`.

- Mark the default `DataSource` / `JdbcClient` with `@Primary` so normal code injects it without qualifiers.
- Use `@Qualifier("reportingJdbcClient")` **only at the boundary** (`ReportingQueryRepository`), so upstream `@Service` classes simply inject `ReportingQueryRepository` by its unique Java type without knowing any bean-name strings.

```java
package com.example.app.reporting;

import java.util.List;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
public class ReportingQueryRepository {

    private final JdbcClient jdbc;

    // @Qualifier selects the reporting JdbcClient bean instead of the @Primary orders JdbcClient
    public ReportingQueryRepository(@Qualifier("reportingJdbcClient") JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    public List<DailyTotal> fetchDailyTotals() {
        return jdbc.sql("""
                SELECT report_date, total_amount
                FROM daily_revenue_summary
                ORDER BY report_date DESC
                LIMIT 30
                """)
            .query(DailyTotal.class)
            .list();
    }
}
```

---

## 3. Implementing a Modular External API Connector (`RestClient` + `@HttpExchange`)

For external REST/JSON data providers, encapsulate base URLs, timeouts, and auth headers in `config/` and expose a declarative `@HttpExchange` interface to the service layer.

### Step 1: Connector Properties & YAML

```yaml
app:
  connectors:
    payment:
      base-url: https://api.payments.example.com
      api-key: ${PAYMENT_API_KEY}
      connect-timeout: 2s
      read-timeout: 5s
```

```java
@Validated
@ConfigurationProperties(prefix = "app.connectors.payment")
public record PaymentConnectorProperties(
    @NotBlank String baseUrl,
    @NotBlank String apiKey,
    @DefaultValue("2s") Duration connectTimeout,
    @DefaultValue("5s") Duration readTimeout
) {}
```

### Step 2: Declarative Client Interface & Wiring

```java
public interface PaymentGatewayClient {
    @GetExchange("/v1/payments/{id}")
    PaymentStatus getPayment(@PathVariable String id);
}
```

```java
@Configuration(proxyBeanMethods = false)
public class PaymentConnectorConfig {

    @Bean
    public PaymentGatewayClient paymentGatewayClient(
            RestClient.Builder builder,
            PaymentConnectorProperties props) {

        var requestFactory = new JdkClientHttpRequestFactory(
            HttpClient.newBuilder()
                .connectTimeout(props.connectTimeout())
                .build()
        );
        requestFactory.setReadTimeout(props.readTimeout());

        RestClient restClient = builder
            .baseUrl(props.baseUrl())
            .requestFactory(requestFactory)
            .defaultHeader("Authorization", "Bearer " + props.apiKey())
            .build();

        return HttpServiceProxyFactory
            .builderFor(RestClientAdapter.create(restClient))
            .build()
            .createClient(PaymentGatewayClient.class);
    }
}
```

---

## 4. Injecting Different Data Connectors into a `@Service`

Depending on whether a service combines multiple sources, swaps one provider per environment, or routes dynamically at runtime, use one of these three injection patterns:

### Pattern A: Multiple Distinct Connectors in One Service (Constructor Injection by Type)

When a service orchestrates across different data stores (e.g., primary DB + reporting DB + external REST API), wrap each secondary source in its own typed bean (`ReportingQueryRepository`, `PaymentGatewayClient`) and inject them cleanly by type — **no `@Qualifier` clutter in the service**:

```java
package com.example.app.reporting;

import com.example.app.order.OrderRepository;
import com.example.app.payment.PaymentGatewayClient;
import org.springframework.stereotype.Service;

@Service
public class ReconciliationService {

    private final OrderRepository orderRepo;               // Primary DB (JPA)
    private final ReportingQueryRepository reportingRepo;  // Secondary DB (reportingJdbcClient)
    private final PaymentGatewayClient paymentClient;      // External HTTP API (RestClient)

    public ReconciliationService(
            OrderRepository orderRepo,
            ReportingQueryRepository reportingRepo,
            PaymentGatewayClient paymentClient) {
        this.orderRepo = orderRepo;
        this.reportingRepo = reportingRepo;
        this.paymentClient = paymentClient;
    }

    public ReconciliationReport reconcile(String paymentId) {
        var totals = reportingRepo.fetchDailyTotals();
        var payment = paymentClient.getPayment(paymentId);
        var orderCount = orderRepo.count();
        return new ReconciliationReport(orderCount, totals, payment);
    }
}
```

### Pattern B: Swapping One Connector per Environment (`@ConditionalOnProperty`)

Keep an interface **only** when you genuinely have multiple runtime implementations (e.g., local filesystem in dev vs. S3 in production). Use `@ConditionalOnProperty` so configuration selects the active bean and the `@Service` injects `BlobStorageConnector` without knowing which implementation is active:

```java
public interface BlobStorageConnector {
    void upload(String key, byte[] content);
}

@Component
@ConditionalOnProperty(name = "app.storage.provider", havingValue = "local", matchIfMissing = true)
public class LocalBlobStorageConnector implements BlobStorageConnector { ... }

@Component
@ConditionalOnProperty(name = "app.storage.provider", havingValue = "s3")
public class S3BlobStorageConnector implements BlobStorageConnector { ... }

@Service
public class DocumentArchiveService {
    private final BlobStorageConnector storage; // Receives Local or S3 based on config

    public DocumentArchiveService(BlobStorageConnector storage) {
        this.storage = storage;
    }
}
```

### Pattern C: Dynamic Runtime Selection (`Map<String, Connector>` Injection)

When a single service must route to different data connectors at runtime (e.g., per tenant, region, or data source type), Spring automatically populates a `Map<String, DataSourceConnector>` keyed by bean name:

```java
public interface DataSourceConnector {
    String fetchPayload(String query);
}

@Component("postgres")
public class PostgresDataConnector implements DataSourceConnector { ... }

@Component("snowflake")
public class SnowflakeDataConnector implements DataSourceConnector { ... }

@Service
public class DataPipelineService {

    private final Map<String, DataSourceConnector> connectors;

    public DataPipelineService(Map<String, DataSourceConnector> connectors) {
        this.connectors = connectors;
    }

    public String extract(String sourceType, String query) {
        DataSourceConnector connector = connectors.get(sourceType);
        if (connector == null) {
            throw new IllegalArgumentException("Unsupported connector: " + sourceType);
        }
        return connector.fetchPayload(query);
    }
}
```

---

## 5. Fast Testing Without `@SpringBootTest`

Use Spring Boot's lightweight `ApplicationContextRunner` to verify `@ConfigurationProperties` binding, validation failures, and conditional bean wiring in milliseconds:

```java
class ReportingConfigTest {

    private final ApplicationContextRunner contextRunner = new ApplicationContextRunner()
        .withUserConfiguration(TestConfig.class);

    @EnableConfigurationProperties(ReportingDataSourceProperties.class)
    static class TestConfig {}

    @Test
    void bindsAndValidatesProperties() {
        contextRunner
            .withPropertyValues(
                "app.datasource.reporting.jdbc-url=jdbc:h2:mem:test",
                "app.datasource.reporting.username=sa",
                "app.datasource.reporting.password=secret"
            )
            .run(ctx -> {
                assertThat(ctx).hasSingleBean(ReportingDataSourceProperties.class);
                var props = ctx.getBean(ReportingDataSourceProperties.class);
                assertThat(props.maximumPoolSize()).isEqualTo(10);
            });
    }
}
```

