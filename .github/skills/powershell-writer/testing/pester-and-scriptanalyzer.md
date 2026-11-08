# PowerShell Testing with Pester v5 & PSScriptAnalyzer

Staff-level testing guide for Pester v5 unit tests, command mocking, and static analysis with PSScriptAnalyzer.

---

## 1. Pester v5 Architecture (`Discovery` vs. `Run` Phases)

Pester v5 separates execution into two phases:
1. **Discovery Phase**: Evaluates all code outside of `BeforeAll`, `BeforeEach`, `It`, and `AfterAll` blocks to discover test cases.
2. **Run Phase**: Executes the actual tests and setup/teardown blocks.

### The Cardinal Rule of Pester v5:
All variable initialization, module imports, and mocks must live inside `BeforeAll` or `BeforeEach` blocks, **never floating in the root script body**!

```powershell
# Get-SystemHealthReport.Tests.ps1

BeforeAll {
    # Import target function or module
    . $PSScriptRoot/../Public/Get-SystemHealthReport.ps1
}

Describe 'Get-SystemHealthReport' {
    Context 'When operating normally' {
        BeforeAll {
            # Mock external CIM call
            Mock Get-CimInstance {
                [PSCustomObject]@{
                    FreePhysicalMemory      = 2097152   # 2048 MB
                    TotalVisibleMemorySize = 8388608   # 8192 MB
                    LastBootUpTime          = [System.DateTime]::Parse('2026-01-01T00:00:00Z')
                }
            } -ParameterFilter { $ClassName -eq 'Win32_OperatingSystem' }
        }

        It 'Returns a PSCustomObject with expected properties' {
            $report = Get-SystemHealthReport
            $report | Should -Not -BeNullOrEmpty
            $report.Status | Should -Be 'Healthy'
            $report.FreeMemoryMb | Should -Be 2048
            $report.PercentFree | Should -Be 25.0
        }

        It 'Invoked Get-CimInstance exactly once' {
            Should -Invoke Get-CimInstance -Times 1 -Exactly -ParameterFilter { $ClassName -eq 'Win32_OperatingSystem' }
        }
    }

    Context 'When free memory is critical (< 500 MB)' {
        BeforeAll {
            Mock Get-CimInstance {
                [PSCustomObject]@{
                    FreePhysicalMemory      = 307200    # 300 MB
                    TotalVisibleMemorySize = 8388608
                    LastBootUpTime          = [System.DateTime]::UtcNow
                }
            }
        }

        It 'Sets Status to Critical' {
            $report = Get-SystemHealthReport
            $report.Status | Should -Be 'Critical'
        }
    }
}
```

---

## 2. Pester Assertions Cheat Sheet

| Assertion | Usage |
|---|---|
| `$val \| Should -Be $expected` | Strict equality check. |
| `$val \| Should -BeExactly $expected` | Case-sensitive equality check. |
| `$val \| Should -BeNullOrEmpty` | Checks for `$null`, `""`, or empty collection. |
| `$val \| Should -BeOfType [string]` | Checks runtime .NET type. |
| `$list \| Should -Contain 'foo'` | Verifies collection contains item. |
| `{ Invoke-FailingCmdlet } \| Should -Throw` | Verifies script block throws an exception. |
| `{ Invoke-FailingCmdlet } \| Should -Throw -ExpectedMessage "*timeout*"` | Checks wildcard exception message. |

---

## 3. Static Analysis with PSScriptAnalyzer

PSScriptAnalyzer is the standard static linter for PowerShell:

```powershell
# Run full analysis on module
$analysisResults = Invoke-ScriptAnalyzer -Path ./MyModule -Recurse -Severity Error, Warning

if ($analysisResults) {
    $analysisResults | Format-Table RuleName, Severity, ScriptName, Line
    throw "PSScriptAnalyzer detected $($analysisResults.Count) errors or warnings!"
}
```

### Critical Rules Enforced:
- `PSAvoidUsingInvokeExpression`: Bans `iex`.
- `PSAvoidUsingPlainTextForPassword`: Catches hardcoded passwords or strings used for secrets.
- `PSUseDeclaredVarsMoreThanAssignments`: Detects dead/unused variables.
- `PSUseApprovedVerbs`: Enforces standard cmdlet naming.
- `PSAvoidUsingPositionalParameters`: Recommends explicit named parameters in scripts for maintainability.

