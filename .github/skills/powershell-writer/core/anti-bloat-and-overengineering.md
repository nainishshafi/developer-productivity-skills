# PowerShell Anti-Bloat & Over-Engineering Guidelines

Architectural heuristics and pragmatism over dogmatic ceremony in PowerShell automation, cross-referencing [`detect-overengineering`](file:///.github/skills/detect-overengineering/SKILL.md).

---

## 1. Architectural Philosophy: Guidance Over Dogmatism

PowerShell is an automation language, an interactive command-line shell, and an object pipeline engine. Writing Staff-level PowerShell requires choosing the right level of abstraction for the problem without incurring enterprise class bloat:

- **Simple Scripts (`.ps1`)**: Ideal for linear build tasks, deployment sequences, or CI/CD job steps (< 150 lines).
- **Advanced Functions (`[CmdletBinding()]`)**: Ideal for reusable automation utilities that process pipeline input and require parameter validation.
- **Script Modules (`.psm1` / `.psd1`)**: Ideal when distributing a cohesive suite of cmdlets across a team or CI/CD runners.
- **PowerShell Classes (`class Foo { ... }`)**: Use sparingly. Ideal for strongly-typed DTOs, custom DSC resources, or complex domain models. **Do not** write Java-style class hierarchies when functions and `[PSCustomObject]` do the job cleanly.

---

## 2. Decision Matrix: Choosing the Right Abstraction

| Use Case | Recommended Abstraction | Avoid |
|---|---|---|
| Single automation task or CI step | Standalone `.ps1` script with parameters | Over-packaging into a module |
| Reusable tool invoked across scripts | Advanced Function with `[CmdletBinding()]` | Monolithic script with global variables |
| Returning structured data | `[PSCustomObject]@{ Id = 1; Name = '...' }` | Creating a dedicated `.cs` or PowerShell `class` |
| Group of 5+ related commands | Script Module (`.psm1` + `.psd1`) | Dot-sourcing multiple loose `.ps1` files |
| Custom collection filtering | Pipeline `Where-Object` or LINQ | Nested imperative for-loops with array appends |

---

## 3. Over-Engineering Self-Checks for PowerShell Engineers

Before finalizing PowerShell code, run these 5 self-checks:

1. **The Array Append Check ($O(N^2)$ Trap)**:
   - Did you write `$results = @(); foreach ($x in $y) { $results += $x }`?
   - In PowerShell, arrays are immutable. `+=` creates a new array in memory on **every iteration**, turning an $O(N)$ task into an $O(N^2)$ CPU and RAM bottleneck.
   - **Fix**: Stream via the pipeline, or use `$results = foreach ($x in $y) { $x }`, or use `[System.Collections.Generic.List[object]]::new()`.

2. **The Class Bloat Check**:
   - Did you create a PowerShell `class` with getters, setters, and private fields just to return 4 properties?
   - **Fix**: Emit a `[PSCustomObject]` hash table literal. PowerShell cmdlets, `Format-Table`, and `Export-Csv` work natively with `PSCustomObject`.

3. **The Global Variable Check**:
   - Did you use `$global:variable` to pass state between functions?
   - **Fix**: Pass parameters explicitly or return structured objects through the pipeline. Never pollute the global shell session.

4. **The `Invoke-Expression` (`iex`) Trap**:
   - Did you use `Invoke-Expression` to run a dynamic command?
   - `iex` is a major security vulnerability (arbitrary code injection) and disables parsing optimizations.
   - **Fix**: Use the call operator `& $cmd @args` or splatting.

5. **The Redundant Wrapper Check**:
   - Did you write a custom function that simply wraps a native cmdlet without adding validation, error handling, or transformations?
   - **Fix**: Use the native cmdlet directly or use a parameter alias.

