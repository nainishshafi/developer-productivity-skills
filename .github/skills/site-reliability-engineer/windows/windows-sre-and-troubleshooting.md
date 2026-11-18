# Windows Server SRE & Production Troubleshooting

Use **read-only PowerShell (`Get-*`)** and Sysinternals/ETW diagnostics before restarting services or recycling app pools.

## 1. 60-Second Windows Triage (PowerShell)

```powershell
# System uptime & pending reboot indicators
Get-CimInstance Win32_OperatingSystem | Select-Object CSName, LastBootUpTime, FreePhysicalMemory, TotalVisibleMemorySize

# Top CPU and memory-consuming processes
Get-Process | Sort-Object CPU -Descending | Select-Object -First 15 Name, Id, CPU, @{N='WS_MB';E={[math]::Round($_.WS/1MB,1)}}, Handles, Threads

# Disk space across local fixed volumes
Get-CimInstance Win32_LogicalDisk -Filter "DriveType=3" | Select-Object DeviceID, @{N='FreeGB';E={[math]::Round($_.FreeSpace/1GB,2)}}, @{N='SizeGB';E={[math]::Round($_.Size/1GB,2)}}

# Critical/Error events in System & Application logs (last 60 min)
$since = (Get-Date).AddHours(-1)
Get-WinEvent -FilterHashtable @{LogName='System','Application'; Level=1,2; StartTime=$since} -MaxEvents 50 |
  Select-Object TimeCreated, LogName, ProviderName, Id, Message
```

---

## 2. Services, Crash Dumps & Hang Analysis

- **Service Crash / Unexpected Stop:**
  - Filter Service Control Manager errors: `Event ID 7031` (unexpected termination), `7034` (crashed), `7000`/`7009` (startup timeout).
  - Check Application log for `.NET Runtime` (`Event ID 1026`) or `Application Error` (`Event ID 1000` — faulting module + exception code `0xc0000005` AV, `0xe0434352` CLR exception).
- **Non-Destructive Dump Capture Before Restart:**
  - **Sysinternals `procdump`:**
    ```powershell
    procdump -ma <PID> C:\dumps\hang.dmp          # Full memory dump of hung process
    procdump -ma -e 1 -f "" <PID> C:\dumps\       # Dump on unhandled exception
    ```
  - **.NET 6/8+ (`dotnet-dump` / `dotnet-counters`):**
    ```powershell
    dotnet-counters monitor -p <PID> --counters System.Runtime,Microsoft.AspNetCore.Hosting
    dotnet-dump collect -p <PID> -o C:\dumps\app.dmp
    ```

---

## 3. Performance Counters & Kernel Memory / Handle Leaks

```powershell
# Sample CPU, Memory, Disk Queue, and TCPv4 connections
Get-Counter @(
  '\Processor(_Total)\% Processor Time',
  '\Memory\Available MBytes',
  '\Memory\Pool Nonpaged Bytes',
  '\LogicalDisk(*)\Avg. Disk Queue Length',
  '\TCPv4\Connections Established'
) -SampleInterval 1 -MaxSamples 5
```

- **Nonpaged Pool Exhaustion:** If `\Memory\Pool Nonpaged Bytes` climbs continuously, inspect driver tags with `poolmon.exe` (Windows Driver Kit).
- **Handle / Thread Leaks:** Watch `Handles` and `Threads` per process; `.NET` threadpool starvation shows rapid `Threads` growth with low CPU and rising request latency.
- **Ephemeral Port Exhaustion (`WSAENOBUFS` / `10055`):**
  ```powershell
  netsh int ipv4 show dynamicport tcp
  Get-NetTCPConnection | Group-Object State | Select-Object Name, Count
  ```

---

## 4. IIS, HTTP.sys & WinRM Remote Triage

- **IIS / HTTP.sys Queue Saturation:**
  - Check `C:\Windows\System32\LogFiles\HTTPERR\` for `QueueFull` (HTTP `503`), `Connection_Abandoned_By_ReqQueue`, or `Timer_EntityBody`.
  - Inspect worker processes and active requests:
    ```powershell
    Import-Module WebAdministration
    Get-WebAppPoolState
    Get-ChildItem IIS:\AppPools | ForEach-Object { [PSCustomObject]@{ Name=$_.Name; State=$_.State; QueueLength=$_.queueLength } }
    ```
- **Remote Triage (WinRM / PowerShell Remoting):**
  ```powershell
  Invoke-Command -ComputerName <host> -ScriptBlock {
    Get-WinEvent -FilterHashtable @{LogName='System'; Level=1,2; StartTime=(Get-Date).AddMinutes(-30)} -MaxEvents 20
  }
  ```
