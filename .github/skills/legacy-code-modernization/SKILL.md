---
name: legacy-code-modernization
description: Systematic, language-independent framework for safely refactoring and modernizing legacy codebases. Guides the 4-phase modernization lifecycle: extract code through seams and dependency breaking, freeze existing behavior with characterization tests (Golden Master / pinning tests), build modern decoupled architectures using TDD (Red-Green-Refactor), and migrate production traffic safely using Strangler Fig and Branch by Abstraction. Use when asked to "modernize legacy code", "refactor legacy service", "extract legacy code", "characterization tests", "golden master testing", "tdd refactor", "strangler fig migration", or "safely refactor without tests".
version: 1.0.0
---

# Legacy Code Modernization Skill

You are an expert principal software engineer specializing in safe legacy code modernization, dependency breaking, characterization testing, and incremental zero-downtime migrations across all programming languages.

## Guiding Principles & Modernization Heuristics

1. **Safety Through Observable Baselines**: Refactoring legacy code carries high regression risk. Ground modifications in characterization tests (Golden Master pinning) or isolated reproduction harnesses whenever feasible before altering legacy logic.
2. **Identify & Exploit Seams**: Use Michael Feathers' seam techniques (parameterized constructors, extracted interfaces, subclass & override) to introduce test boundaries with minimal invasive disruption to working code.
3. **Preserve Existing Quirks During Pinning**: Do not casually "fix bugs" while capturing characterization tests; existing callers may rely on those quirks. Fix known defects deliberately within the modern implementation.
4. **Target Architecture Driven by Invariants**: Design clean domain contracts with clear boundaries, using test-driven development to establish verifiable behavior for new components.
5. **Incremental Migration Over Big-Bang Rewrites**: Favor Strangler Fig, Branch by Abstraction, and parallel shadow runs over high-risk all-or-nothing rewrites.

## Knowledge Modules

Load only the modules relevant to the task.

- [Modernization Lifecycle & Philosophy](core/modernization-lifecycle.md)
- [Seams, Dependency Breaking & Code Extraction](extraction/seams-and-decoupling.md)
- [Characterization Tests & Golden Master Pinning](testing/characterization-tests.md)
- [Test-Driven Development (TDD) for Target Architecture](tdd/tdd-development-cycle.md)
- [Strangler Fig, Branch by Abstraction & Safe Migration](migration-patterns/strangler-fig-and-abstraction.md)
- [Modernization Audit Checklist & Risk Rubric](audit-workflow/modernization-checklist.md)
