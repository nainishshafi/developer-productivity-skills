# PowerShell Concurrency, Parallelism & Asynchronous Jobs

Guide to multi-threading, parallel pipelines, and asynchronous automation in PowerShell 7+ and Windows PowerShell 5.1.

---

## 1. Concurrency Model Comparison

| Mechanism | Version | Overhead | Best Used For |
|---|---|---|---|
| `ForEach-Object -Parallel` | PS 7.0+ | Very Low (Threads) | Parallel batch processing, I/O waits, concurrent API queries. |
| `Start-ThreadJob` | PS 5.1+ (ThreadJob module) | Low (Threads) | Asynchronous background tasks within the same process. |
| `Start-Job` | All | High (New `pwsh`/`powershell` process per job) | Complete isolation where crashing must not impact the host. |
| `RunspacePool` | All | Extremely Low (Native .NET runspaces) | High-scale, low-latency concurrent processing (1,000+ tasks). |

---

## 2. `ForEach-Object -Parallel` (PowerShell 7+)

The most modern and idiomatic parallel construct in PowerShell:

```powershell
$servers = @('srv-app01', 'srv-app02', 'srv-app03', 'srv-db01', 'srv-db02')
$targetPort = 443

$results = $servers | ForEach-Object -Parallel -ThrottleLimit 10 {
    # Variables from the outer scope must use the $using: prefix
    $port = $using:targetPort
    $server = $_

    $testResult = Test-NetConnection -ComputerName $server -Port $port -WarningAction SilentlyContinue

    [PSCustomObject]@{
        Server       = $server
        Port         = $port
        IsOpen       = $testResult.TcpTestSucceeded
        ResponseTime = $testResult.PingReplyDetails.RoundtripTime
        TimestampUtc = [System.DateTime]::UtcNow
    }
}

$results | Format-Table -AutoSize
```

### Key Rules for `-Parallel`:
1. **Scope Access**: Variables defined in the parent script must be referenced with `$using:variableName`.
2. **Throttle Limit**: Always set `-ThrottleLimit` (default is 5). Tune based on network or CPU constraints (e.g. 10–30 for I/O; equal to CPU cores for compute).
3. **No Thread-Unsafe Mutations**: Never mutate a shared hashtable or list directly from inside parallel blocks without a thread-safe wrapper.

---

## 3. Thread-Safe Shared State

When multiple parallel threads must append to a shared collection, use synchronized or concurrent collections:

```powershell
# Thread-safe hashtable
$sharedMap = [hashtable]::Synchronized(@{})

# Thread-safe concurrent queue (System.Collections.Concurrent)
$queue = [System.Collections.Concurrent.ConcurrentBag[object]]::new()

1..100 | ForEach-Object -Parallel {
    $bag = $using:queue
    $bag.Add("Item-$_ processed by Thread $([System.Threading.Thread]::CurrentThread.ManagedThreadId)")
}
```

---

## 4. `Start-ThreadJob` (Cross-Version Threading)

For Windows PowerShell 5.1 compatibility or fire-and-forget background tasks:

```powershell
# Start a lightweight thread job
$job = Start-ThreadJob -ScriptBlock {
    param($Url)
    Invoke-RestMethod -Uri $Url -TimeoutSec 30
} -ArgumentList 'https://api.github.com/zen'

# Wait and receive output
$result = $job | Wait-Job -Timeout 10 | Receive-Job
$job | Remove-Job
```

---

## 5. Low-Latency Runspace Pools (.NET Native)

For high-throughput tooling requiring maximum execution speed without job overhead:

```powershell
$pool = [runspacefactory]::CreateRunspacePool(1, [System.Environment]::ProcessorCount)
$pool.Open()

$tasks = [System.Collections.Generic.List[PSCustomObject]]::new()

foreach ($item in 1..20) {
    $powershell = [powershell]::Create()
    $powershell.RunspacePool = $pool
    [void]$powershell.AddScript({
        param($n)
        [System.Threading.Thread]::Sleep(100)
        return "Result for $n on thread $([System.Threading.Thread]::CurrentThread.ManagedThreadId)"
    }).AddArgument($item)

    $asyncResult = $powershell.BeginInvoke()
    $tasks.Add([PSCustomObject]@{
        PowerShell  = $powershell
        AsyncResult = $asyncResult
    })
}

# Collect all results
$completedResults = foreach ($task in $tasks) {
    $task.PowerShell.EndInvoke($task.AsyncResult)
    $task.PowerShell.Dispose()
}

$pool.Close()
$pool.Dispose()
```

