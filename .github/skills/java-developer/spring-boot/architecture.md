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

## Common Pitfalls

- **`@Transactional` self-invocation**: Calling a `@Transactional` method from another method in the same class bypasses the proxy — no transaction. Move it to another bean. Same applies to `@Async` and `@Cacheable`.
- **Checked exceptions don't roll back** by default; use `rollbackFor` or throw unchecked exceptions.
- **N+1 queries**: Default associations to `LAZY`; fetch what you need with `JOIN FETCH`, `@EntityGraph`, or DTO projections. Enable SQL logging in dev to spot it.
- **Open Session in View**: Set `spring.jpa.open-in-view=false` so lazy loading can't leak into the web layer.
- **Entity `equals`/`hashCode`**: Don't use Lombok `@Data` on JPA entities; base equality on the ID (or business key) only.
