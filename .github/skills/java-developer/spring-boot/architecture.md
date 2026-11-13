# Spring Boot Architecture & Layering

## Package Structure

Follow the project's existing layout. For new projects, prefer **package-by-feature** once the app grows beyond a few entities; layered packages are fine for small services.

```text
# Package-by-layer (small services)       # Package-by-feature (growing apps)
com/example/app/                           com/example/app/
├── controller/                            ├── order/
├── service/                               │   ├── OrderController.java
├── repository/                            │   ├── OrderService.java
├── model/                                 │   ├── OrderRepository.java
├── dto/                                   │   └── Order.java
└── config/                                ├── customer/
                                           └── config/
```

Within a feature package, keep implementation classes package-private where possible.

## Layer Directives

1. **Controllers**:
   - Keep controllers thin. They should only handle HTTP concerns, parameter validation, and status codes.
   - Never place business logic or direct database queries in controllers.
   - Return DTO records (or `ResponseEntity<T>` when you need custom status/headers).

2. **Services**:
   - Business logic resides here.
   - Put `@Transactional` on service methods (not controllers/repositories). Use `@Transactional(readOnly = true)` for reads.
   - Coordinate cross-cutting concerns (auditing, events, notifications).
   - Don't make remote HTTP calls inside a DB transaction — it holds connections open.

3. **Repositories**:
   - Use Spring Data interfaces (`JpaRepository`, `CrudRepository`).
   - Write custom query methods with Spring Data method conventions or `@Query`.
   - Paginate unbounded queries (`Pageable`); never `findAll()` on large tables.

4. **DTOs & Mappers**:
   - Never expose JPA entities directly to the client layer. Use DTO records.
   - Use mapping libraries (e.g., MapStruct) or explicit factory methods to transform between entities and DTOs.

5. **Configuration & Data Connectors (`config/`)**:
   - **Typed Settings (`@ConfigurationProperties`)**: Bind externalized config (`application.yml`, env vars) to immutable `@ConfigurationProperties` `record`s with `@Validated` (`@NotBlank`, `@Positive`) instead of scattering `@Value` strings across services.
   - **Database Connectors (`DataSource` / HikariCP)**:
     - *Single database*: Rely on Spring Boot's auto-configured HikariCP `DataSource` (`spring.datasource.*`) and tune `maximum-pool-size`, `connection-timeout`, and `leak-detection-threshold` rather than writing boilerplate `@Bean DataSource`.
     - *Multiple databases*: Define one `@Configuration` class per connector (`@ConfigurationProperties(prefix = "app.datasource.reporting")`), creating dedicated `DataSource`, `JdbcClient` (or `EntityManagerFactory`), and `PlatformTransactionManager` beans. Mark the primary store `@Primary` and wire secondary connectors explicitly with `@Qualifier`.
   - **External API / Service Connectors (`RestClient` / `@HttpExchange`)**:
     - Wire `RestClient` or declarative `@HttpExchange` interfaces as `@Bean`s in `config/` with explicit connect/read timeouts, base URLs from `@ConfigurationProperties`, and auth/logging interceptors — never instantiate `RestClient.create()` inside `@Service` methods.
   - **Boundary Rule**: Keep `config/` strictly for bean wiring, connection pools, and connector adapters; never place business logic inside `@Configuration` classes.
   - See [Modular Configuration & Data Connectors](configuration-and-data-connectors.md) for full `@ConfigurationProperties`, multi-`DataSource`, `RestClient`, `@ConditionalOnProperty`, and `ApplicationContextRunner` implementation examples.

## Common Pitfalls

- **`@Transactional` self-invocation**: Calling a `@Transactional` method from another method in the same class bypasses the proxy — no transaction. Move it to another bean. Same applies to `@Async` and `@Cacheable`.
- **Checked exceptions don't roll back** by default; use `rollbackFor` or throw unchecked exceptions.
- **Lost Updates (Concurrency)**: Add `@Version` to mutable JPA entities for optimistic locking so concurrent updates fail fast instead of silently overwriting each other.
- **N+1 queries & Pagination**: Default associations to `LAZY`; fetch what you need with `JOIN FETCH`, `@EntityGraph`, or DTO projections. Never combine `JOIN FETCH` on a collection (`@OneToMany`) with `Pageable` — Hibernate loads the entire table into memory; paginate IDs first or use `@BatchSize`.
- **Open Session in View**: Set `spring.jpa.open-in-view=false` so lazy loading can't leak into the web layer.
- **Schema Management**: Use Flyway or Liquibase for migrations and set `spring.jpa.hibernate.ddl-auto=validate` in production (never `update` or `create-drop`).
- **Entity `equals`/`hashCode`**: Don't use Lombok `@Data` on JPA entities; base equality on the ID (or business key) only.
