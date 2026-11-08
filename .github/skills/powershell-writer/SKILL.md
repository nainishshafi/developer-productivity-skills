---
name: powershell-writer
description: Writes idiomatic, high-performance, and secure PowerShell scripts, modules, and automation workflows (PowerShell 7.4+ LTS & Windows PowerShell 5.1). Covers advanced functions ([CmdletBinding]), approved verbs, object pipeline streaming, error handling with Set-StrictMode, Pester v5 testing, PSScriptAnalyzer rules, and parallel concurrency. Use when asked to "write powershell", "powershell script", "create powershell module", "powershell-writer", "ps1 script", "pester test", or "powershell automation".
version: 1.0.0
---

# PowerShell Writer

Staff-level guidance for authoring production-grade PowerShell scripts, advanced functions, and enterprise modules across cross-platform environments (Windows, Linux, macOS).

---

## When to Use This Skill

- Writing standalone automation scripts (`.ps1`) or reusable modules (`.psm1` / `.psd1`).
- Implementing advanced cmdlets with `[CmdletBinding()]`, parameter validation, and pipeline streaming (`begin`/`process`/`end`).
- Enforcing defensive error handling with `$ErrorActionPreference = 'Stop'`, `try/catch`, and `Set-StrictMode`.
- Eliminating performance bottlenecks like the $O(N^2)$ array append antipattern (`$arr += $item`).
- Multi-threading and background tasks using `ForEach-Object -Parallel`, `Start-ThreadJob`, or Runspaces.
- Authoring unit tests with Pester v5 and linting with PSScriptAnalyzer.

---

## Architectural Philosophy: Guidance Over Dogmatism

PowerShell is an object-oriented shell and automation engine. Heuristics guide design:
- Prefer simple `.ps1` scripts for linear orchestration (< 150 lines); use Modules (`.psm1`) when distributing 5+ reusable cmdlets.
- Emit structured `[PSCustomObject]` rather than raw strings or bloated custom C# class hierarchies.
- Never use `Invoke-Expression` (`iex`); pass arrays or use the call operator (`&`).
- Always validate manifests using `Test-ModuleManifest` before shipping.

---

## Core Knowledge Modules

Load the relevant module based on your task:

| Domain | Description | Module File |
|---|---|---|
| **Core & Cmdlet Design** | `[CmdletBinding()]`, approved verbs, pipeline binding, parameter validation | [Cmdlet Design](file:///.github/skills/powershell-writer/core/advanced-functions-and-cmdlets.md) |
| **Error Handling** | `$ErrorActionPreference = 'Stop'`, `Set-StrictMode`, `try/catch`, `$LASTEXITCODE` | [Error Handling](file:///.github/skills/powershell-writer/core/error-handling-and-strictmode.md) |
| **Anti-Bloat & Pragmatism** | Decision matrix, over-engineering self-checks, avoiding $O(N^2)$ array traps | [Anti-Bloat Guidelines](file:///.github/skills/powershell-writer/core/anti-bloat-and-overengineering.md) |
| **Pipeline & Splatting** | Streaming, `[PSCustomObject]`, calculated properties, hashtable splatting (`@params`) | [Pipeline & Objects](file:///.github/skills/powershell-writer/pipeline-and-streaming/pipeline-and-custom-objects.md) |
| **Data & REST APIs** | `Invoke-RestMethod`, JSON depth limits, CSV/XML, native CLI argument quoting | [Data & REST APIs](file:///.github/skills/powershell-writer/pipeline-and-streaming/data-parsing-and-rest.md) |
| **Concurrency & Jobs** | `ForEach-Object -Parallel`, thread-safe collections, `Start-ThreadJob`, Runspaces | [Concurrency & Parallelism](file:///.github/skills/powershell-writer/concurrency/jobs-and-parallelism.md) |
| **Module Architecture** | Professional directory layout, `.psm1`, `.psd1` manifests, `Export-ModuleMember` | [Module Architecture](file:///.github/skills/powershell-writer/modules/module-architecture-and-manifests.md) |
| **Security & Hardening** | `iex` ban, SecureString, SecretManagement, ExecutionPolicy, CLM | [Security & Hardening](file:///.github/skills/powershell-writer/security/security-and-hardening.md) |
| **Testing & Quality** | Pester v5 test patterns (`Discovery` vs `Run`), mocks, PSScriptAnalyzer rules | [Testing with Pester v5](file:///.github/skills/powershell-writer/testing/pester-and-scriptanalyzer.md) |

---

## References

- [PowerShell Writer Reference Guide](file:///.github/skills/powershell-writer/references/powershell-writer-reference.md) — Comprehensive architectural and operational reference.
- [Code Reviewer](file:///.github/skills/code-reviewer/SKILL.md) — Multi-language senior code review skill.
- [API Security](file:///.github/skills/api-security/SKILL.md) — Universal API security and authentication audit.
- [Detect Overengineering](file:///.github/skills/detect-overengineering/SKILL.md) — Anti-bloat heuristics and YAGNI auditing.
