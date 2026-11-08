# PowerShell Pipeline, Concurrency & Module Review Guide

Audit guide for advanced PowerShell pipeline streaming, parallelism, and module packaging.

---

## 1. Concurrency & Parallelism Review

- [ ] **`-Parallel` Variable Scoping**:
  - In `ForEach-Object -Parallel`, are outer script variables referenced with the `$using:` prefix (e.g. `$using:targetPort`)?
  - Omitting `$using:` causes silent `$null` values in child threads.
- [ ] **`-ThrottleLimit` Specification**:
  - Is `-ThrottleLimit` set appropriately rather than defaulting to 5?
- [ ] **Thread-Safe Shared Collections**:
  - Are parallel blocks mutating a standard `$hash = @{}` or `$list = @()` concurrently?
  - Multi-threaded writes to standard hashtables cause corrupt internal buckets or runtime exceptions.
  - **Resolution**: Use `[hashtable]::Synchronized(@{})` or `[System.Collections.Concurrent.ConcurrentBag[object]]::new()`.

---

## 2. JSON & Data Serialization

- [ ] **`ConvertTo-Json -Depth` Truncation**:
  - Is `ConvertTo-Json` called without an explicit `-Depth` parameter?
  - Default depth is 2; nested properties deeper than 2 levels are silently converted into string type names!
  - **Resolution**: Always pass `-Depth 10` or higher.

---

## 3. Module Manifest Review

- [ ] **No Wildcard `FunctionsToExport`**:
  - Does `MyModule.psd1` have `FunctionsToExport = '*'`? Flag as `[P2 - Minor]`.
  - Wildcard exports degrade command discovery performance and prevent clean tab-completion until loaded.
- [ ] **Manifest Validation**:
  - Does the module pass `Test-ModuleManifest` cleanly?
- [ ] **PSScriptAnalyzer Clean**:
  - Does the code pass `Invoke-ScriptAnalyzer -Severity Error, Warning` with zero violations?
