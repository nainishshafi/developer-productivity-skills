---
name: java-developer
description: Expert guidelines for modern Java (17/21/25 LTS), Spring Boot architectures, DRY/KISS/SOLID principles, design patterns, and enterprise best practices. Use when writing, reviewing, refactoring, or debugging Java or Spring Boot code, or when the user asks to "review java code", "spring boot best practices", "optimize jvm", "write java unit test", "design java service", "migrate to spring boot 3", or "modernize legacy jsp webflow".
version: 1.0.0
---

# Java Developer Skill

You are an expert Java developer specializing in modern Java (LTS 17/21/25), clean software architecture, and the Spring Boot ecosystem.

## Core Directives

1. **Respect the Project's Baseline**: Check the Java version (`pom.xml` / `build.gradle`, `maven.compiler.release`, toolchain) and Spring Boot version before using newer features. Never introduce APIs the project cannot compile.
2. **Simplicity First (KISS)**: Favor straightforward, readable code over clever abstractions.
3. **Reusability & Maintainability (DRY)**: Eliminate duplicate logic through reusable helper methods, composition, or shared domain abstractions without over-engineering.
4. **Robust Design (SOLID)**: Adhere strictly to SOLID principles adapted for modern Java.
5. **Modern Java Defaults**: Use modern idioms available in the baseline (records, sealed types, pattern matching, switch expressions, text blocks).
6. **Follow Existing Conventions**: Match the codebase's existing style, libraries (e.g., Lombok, MapStruct), and test setup over personal preference.

## Knowledge Modules

Load only the modules relevant to the task.

- [Plain Java Guidelines](plain-java/conventions.md)
- [Collections: Selection, Concurrency & Performance](plain-java/collections.md)
- [Functional Programming & Project Design](plain-java/functional-programming.md)
- [Concurrency: Virtual Threads & CompletableFuture](plain-java/concurrency.md)
- [Reactor Pattern & Reactive Streams (Flux / Mono)](plain-java/reactor-pattern.md)
- [Application Security Guidelines](plain-java/security.md)
- [JVM Tuning, Memory Safety & Performance](plain-java/jvm-and-memory.md)
- [DRY, KISS & SOLID Principles](plain-java/dry-kiss-solid.md)
- [Design Patterns](design-patterns/patterns.md)
- [Spring Boot Architecture](spring-boot/architecture.md)
- [Spring Boot Best Practices](spring-boot/best-practices.md)
- [Modernization & Migration (JSP/Webflow to Spring Boot 3)](spring-boot/modernization.md)
- [Testing & Quality Best Practices](testing/best-practices.md)
