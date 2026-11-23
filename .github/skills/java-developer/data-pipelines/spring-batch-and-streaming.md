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
// Excerpt: routine imports omitted.
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
// Excerpt: routine imports omitted.
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

Choose the processing model for each step, not for the entire job:

- **Chunk-oriented (chunk-based):** Use for a stream of records. An `ItemReader` reads one item at a time, an optional `ItemProcessor` transforms or filters items, and an `ItemWriter` receives the resulting group before the transaction commits. A failed chunk can roll back without undoing earlier committed chunks. Use restartable readers and writers when the job needs to resume from its last checkpoint.
- **Tasklet-based:** Use for a custom operation that does not need an item pipeline, such as checking an input file, calling a stored procedure, or archiving a file. `Tasklet.execute()` returns `RepeatStatus.FINISHED` when done or `RepeatStatus.CONTINUABLE` to run again. Each invocation is wrapped in a transaction, but that transaction cannot undo a filesystem move; make such operations safe to repeat on restart.

### Example: Check a CSV, then import orders (Spring Batch 5 / Boot 3)

This configuration assumes Boot provides a JDBC `JobRepository` and a transaction manager for the same PostgreSQL data source used by the writer. Create the Spring Batch metadata tables and an `orders` table with `id BIGINT PRIMARY KEY` and `payload TEXT NOT NULL`. Launch with an identifying `input` job parameter containing a trusted local file path. The UTF-8 CSV starts with an `id,payload` header followed by rows such as `42,ready`.

```java
// Excerpt: routine imports omitted.
@Configuration(proxyBeanMethods = false)
public class OrderBatchJobConfig {
    record Order(long id, String payload) {}
    static class InvalidOrderException extends RuntimeException {
        InvalidOrderException(long id) {
            super("Blank payload for order " + id);
        }
    }

    @Bean
    Job orderImport(JobRepository repository, @Qualifier("checkInput") Step checkInput,
                    @Qualifier("importOrders") Step importOrders) {
        return new JobBuilder("orderImport", repository).start(checkInput).next(importOrders).build();
    }

    @Bean
    Step checkInput(JobRepository repository, PlatformTransactionManager transactions) {
        return new StepBuilder("checkInput", repository)
            .tasklet((contribution, context) -> {
                Object input = context.getStepContext().getJobParameters().get("input");
                if (!(input instanceof String file) || file.isBlank()) {
                    throw new IllegalArgumentException("The input job parameter is required");
                }
                Path path = Path.of(file);
                if (!Files.isRegularFile(path) || !Files.isReadable(path)) {
                    throw new IllegalArgumentException("Input must be a readable file: " + path);
                }
                return RepeatStatus.FINISHED;
            }, transactions)
            .build();
    }

    @Bean
    Step importOrders(JobRepository repository, PlatformTransactionManager transactions,
                      FlatFileItemReader<Order> orderReader, JdbcBatchItemWriter<Order> orderWriter) {
        return new StepBuilder("importOrders", repository)
            .<Order, Order>chunk(500, transactions)
            .reader(orderReader)
            .processor(order -> {
                if (order.payload().isBlank()) {
                    throw new InvalidOrderException(order.id());
                }
                return new Order(order.id(), order.payload().strip());
            })
            .writer(orderWriter)
            .faultTolerant()
            .skip(InvalidOrderException.class)
            .skipLimit(10)
            .retry(CannotAcquireLockException.class)
            .retryLimit(3) // Up to three attempts for this failure, including the initial attempt.
            .build();
    }

    @Bean
    @StepScope
    FlatFileItemReader<Order> orderReader(@Value("#{jobParameters['input']}") String input) {
        return new FlatFileItemReaderBuilder<Order>()
            .name("orderCsvReader")
            .resource(new FileSystemResource(input))
            .encoding("UTF-8")
            .linesToSkip(1)
            .delimited().names("id", "payload")
            .fieldSetMapper(fields -> new Order(fields.readLong("id"), fields.readString("payload")))
            .build();
    }

    @Bean
    JdbcBatchItemWriter<Order> orderWriter(DataSource dataSource) {
        return new JdbcBatchItemWriterBuilder<Order>()
            .dataSource(dataSource)
            .sql("""
                INSERT INTO orders (id, payload) VALUES (?, ?)
                ON CONFLICT (id) DO UPDATE SET payload = EXCLUDED.payload
                """)
            .itemPreparedStatementSetter((order, statement) -> {
                statement.setLong(1, order.id());
                statement.setString(2, order.payload());
            })
            .build();
    }
}
```

### Chunk step best practices

- **Tune the commit interval by measurement.** With 1,201 valid rows and no failures, the writer gets batches of 500, 500, and 201. Filtering or skipping can make a write smaller. Smaller chunks reduce lock duration and rollback work; larger chunks amortize commit overhead but buffer more items. JDBC fetch size is a separate driver setting. Compare throughput, heap use, and transaction duration before tuning either.
- **Keep processors repeatable and batch writes.** A retry or rollback can run processing again. Avoid remote calls, file moves, or notifications inside the processor. Return `null` to intentionally filter an item; throw a specific exception only for a failure. Let the step manage the transaction rather than committing inside the writer.
- **Retry transient failures and skip only known bad data.** The example retries lock acquisition failures and skips up to 10 orders with blank payloads. Malformed CSV and unrelated errors fail the step. When skipping is allowed, surface the skip count and record enough information to trace rejected rows without logging sensitive payloads.
- **Design for restart, not just retry.** Restart a failed execution with the same identifying job parameters and unchanged input. The `JobRepository` and the step-scoped reader's saved position let the step resume from the last committed chunk. A position-based checkpoint is unsafe if records move: keep files immutable and give database readers a stable input set and deterministic ordering. The example's upsert is appropriate only if the incoming payload should replace the current one; it does not make triggers or external effects exactly-once.

### Tasklet step best practices

- **Keep `execute()` focused on one operation.** Return `FINISHED` for a one-shot check or stored procedure. Use `CONTINUABLE` only when each invocation completes one bounded unit of work and moves closer to completion. For a record import, prefer a chunk step to a manual loop.
- **Persist progress explicitly for repeating tasklets.** Store a resume key in the step `ExecutionContext` when an invocation completes its unit of work. Each invocation has its own transaction; a later rollback does not undo prior committed invocations. Don't rely on instance fields to carry state across restarts.
- **Plan for external effects and completed steps.** An archive step can move a file successfully and then fail before Spring Batch records completion. Use a deterministic destination and verify that an existing archive matches the intended input before treating replay as complete. Completed steps are normally skipped on restart; set `allowStartIfComplete(true)` only when a step must run again, such as when repeating an input check is required.

### Verify failure and restart behavior

Use a real test database with persisted batch metadata. Import enough rows to reach a second chunk, force a non-retryable failure on its write, and verify that only the first chunk persisted. Remove the fault, restart with the same identifying parameters, and verify the final row count and absence of duplicates. Also test that a missing file fails `checkInput` without starting `importOrders`, and that known invalid data is skipped while an unexpected exception fails the step.

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
