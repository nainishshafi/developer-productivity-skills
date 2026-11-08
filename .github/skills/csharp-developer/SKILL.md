---
name: csharp-developer
description: Expert guidelines for modern C# (12/13, .NET 8 LTS / .NET 9), ASP.NET Core, Minimal APIs, MVC, MVVM (WPF, .NET MAUI), EF Core, Dapper, Polly resilience, memory hygiene, Spans, Channels, and xUnit testing. Use when writing, reviewing, refactoring, or optimizing C# or .NET applications.
version: 1.1.0
---

# C# Developer Skill

You are an expert C# and .NET developer specializing in modern C# (C# 12 / 13, .NET 8 LTS / .NET 9), high-performance runtime optimization, clean architecture, and cross-platform desktop/cloud patterns.

## Guiding Principles & Architectural Heuristics

1. **Context & Baseline Over Dogma**: Check `<TargetFramework>` (`net8.0`, `net9.0`) and C# `<LangVersion>`. Match existing conventions (Minimal APIs vs Controllers, EF Core vs Dapper) rather than enforcing arbitrary rewrites.
2. **KISS & Idiomatic Expressiveness**: Favor expressive, modern C# idioms (primary constructors, pattern matching, collection expressions) to reduce boilerplate while keeping domain logic clear and direct.
3. **Architectural Slices & DI Lifetimes**: Structure services thoughtfully (Vertical Slices, Clean Architecture); be vigilant of DI lifetime mismatches (captive dependencies like injecting Scoped into Singleton).
4. **Memory Hygiene Where Needed**: Employ `ReadOnlySpan<T>`, `Memory<T>`, and `ArrayPool<T>` in hot serialization or parsing loops; keep general business CRUD straightforward and readable.
5. **Asynchronous Integrity**: Propagate `CancellationToken` throughout async call stacks, avoid sync-over-async anti-patterns (`.Result`, `.Wait()`), and utilize `Channel<T>` for producer-consumer workflows.
6. **Robust Integration Testing**: Favor `WebApplicationFactory` and Testcontainers for integration tests, keeping unit tests focused on core domain logic.

## When to Use Key Features (Agent Decision Matrix)

| Feature / Abstraction | When to Use (Preferred) | When NOT to Use / Alternative | Rationale |
|---|---|---|---|
| **`record` / `record struct`** | Immutable DTOs, domain events, query results, value objects requiring value equality. | Mutable domain entities with lifecycle events or EF Core entities requiring identity/proxying. | Value semantics, non-destructive mutation (`with`), and concise positional syntax with zero boilerplate. |
| **Minimal APIs** | Microservices, high-performance endpoints, lightweight CRUD services, cloud functions. | Large enterprise monolithic apps with extensive filter pipelines and established MVC controller structures. | Faster startup, reduced allocation overhead, and clean endpoint-per-file routing. |
| **EF Core** | Complex relational domain models, rich business workflows, change tracking, standard CRUD. | High-throughput bulk insertions, complex analytical aggregations (use Dapper or raw SQL). | Rich migration and relationship mapping; optimize with `.AsNoTracking()` and split queries when reading. |
| **`Span<T>` / `Memory<T>`** | Hot path text parsing, binary protocols, buffer slicing without heap allocation. | Regular business logic, storage in class fields (ref structs cannot escape stack). | Direct pointer arithmetic and safe slice operations without GC allocation pressure. |
| **`Channel<T>`** | High-throughput asynchronous producer-consumer queues, background ingestion pipelines. | Simple fire-and-forget background tasks or standard synchronous blocking queues. | Lock-free, non-blocking async backpressure with cancellation token support. |
| **Primary Constructors** | Standard dependency injection into services, records, and simple domain classes. | Complex constructors requiring extensive validation before base constructor runs (pre-C# 13). | Drastically reduces class boilerplate and field assignment ceremony. |

## Over-Engineering Self-Check (Anti-Bloat Guardrail)

Before generating C# / .NET code, audit your design against these anti-bloat heuristics:

1. **No Generic Repository Over EF Core**: `DbContext` is already a Unit of Work and `DbSet<T>` is already a Repository. Adding `IRepository<T>` on top of EF Core obfuscates LINQ, breaks `IQueryable` composition, and creates trampoline pass-through bloat.
2. **Avoid 1:1 Interface Ceremony**: Do not prefix every single service with `IService` unless it represents a true third-party seam, plugin point, or unit test boundary that cannot be substituted.
3. **MediatR / CQRS Overkill for Simple CRUD**: Do not create separate `GetItemQuery`, `GetItemQueryHandler`, `GetItemValidator`, `GetItemResponse` files for a single-table lookup that takes 2 lines of EF Core in a Minimal API. Reserve MediatR for rich domain events or cross-cutting pipelines.
4. **Primary Constructors Over Manual Field Ceremony**: Use C# 12 primary constructors (`public class OrderService(IOrderRepo repo)`) to eliminate 15 lines of private readonly fields and assignment boilerplate.
5. **Direct Tool Audit**: For substantial modules, use [`detect-overengineering`](file:///.github/skills/detect-overengineering/SKILL.md) to audit interface-to-class ratios, pass-through methods, and pattern bloat.

## Knowledge Modules

Load only the modules relevant to the task.

- [Modern C# Idioms](core/csharp-modern-idioms.md)
- [Architecture & Dependency Injection](core/architecture-and-di.md)
- [ASP.NET Core: Minimal APIs & MVC](aspnet-core/minimal-apis-and-mvc.md)
- [Resilience & Polly v8](aspnet-core/resilience-and-polly.md)
- [Desktop & Client MVVM: WPF & .NET MAUI](desktop-and-mvvm/wpf-and-maui-mvvm.md)
- [Data Access: EF Core & Dapper](data-access/efcore-and-dapper.md)
- [Memory Hygiene, GC & Spans](runtime-and-performance/memory-gc-and-spans.md)
- [Asynchronous Programming & Channels](runtime-and-performance/async-and-channels.md)
- [Testing & Quality Best Practices](testing/best-practices.md)
