# PowerShell Pipeline, PSCustomObject & Splatting

Staff-level guide to PowerShell's object pipeline, streaming performance, and parameter splatting.

---

## 1. Object Pipeline vs. Text Parsing

Unlike Unix shells that pipe raw byte streams (`stdout`), PowerShell pipes **live .NET objects**:
- Never parse output strings using regex or `awk`/`grep` unless consuming output from an external legacy executable.
- Inspect object properties and methods using `Get-Member` (`gm`).
- Filter objects using `Where-Object` (`?`) or `.Where({ $_.Status -eq 'Active' })`.
- Project properties using `Select-Object` (`select`).

---

## 2. Emitting Structured `[PSCustomObject]`

The idiomatic return type for PowerShell functions is a `[PSCustomObject]`:

```powershell
function Get-SystemHealthReport {
    [CmdletBinding()]
    [OutputType([PSCustomObject])]
    param()

    $os = Get-CimInstance -ClassName Win32_OperatingSystem
    $freeMemoryMb = [math]::Round($os.FreePhysicalMemory / 1024, 2)
    $totalMemoryMb = [math]::Round($os.TotalVisibleMemorySize / 1024, 2)

    [PSCustomObject]@{
        ComputerName   = $env:COMPUTERNAME
        FreeMemoryMb   = $freeMemoryMb
        TotalMemoryMb  = $totalMemoryMb
        PercentFree    = [math]::Round(($freeMemoryMb / $totalMemoryMb) * 100, 1)
        LastBootUpTime = $os.LastBootUpTime
        Status         = if ($freeMemoryMb -lt 500) { 'Critical' } else { 'Healthy' }
    }
}
```

### Calculated Properties with `Select-Object`
When transforming objects in a pipeline, use calculated properties:

```powershell
Get-ChildItem -File |
    Select-Object Name,
                  @{ Name = 'SizeMB'; Expression = { [math]::Round($_.Length / 1MB, 2) } },
                  @{ Name = 'AgeDays'; Expression = { (New-TimeSpan -Start $_.LastWriteTime -End (Get-Date)).Days } }
```

---

## 3. High-Performance Collection Accumulation ($O(N)$ vs. $O(N^2)$)

### The $O(N^2)$ Array Addition Antipattern
```powershell
# TERRIBLE: Reallocates and copies array on every single iteration
$items = @()
foreach ($file in (Get-ChildItem -Path C:\Logs -Recurse)) {
    $items += [PSCustomObject]@{ File = $file.Name; Size = $file.Length } # O(N^2)
}
```

### High-Performance Solutions
```powershell
# SOLUTION 1: Direct Pipeline Streaming (Memory O(1), Time O(N))
Get-ChildItem -Path C:\Logs -Recurse | ForEach-Object {
    [PSCustomObject]@{ File = $_.Name; Size = $_.Length }
}

# SOLUTION 2: Foreach Loop Assignment (Memory O(N), Time O(N))
$items = foreach ($file in (Get-ChildItem -Path C:\Logs -Recurse)) {
    [PSCustomObject]@{ File = $file.Name; Size = $file.Length }
}

# SOLUTION 3: Strongly-Typed Generic List (Fastest mutable in-memory accumulation)
$items = [System.Collections.Generic.List[PSCustomObject]]::new()
foreach ($file in (Get-ChildItem -Path C:\Logs -Recurse)) {
    $items.Add([PSCustomObject]@{ File = $file.Name; Size = $file.Length })
}
```

---

## 4. Parameter Splatting (`@params`)

Splatting allows passing a dictionary of parameters to a cmdlet or function, eliminating unwieldy single-line commands and improving readability:

```powershell
$invokeParams = @{
    Uri             = 'https://api.github.com/repos/owner/repo/issues'
    Method          = 'Post'
    Headers         = @{
        Authorization = "Bearer $token"
        Accept        = 'application/vnd.github.v3+json'
    }
    Body            = ($payload | ConvertTo-Json -Depth 5)
    ContentType     = 'application/json'
    TimeoutSec      = 30
    ErrorAction     = 'Stop'
}

# Use @ instead of $ when calling the cmdlet
$response = Invoke-RestMethod @invokeParams
```

Splatting also supports arrays for positional parameters:
```powershell
$copyParams = @('C:\Source\data.csv', 'D:\Backup\data.csv', $true)
Copy-Item @copyParams # Binds to -Path, -Destination, -Force
```
