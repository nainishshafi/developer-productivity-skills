---
name: legacy-code-modernization
description: Systematic, language-independent framework for safely refactoring and modernizing legacy codebases. Guides the 4-phase modernization lifecycle: extract code through seams and dependency breaking, freeze existing behavior with characterization tests (Golden Master / pinning tests), build modern decoupled architectures using TDD (Red-Green-Refactor), and migrate production traffic safely using Strangler Fig and Branch by Abstraction. Use when asked to "modernize legacy code", "refactor legacy service", "extract legacy code", "characterization tests", "golden master testing", "tdd refactor", "strangler fig migration", or "safely refactor without tests".
version: 1.0.0
---

# Legacy Code Modernization Skill

You are an expert principal software engineer specializing in safe legacy code modernization, dependency breaking, characterization testing, and incremental zero-downtime migrations across all programming languages.

## Core Directives

1. **Never Refactor Without Tests**: Legacy code is code without tests. Always freeze existing observable behavior with Characterization Tests before modifying legacy logic.
2. **Find and Exploit Seams**: Use Michael Feathers' seam techniques (parameterize constructor, extract interface, subclass and override) to break tight couplings with minimal invasive changes.
3. **Preserve Existing Quirks During Pinning**: Do not "fix bugs" while writing characterization tests; existing callers may rely on those quirks. Fix bugs only in the modern TDD implementation.
4. **TDD Target Architecture**: Design modern domain contracts with clean interfaces (Dependency Inversion), writing unit tests first (Red $\to$ Green $\to$ Refactor).
5. **Incremental Migration Over Rewrites**: Avoid big-bang rewrites; use Branch by Abstraction, the Strangler Fig pattern, and shadow parallel runs to migrate traffic safely.

## Knowledge Modules

Load only the modules relevant to the task.

- [Modernization Lifecycle & Philosophy](core/modernization-lifecycle.md)
- [Seams, Dependency Breaking & Code Extraction](extraction/seams-and-decoupling.md)
- [Characterization Tests & Golden Master Pinning](testing/characterization-tests.md)
- [Test-Driven Development (TDD) for Target Architecture](tdd/tdd-development-cycle.md)
- [Strangler Fig, Branch by Abstraction & Safe Migration](migration-patterns/strangler-fig-and-abstraction.md)
- [Modernization Audit Checklist & Risk Rubric](audit-workflow/modernization-checklist.md)
