# Data Pipelines, Spring Batch & Memory-Efficient Streaming

Architectural guidance for processing massive enterprise datasets, building resilient Spring Batch pipelines, and streaming via `JdbcTemplate` without triggering Garbage Collection pause storms or `OutOfMemoryError`.

---

## 1. The Heavy Dataset OOM Trap

When processing millions of records, standard database queries fail with `java.lang.OutOfMemoryError: Java heap space`:

```text
❌ ANTI-PATTERN: Loading unbounded rows into JVM Heap
Database (10,000,000 rows) ──> SELECT * ──> List<Order> (10M Java objects = 4GB Heap) ──> OOM / GC Pause Storm
```

### The Streaming Invariant: Constant $O(1)$ Memory Footprint
A well-architected data pipeline processes an infinite stream of records using a constant, bounded memory footprint ($O(1)$ memory):
```text
✔ STREAMING PATTERN: Bounded Cursor Streaming
Database ──[ Fetch 1,000 rows ]──> JVM Buffer (1,000 objects = 2MB Heap) ──> Process & Write ──> Discard & Reuse
```

---

## 2. Memory-Efficient Streaming with `JdbcTemplate` & `JdbcClient`

Standard JDBC drivers (PostgreSQL, MySQL, Oracle) default to **fetching the entire query result into client RAM** before returning from `.executeQuery()`.

### Driver Buffer Traps & Fixes

| Database Engine | Default Driver Behavior | Required Driver Setting for True Streaming |
| :--- | :--- | :--- |
| **PostgreSQL** | Buffers all rows in client memory | Set `fetchSize > 0` **AND** set `connection.setAutoCommit(false)`. If autocommit is enabled, PostgreSQL ignores fetchSize and buffers the whole table! |
| **MySQL (Connector/J)** | Buffers all rows in client memory | Set `statement.setFetchSize(Integer.MIN_VALUE)` for row-by-row streaming, or configure `useCursorFetch=true` in connection URL. |
| **Oracle** | Default fetch size is 10 rows | Set `statement.setFetchSize(1000)` to balance round-trips and memory. |

### Streaming Rows with `RowCallbackHandler`
`RowCallbackHandler` processes rows one at a time as they arrive over the wire, never materializing a full list in memory:

```java
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

@Service
public class OrderExportService {
    private final JdbcTemplate jdbcTemplate;

    public OrderExportService(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    public void streamOrdersToCsv(OutputStream out) {
        // 1. Configure fetch size on the statement
        jdbcTemplate.setFetchSize(1000);

        String sql = "SELECT id, customer_id, total_amount, created_at FROM orders WHERE status = 'COMPLETED'";

        // 2. Stream directly to writer without accumulating in Java heap
        try (var writer = new BufferedWriter(new OutputStreamWriter(out))) {
            jdbcTemplate.query(sql, rs -> {
                // Invoked once per row
                long orderId = rs.getLong("id");
                String customerId = rs.getString("customer_id");
                double amount = rs.getDouble("total_amount");
                
                writer.write(orderId + "," + customerId + "," + amount + "\n");
            });
            writer.flush();
        } catch (Exception e) {
            throw new RuntimeException("Stream export failed", e);
        }
    }
}
```

### Streaming with `JdbcClient` (Spring 6 / Boot 3+) & Java 8 `Stream`
When using `JdbcClient.query().stream()`, always wrap the stream in a `try-with-resources` block to ensure the underlying database connection and cursor close cleanly:
```java
import org.springframework.jdbc.core.simple.JdbcClient;
import java.util.stream.Stream;

public void processStream(JdbcClient jdbcClient) {
    String sql = "SELECT id, sku, price FROM products";

    // MUST use try-with-resources to close connection stream
    try (Stream<ProductDto> stream = jdbcClient.sql(sql)
            .query((rs, rowNum) -> new ProductDto(rs.getLong("id"), rs.getString("sku"), rs.getBigDecimal("price")))
            .stream()) {
        
        stream.filter(p -> p.price().doubleValue() > 100.0)
              .forEach(this::processSingleItem);
    }
}
```

### High-Throughput Batch Inserts
Never execute individual `INSERT` statements inside a loop. Use `JdbcTemplate.batchUpdate()` with chunked parameter batches:
```java
public void bulkInsertOrders(List<OrderDto> orders) {
    String sql = "INSERT INTO orders (id, customer_id, amount) VALUES (?, ?, ?)";
    int batchSize = 1000;

    jdbcTemplate.batchUpdate(sql, orders, batchSize, (ps, order) -> {
        ps.setLong(1, order.id());
        ps.setString(2, order.customerId());
        ps.setBigDecimal(3, order.amount());
    });
}
```

---

## 3. Spring Batch: Enterprise Pipeline Architecture

Spring Batch provides chunk-oriented, transactional processing designed for high-volume ETL workloads with built-in checkpointing and fault tolerance.

