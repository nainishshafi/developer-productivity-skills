# PowerShell Code Review Checklist

Senior-level review checklist for PowerShell scripts and modules, cross-referencing [`powershell-writer`](file:///.github/skills/powershell-writer/SKILL.md).

---

## 1. Security & Execution Safety

- [ ] **No `Invoke-Expression` (`iex`)**:
  - Is `Invoke-Expression` used on any input or dynamically constructed string?
  - Flag `Invoke-Expression` as `[P0 - Blocker]` due to arbitrary command injection risks.
  - Use call operator (`& $cmd @args`) or splatting instead.
- [ ] **No Plaintext Passwords / API Keys**:
  - Are secrets, passwords, or tokens hardcoded in `.ps1`, `.psm1`, or `.psd1` files? Flag as `[P0 - Blocker]`.
  - Use `[pscredential]` parameters, Azure Key Vault, or `SecretManagement` module.
- [ ] **Strict Mode & Error Action**:
  - Do production automation scripts declare `$ErrorActionPreference = 'Stop'` and `Set-StrictMode -Version Latest` at the top?
  - Unhandled non-terminating errors silently continue by default if `$ErrorActionPreference` is not `'Stop'`.

---

## 2. Cmdlet Design & Approved Verbs

- [ ] **Approved Verbs**:
  - Do function names follow `Verb-Noun` with approved verbs from `Get-Verb` (`Get`, `Set`, `New`, `Remove`, `Invoke`, `Test`)?
  - Unapproved verbs trigger PSScriptAnalyzer warnings and create inconsistent API surface.
- [ ] **Singular Nouns**:
  - Are nouns singular (`Get-AgyUser`, not `Get-AgyUsers`)?
- [ ] **`[CmdletBinding()]` Declaration**:
  - Do functions declare `[CmdletBinding()]` to support `-Verbose`, `-Debug`, and common parameters?
- [ ] **Parameter Validation**:
  - Are parameters guarded with declarative attributes (`[ValidateNotNullOrEmpty()]`, `[ValidateSet()]`, `[ValidateRange()]`) instead of manual imperative checks?

---

## 3. Pipeline Streaming & Memory Hygiene

- [ ] **The $O(N^2)$ Array Addition Antipattern**:
  - Did the author write `$arr = @(); foreach ($x in $y) { $arr += $x }`? Flag as `[P1 - Major]` on non-trivial loops.
  - Arrays are immutable in .NET; `+=` reallocates the array on every element.
  - **Resolution**: Use pipeline streaming, assign loop directly (`$arr = foreach ($x in $y) { $x }`), or use `[System.Collections.Generic.List[object]]::new()`.
- [ ] **`process` Block in Pipeline Functions**:
  - If a function accepts `ValueFromPipeline`, are statements inside a `process { ... }` block?
  - Code outside `process` only runs once for the **last** item in the pipeline!

---

## 4. Native CLI Integration

- [ ] **Checking `$LASTEXITCODE`**:
  - Does the script invoke native binaries (`git`, `docker`, `npm`, `kubectl`) without verifying `$LASTEXITCODE -eq 0`?
  - PowerShell does not throw on native executable failures by default.
