# PowerShell Advanced Functions & Cmdlet Design

Staff-level guide to writing idiomatic, robust PowerShell functions and cmdlets (PowerShell 7.4+ LTS / Windows PowerShell 5.1).

---

## 1. Approved Verbs & Cmdlet Naming

Always follow the `Verb-Noun` naming convention using officially approved verbs:
- Check approved verbs using `Get-Verb`.
- **Common Lifecycle Verbs**:
  - `Get`: Retrieve resource(s) without modifying state.
  - `Set`: Modify existing resource state.
  - `New`: Create a new resource.
  - `Remove`: Delete or destroy a resource.
  - `Invoke`: Execute an operation or action (e.g., `Invoke-DatabaseQuery`, `Invoke-RestApi`).
  - `Test`: Return boolean `$true` / `$false` verifying a condition (e.g., `Test-NetworkPort`).
  - `Find`: Search for resources.
- **Noun Rules**:
  - Use **singular nouns** (e.g., `Get-ServiceProcess`, not `Get-ServiceProcesses`).
  - Use a descriptive prefix to avoid name collisions (e.g., `Get-AgyUser`, `New-OrgProject`).

---

## 2. Advanced Function Anatomy (`[CmdletBinding()]`)

Always declare `[CmdletBinding()]` to turn a script into an advanced function supporting `-Verbose`, `-Debug`, `-ErrorAction`, and `-WhatIf`.

```powershell
function Invoke-DataSync {
    [CmdletBinding(
        SupportsShouldProcess = $true,
        ConfirmImpact = 'Medium',
        DefaultParameterSetName = 'ByName'
    )]
    [OutputType([PSCustomObject])]
    param(
        [Parameter(
            Mandatory = $true,
            Position = 0,
            ParameterSetName = 'ByName',
            ValueFromPipeline = $true,
            ValueFromPipelineByPropertyName = $true,
            HelpMessage = 'Target dataset name to synchronize'
        )]
        [ValidateNotNullOrEmpty()]
        [ValidateLength(3, 64)]
        [string]$Name,

        [Parameter(
            Mandatory = $true,
            ParameterSetName = 'ById',
            ValueFromPipelineByPropertyName = $true
        )]
        [ValidateRange(1, [int]::MaxValue)]
        [int]$Id,

        [Parameter()]
        [ValidateSet('Incremental', 'Full', 'SchemaOnly')]
        [string]$SyncMode = 'Incremental',

        [Parameter()]
        [switch]$Force
    )

    begin {
        Write-Verbose "[$($MyInvocation.MyCommand)] Starting synchronization pipeline..."
        $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
        $processedCount = 0
    }

    process {
        $targetIdentifier = if ($PSCmdlet.ParameterSetName -eq 'ByName') { $Name } else { "ID:$Id" }
        Write-Verbose "[$($MyInvocation.MyCommand)] Processing target: $targetIdentifier in $SyncMode mode"

        # SupportsShouldProcess (-WhatIf and -Confirm) support
        if ($PSCmdlet.ShouldProcess($targetIdentifier, "Execute $SyncMode data sync")) {
            try {
                # Simulated payload generation
                $result = [PSCustomObject]@{
                    Target       = $targetIdentifier
                    SyncMode     = $SyncMode
                    Status       = 'Success'
                    TimestampUtc = [System.DateTime]::UtcNow
                }

                $processedCount++
                $result # Stream to pipeline immediately
            }
            catch {
                Write-Error -Message "Failed synchronizing $targetIdentifier: $($_.Exception.Message)" `
                            -Category OperationStopped `
                            -TargetObject $targetIdentifier
            }
        }
    }

    end {
        $stopwatch.Stop()
        Write-Verbose "[$($MyInvocation.MyCommand)] Completed. Processed $processedCount targets in $($stopwatch.ElapsedMilliseconds)ms"
    }

    clean {
        # PowerShell 7.3+ clean block for guaranteed cleanup even upon pipeline halt
        Write-Verbose "[$($MyInvocation.MyCommand)] Cleanup executed"
    }
}
```

---

## 3. Parameter Validation Attributes

Never write manual `if ($param -eq $null)` checks when declarative attributes exist:

| Attribute | Example | Purpose |
|---|---|---|
| `[ValidateNotNullOrEmpty()]` | `[string]$Path` | Rejects `$null`, `""`, and empty arrays. |
| `[ValidateSet('A', 'B', 'C')]` | `[string]$Env` | Restricts allowed values to an explicit enumeration with tab-completion. |
| `[ValidateRange(min, max)]` | `[int]$Port` | Enforces numerical boundaries (e.g. `1, 65535`). |
| `[ValidatePattern('^regex$')]` | `[string]$Email` | Validates strings against regular expressions. |
| `[ValidateScript({ Test-Path $_ })]` | `[string]$ConfigFile` | Executes custom validation script block; throws if returns `$false`. |
| `[ValidateCount(min, max)]` | `[string[]]$Servers` | Enforces collection size bounds. |

---

## 4. Pipeline Binding Rules

PowerShell pipelines process items one-at-a-time through streaming:
- `ValueFromPipeline = $true`: The entire piped object binds to this parameter.
- `ValueFromPipelineByPropertyName = $true`: The piped object's property with matching name binds to this parameter.
- **Always provide `begin`, `process`, and `end` blocks** when writing functions that accept pipeline input. If omitted, the function body behaves as an `end` block and will only process the **last** piped element!
