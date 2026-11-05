# Reactor Patterns & Reactive Streams (Flux / Mono)

This section covers both the **Architectural Reactor Pattern** (underlying Netty / Java NIO) and **Project Reactor (Flux & Mono)** used in Spring WebFlux.

---

## 1. The Classic Reactor Architectural Pattern

The Reactor pattern is an event-handling architecture for dispatching service requests delivered concurrently to a service handler by one or more inputs.

### Core Components
- **Demultiplexer (Event Loop)**: Uses OS-level polling (`select`/`epoll` via Java NIO `Selector`) to wait for events on channels without blocking threads.
- **Dispatcher**: Central loop that routes events (Accept, Read, Write) to registered handlers.
- **Event Handlers**: Non-blocking callbacks that execute the request processing logic.

### Used By
- **Netty** (EventLoopGroup), Java NIO (`Selector`), and underneath Spring WebFlux / Node.js.

---

## 2. Project Reactor & Reactive Streams (`Flux` / `Mono`)

Project Reactor is the reactive library powering **Spring WebFlux**, built on the Reactive Streams standard.

### Core Primitives
- **`Mono<T>`**: Emits 0 or 1 item (asynchronous single value, e.g., finding a user by ID).
- **`Flux<T>`**: Emits 0 to N items (asynchronous stream of data, e.g., real-time events, SSE).

```java
// Non-blocking pipeline with backpressure
Flux<OrderDto> activeOrders = orderRepository.findByStatus(Status.ACTIVE)
    .filter(order -> order.amount().compareTo(BigDecimal.ZERO) > 0)
    .map(this::enrichOrder);
```

---

## 3. When to Use vs. What to Avoid

### When to Use
- **Real-time streaming**: Server-Sent Events (SSE), WebSockets, or live telemetry streams.
- **Gateway / Proxy layers**: Edge proxies (like Spring Cloud Gateway) routing millions of lightweight requests with minimal memory footprint.
- **High concurrency with full non-blocking stack**: When every layer (database drivers via R2DBC, HTTP clients via WebClient) is 100% non-blocking.

### What to Avoid
- **Never block inside a Reactive pipeline**: Calling `Thread.sleep()`, JDBC drivers, or blocking HTTP clients freezes the Netty event loop and starves all other requests.
- **Never mix blocking JPA with WebFlux**: Use standard Spring MVC with Virtual Threads instead.
- **Avoid overcomplicating simple CRUD**: If an app consists of standard database queries and synchronous business logic, reactive programming introduces steep debugging complexity and stack trace obscurity.

### Essential Rules
- **Nothing happens until subscribe**: Return the `Mono`/`Flux` to the framework; never call `.block()` or `.subscribe()` inside a pipeline or WebFlux handler.
- **Defer eager evaluation**: `Mono.just(expensiveOrCurrentTime())` evaluates immediately at assembly time. Use `Mono.fromSupplier(...)` or `Mono.defer(...)` so execution happens on subscription.
- **Wrap unavoidable blocking calls**: `Mono.fromCallable(() -> legacyClient.call()).subscribeOn(Schedulers.boundedElastic())`.
- **Bound backpressure**: Never use unbounded buffers on fast producers; configure `onBackpressureBuffer(maxSize)`, `onBackpressureDrop()`, or `onBackpressureLatest()` to prevent OOM.
- **Errors & timeouts**: Use `.timeout(...)`, `.onErrorResume(...)`, `.retryWhen(Retry.backoff(...))`; never let errors drop silently.
- **`map` vs `flatMap`**: `map` for sync transforms; `flatMap` for calls returning `Mono`/`Flux` (`concatMap` when order matters).
- **Context, not `ThreadLocal`**: Pass request context via Reactor `Context` (threads switch mid-pipeline).
- **Test with `StepVerifier`**, not by blocking.

---

## 4. Modern Perspective: Virtual Threads vs. Reactor / WebFlux

| Dimension | Reactive (Flux / Mono) | Virtual Threads (Java 21+) |
| :--- | :--- | :--- |
| **Programming Model** | Functional, chained reactive operators | Standard imperative / sequential code |
| **Debugging / Stack Traces** | Difficult (asynchronous thread switches) | Simple (standard clean stack traces) |
| **Ecosystem Compatibility** | Requires reactive drivers (R2DBC, WebClient) | Works with all existing blocking code (JDBC, JPA) |
| **Best Fit** | Continuous event streaming & backpressure | High-volume I/O, REST APIs, microservices |