```text
[ JobRepository ] ── Metadata & Checkpointing
       │
    [ Job ]
       │
   [ Step ] ── Chunk-Oriented Processing (e.g. Commit Interval = 1,000)
       ├── ItemReader    ──> Reads 1 item at a time until chunk is full (1,000 items)
       ├── ItemProcessor ──> Transforms/validates items
       └── ItemWriter    ──> Writes entire chunk (1,000 items) in a single DB transaction
```

### Complete Chunk-Oriented Step Configuration (Spring Batch 5 / Boot 3)
```java
import org.springframework.batch.core.Job;
import org.springframework.batch.core.Step;
import org.springframework.batch.core.job.builder.JobBuilder;
import org.springframework.batch.core.repository.JobRepository;
import org.springframework.batch.core.step.builder.StepBuilder;
import org.springframework.batch.item.ItemProcessor;
import org.springframework.batch.item.database.JdbcCursorItemReader;
import org.springframework.batch.item.database.builder.JdbcCursorItemReaderBuilder;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.transaction.PlatformTransactionManager;

import javax.sql.DataSource;

@Configuration
public class OrderBatchJobConfig {

    @Bean
    public Job orderProcessingJob(JobRepository jobRepository, Step orderStep) {
        return new JobBuilder("orderProcessingJob", jobRepository)
            .start(orderStep)
            .build();
    }

    @Bean
    public Step orderStep(JobRepository jobRepository,
                         PlatformTransactionManager transactionManager,
                         DataSource dataSource) {
        return new StepBuilder("orderStep", jobRepository)
            .<RawOrder, CleanOrder>chunk(1000, transactionManager) // Chunk size: 1,000 items per commit
            .reader(orderCursorReader(dataSource))
            .processor(orderProcessor())
            .writer(orderItemWriter(dataSource))
            .faultTolerant()
            .skip(InvalidOrderException.class)
            .skipLimit(50) // Skip up to 50 bad records without failing job
            .retry(TransientNetworkException.class)
            .retryLimit(3)
            .build();
    }

    @Bean
    public JdbcCursorItemReader<RawOrder> orderCursorReader(DataSource dataSource) {
        return new JdbcCursorItemReaderBuilder<RawOrder>()
            .name("orderCursorReader")
            .dataSource(dataSource)
            .sql("SELECT id, raw_payload FROM inbound_orders WHERE processed = false")
            .fetchSize(1000)
            .rowMapper((rs, rowNum) -> new RawOrder(rs.getLong("id"), rs.getString("raw_payload")))
            .verifyCursorPosition(false)
            .build();
    }

    @Bean
    public ItemProcessor<RawOrder, CleanOrder> orderProcessor() {
        return raw -> {
            if (raw.payload() == null || raw.payload().isBlank()) {
                throw new InvalidOrderException("Empty payload for order: " + raw.id());
            }
            return new CleanOrder(raw.id(), raw.payload().trim().toUpperCase());
        };
    }
}
```

---

## 4. Cursor vs. Paging Readers: Decision Matrix

Selecting the wrong reader causes transaction timeouts or duplicate processing.

| Reader Type | Implementation | Pros | Cons / Watchouts |
| :--- | :--- | :--- | :--- |
| **Cursor Reader** | `JdbcCursorItemReader` | **Fastest execution**: Streams over a single open database cursor with constant memory. | Holds a database connection open for the duration of the entire step. Incompatible with multi-threaded steps. |
| **Paging Reader** | `JdbcPagingItemReader` | **Safe for long jobs**: Queries data in discrete pages (`OFFSET` / Keyset). Releases DB connection between pages. Thread-safe for multi-threaded steps. | **MANDATORY**: Requires a strict, deterministic `ORDER BY` clause. Without stable ordering, updates can shift rows across pages, skipping records or processing them twice! |

---

## 5. Eliminating GC Bottlenecks in Batch Pipelines

1. **Bypass Hibernate / JPA for Heavy ETL**:
   - JPA entity managers track every loaded entity in the first-level cache (`PersistenceContext`).
   - Loading 500,000 entities via JPA causes Hibernate to store 500,000 snapshots for dirty-checking, quickly consuming gigabytes of heap.
   - *Fix*: Use `JdbcCursorItemReader` and `JdbcBatchItemWriter` for batch jobs. If JPA is strictly required, inject `EntityManager` and call `entityManager.clear()` after each chunk.
2. **Object Reuse / Flyweight Pattern**:
   - In `ItemProcessor`, avoid instantiating heavy temporary objects (date formatters, JSON parsers, regex `Pattern`).
   - Pre-compile `Pattern` instances into `static final` constants.
3. **Partitioning for Horizontal Scaling**:
   - Split a monolithic step into $N$ parallel steps using Spring Batch `PartitionHandler`:
   - Example: Partition by range (`WHERE id BETWEEN 1 AND 1000000`, `WHERE id BETWEEN 1000001 AND 2000000`) across separate worker threads or remote worker nodes.

