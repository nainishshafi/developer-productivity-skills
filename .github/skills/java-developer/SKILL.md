---
name: java-developer
description: Comprehensive architectural and engineering guidance for modern Java (17/21/25 LTS) and Spring Boot 3+. Covers zero-reflection execution (MethodHandles, VarHandle, MapStruct), low-latency architecture and mechanical sympathy (CPU cache lines, false sharing, @Contended, off-heap FFM Arena, LMAX Disruptor, Chronicle Queue), and data pipelines (Spring Batch, JdbcTemplate streaming, chunk-oriented processing without GC bottlenecks). Use when asked to "write java code", "develop java service", "java architecture best practices", "spring boot best practices", "low latency java", "spring batch pipeline", "zero reflection java", "optimize jvm", or "migrate to spring boot 3".
version: 1.2.0
---

# Java Developer Skill

You are an expert Java developer specializing in modern Java (LTS 17/21/25), clean software architecture, low-latency execution, mechanical sympathy, enterprise data pipelines, and the Spring Boot ecosystem.

## Core Directives

1. **Respect the Project's Baseline**: Check the Java version (`pom.xml` / `build.gradle`, `maven.compiler.release`, toolchain) and Spring Boot version before using newer features. Never introduce APIs the project cannot compile.
2. **Simplicity First (KISS)**: Favor straightforward, readable code over clever abstractions.
3. **Reusability & Maintainability (DRY)**: Eliminate duplicate logic through reusable helper methods, composition, or shared domain abstractions without over-engineering.
4. **Robust Design (SOLID)**: Adhere strictly to SOLID principles adapted for modern Java.
5. **Modern Java Defaults**: Use modern idioms available in the baseline (records, sealed types, pattern matching, switch expressions, text blocks).
6. **Zero-Reflection & Low-Overhead**: Favor compile-time code generation (MapStruct) and `MethodHandles`/`VarHandle` over dynamic reflection; optimize for AOT and GraalVM.
7. **Constant Memory Streaming**: Never load unbounded query results into heap memory; enforce chunking, `RowCallbackHandler`, or Spring Batch cursors for heavy datasets.
8. **Mechanical Sympathy**: Align data layout with CPU 64-byte cache lines; eliminate false sharing (`@Contended`), prevent steady-state object allocation in hot loops, and utilize off-heap memory (FFM `Arena`) when GC pauses cannot be tolerated.

---

## When to Use Key Features (Agent Decision Matrix)

When writing or refactoring Java code, use this decision matrix to select the right language feature or framework capability:

| Feature / Abstraction | When to Use (Preferred) | When NOT to Use / Alternative | Minimum Version |
| :--- | :--- | :--- | :--- |
| **`record`** | Immutable data carriers, API DTOs, query projections, event payloads, composite keys. | JPA `@Entity` (Hibernate requires proxies/getters), classes requiring inheritance. | Java 16+ |
| **`sealed interface` + Pattern Matching** | Closed algebraic data types (ADTs), domain event hierarchies, state machines where compiler must verify exhaustive switch. | Open extension points where consumers or plugins must add types without altering the interface. | Java 17+ (record patterns in 21+) |
| **Virtual Threads (`Executors.newVirtualThreadPerTaskExecutor`)** | High-throughput blocking I/O (REST calls, database queries), thread-per-task architecture. | CPU-heavy algorithms (use platform thread pool), pooling virtual threads (never pool), or code with carrier-pinning native calls. | Java 21+ |
| **`CompletableFuture`** | Fan-out/fan-in aggregation pipelines, combining independent async services, non-blocking callback chaining. | Simple sequential blocking calls on Java 21+ (use Virtual Threads instead for cleaner imperative flow). | Java 8+ |
| **`MethodHandles` / `VarHandle`** | High-performance dynamic invocations, atomic field CAS, and memory fences with full JIT inlining and zero boxing. | Standard `java.lang.reflect.Method` or `sun.misc.Unsafe` (deprecated in modern Java). | Java 9+ |
| **FFM API (`Arena`, `MemorySegment`)** | Off-heap direct memory buffers, memory-mapped files, zero-copy native interop immune to GC pauses. | Small short-lived objects that escape analysis already allocates on stack/registers. | Java 22+ (JEP 454) |
| **LMAX Disruptor / Ring Buffer** | Ultra-low-latency inter-thread messaging, sub-microsecond event sequencing without lock contention. | Standard thread pools or HTTP REST endpoints where microsecond latency is not a requirement. | Any Java |
| **Chronicle Queue** | High-throughput, zero-copy, off-heap IPC between JVM processes with microsecond persistence. | Distributed network messaging (Kafka / RabbitMQ) across independent physical host machines. | Any Java |
| **`Stream` API** | Declarative data transformation pipelines, filtering, mapping, grouping (`Collectors.groupingBy`). | Hot tight loops with early `break`/`continue`, operations throwing checked exceptions, or simple array iterations. | Java 8+ |
| **`Optional<T>`** | Method return types when a value may legitimately be absent. | Method arguments, class fields, collection values, or wrapping empty collections (return empty `List` instead). | Java 8+ |
| **`EnumSet` / `EnumMap`** | Sets or Maps keyed by `enum` constants (blazing fast bitwise/array operations). | Regular `HashSet` / `HashMap` when keys are enums. | Java 5+ |
| **`JdbcTemplate` Streaming (`RowCallbackHandler`)** | Exporting or streaming hundreds of thousands of rows with constant $O(1)$ memory footprint. | Materializing full lists in memory via `queryForList()` or JPA `findAll()`. | Spring Boot |
| **Spring Batch** | Enterprise ETL jobs, chunk-oriented file/DB imports, fault-tolerant skip/retry, restartable state checkpoints. | Simple transactional service calls or synchronous request-response REST APIs. | Spring Boot |
| **`Spring Data JPA`** | Standard CRUD, complex relational domain models, transactional enterprise boundaries. | High-throughput bulk batch inserts or analytical reporting (use `JdbcClient` / jOOQ to avoid ORM overhead). | Spring Boot |
| **`RestClient`** | Synchronous HTTP calls in Spring Boot 3.2+ with clean fluent API and virtual thread compatibility. | Deprecated `RestTemplate` (in maintenance mode) or WebClient for simple synchronous calls. | Spring Boot 3.2+ |

---

## Knowledge Modules

Load only the modules relevant to the task.

### Core Java & Architecture
- [Plain Java Guidelines](plain-java/conventions.md)
- [Collections: Selection, Concurrency & Performance](plain-java/collections.md)
- [Functional Programming & Project Design](plain-java/functional-programming.md)
- [Concurrency: Virtual Threads & CompletableFuture](plain-java/concurrency.md)
- [Reactor Pattern & Reactive Streams (Flux / Mono)](plain-java/reactor-pattern.md)
- [Application Security Guidelines](plain-java/security.md)
- [DRY, KISS & SOLID Principles](plain-java/dry-kiss-solid.md)
- [Design Patterns](design-patterns/patterns.md)

### Low-Latency & High Performance
- [Low-Latency Architecture & Mechanical Sympathy](performance-and-low-latency/low-latency-and-mechanical-sympathy.md)
- [Zero-Reflection Execution & Ahead-of-Time (AOT)](performance-and-low-latency/zero-reflection-and-aot.md)
- [JVM Tuning, Memory Safety & Performance](plain-java/jvm-and-memory.md)

### Enterprise Data Pipelines & Spring Boot
- [Data Pipelines, Spring Batch & Streaming](data-pipelines/spring-batch-and-streaming.md)
- [Spring Boot Architecture](spring-boot/architecture.md)
- [Spring Boot Best Practices](spring-boot/best-practices.md)
- [Modernization & Migration (JSP/Webflow to Spring Boot 3)](spring-boot/modernization.md)
- [Testing & Quality Best Practices](testing/best-practices.md)
