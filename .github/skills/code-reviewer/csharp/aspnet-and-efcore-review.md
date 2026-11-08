# ASP.NET Core & EF Core Review Guide

Audit guide for ASP.NET Core APIs, Entity Framework Core, Dapper, and database persistence in .NET.

---

## 1. ASP.NET Core & Minimal APIs

- [ ] **Typed Results**:
  - Are Minimal API endpoints returning `Results<Ok<T>, NotFound, BadRequest>` for type safety and OpenAPI generation?
- [ ] **Dependency Injection Lifetimes**:
  - Are service lifetimes configured correctly (`AddTransient`, `AddScoped`, `AddSingleton`)?
  - Flag injecting a `Scoped` service (e.g. `DbContext`) into a `Singleton` service as a captive dependency `[P0 - Blocker]`.
- [ ] **Exception Handling Middleware**:
  - Is `app.UseExceptionHandler()` configured to return standardized RFC 7807 `ProblemDetails`?

---

## 2. Entity Framework Core Performance

- [ ] **`AsNoTracking()` on Queries**:
  - Are read-only queries marked with `.AsNoTracking()`?
  - Omitting `.AsNoTracking()` forces EF Core to create snapshot tracker instances for every entity, consuming double memory and CPU.
- [ ] **N+1 Query Detection**:
  - Are navigation properties loaded eagerly via `.Include()` / `.ThenInclude()` or projected using `.Select()`?
- [ ] **Split Queries**:
  - When loading multiple collection includes, is `.AsSplitQuery()` used to prevent Cartesian explosive joins?
- [ ] **Client Evaluation Hazards**:
  - Are methods or C# expressions in LINQ `Where` clauses causing full table retrieval and client-side evaluation?
  - Verify queries translate directly to SQL.

---

## 3. Dapper & Direct SQL

- [ ] **Parameterized Queries**:
  - Are all Dapper queries passing parameters via anonymous objects (`new { id }`) rather than string interpolation? Flag interpolated raw SQL as `[P0 - Blocker]`.
- [ ] **Connection Lifecycle**:
  - Are `IDbConnection` instances wrapped in `await using var connection = ...`?

---

## 4. Resilience & Polly

- [ ] **Retry with Jitter**:
  - Are outgoing HTTP clients configured with resilience pipelines (Polly v8) using exponential backoff with jitter?
- [ ] **Circuit Breakers**:
  - Do external API integrations trip circuit breakers when external services fail consistently?

