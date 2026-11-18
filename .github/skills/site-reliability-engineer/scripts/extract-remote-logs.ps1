<#
.SYNOPSIS
    Automated extraction and filtering of error/troubleshooting logs from Kubernetes pods and remote Linux hosts.
.DESCRIPTION
    Staging & In-Situ Execution Protocol:
    1. Copies 'remote-collector.sh' to remote host or pod in '/tmp' via SCP or 'kubectl cp'
    2. Executes the collector locally in '/tmp' to process logs without network latency
    3. Copies the resulting archive '/tmp/log-bundle-<timestamp>.tar.gz' back to local OutputDir
    4. Automatically cleans up temporary files in remote '/tmp'
    5. Falls back to 'kubectl logs' streaming if container lacks shell or cp support.
.PARAMETER TargetType
    Target source type: 'Pod' or 'LinuxHost'.
.PARAMETER PodName
    Name of target Kubernetes pod (for TargetType 'Pod').
.PARAMETER Namespace
    Kubernetes namespace (default: 'default').
.PARAMETER Container
    Specific container in multi-container pod.
.PARAMETER LabelSelector
    Kubernetes label selector (e.g. 'app=payment-service').
.PARAMETER ExtractPrevious
    Switch to extract previous crashed container instance (CrashLoopBackOff).
.PARAMETER RemoteHost
    Remote Linux server hostname or IP address (for TargetType 'LinuxHost').
.PARAMETER User
    SSH user for remote host.
.PARAMETER Bastion
    Optional SSH jump bastion (e.g. 'jumpuser@bastion.corp.net').
.PARAMETER IdentityFile
    Path to private SSH key.
.PARAMETER LogPath
    Remote log file path on Linux host.
.PARAMETER SystemdUnit
    Remote systemd service to query via journalctl (e.g. 'kubelet').
.PARAMETER Since
    Time window to extract (default: '1h').
.PARAMETER OutputDir
    Local destination folder for extracted logs (default: './extracted-logs').
.EXAMPLE
    ./extract-remote-logs.ps1 -TargetType LinuxHost -RemoteHost 10.0.4.15 -User ubuntu -SystemdUnit kubelet -Since "1h"
.EXAMPLE
    ./extract-remote-logs.ps1 -TargetType Pod -Namespace prod -PodName order-service-xyz -ExtractPrevious
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet('Pod', 'LinuxHost')]
    [string]$TargetType,

    # Kubernetes Parameters
    [Parameter()]
    [string]$PodName,

    [Parameter()]
    [string]$Namespace = 'default',

    [Parameter()]
    [string]$Container,

    [Parameter()]
    [string]$LabelSelector,

    [Parameter()]
    [switch]$ExtractPrevious,

    # SSH / Linux Host Parameters
    [Parameter()]
    [string]$RemoteHost,

    [Parameter()]
    [string]$User,

    [Parameter()]
    [string]$Bastion,

    [Parameter()]
    [string]$IdentityFile,

    [Parameter()]
    [string]$LogPath,

    [Parameter()]
    [string]$SystemdUnit,

    # Shared Parameters
    [Parameter()]
    [string]$Since = '1h',

    [Parameter()]
    [string]$OutputDir = './extracted-logs'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$collectorScript = Join-Path -Path $PSScriptRoot -ChildPath 'remote-collector.sh'
if (-not (Test-Path -Path $collectorScript)) {
    throw "Collector script not found at '$collectorScript'."
}

$timestamp = [System.DateTime]::UtcNow.ToString('yyyyMMdd_HHmmss\Z')
if (-not (Test-Path -Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host " Remote Staging & In-Situ Log Extraction ($TargetType)" -ForegroundColor Cyan
Write-Host " Output Directory: $OutputDir" -ForegroundColor Cyan
Write-Host " Timestamp (UTC) : $timestamp" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

if ($TargetType -eq 'LinuxHost') {
    if (-not $RemoteHost -or -not $User) {
        throw "Both -RemoteHost and -User are required for TargetType 'LinuxHost'."
    }

    $sshOpts = [System.Collections.Generic.List[string]]::new()
    $sshOpts.Add('-o'); $sshOpts.Add('BatchMode=yes')
    $sshOpts.Add('-o'); $sshOpts.Add('ConnectTimeout=5')
    $sshOpts.Add('-o'); $sshOpts.Add('StrictHostKeyChecking=accept-new')

    if ($Bastion) {
        $sshOpts.Add('-J'); $sshOpts.Add($Bastion)
    }
    if ($IdentityFile) {
        $sshOpts.Add('-i'); $sshOpts.Add($IdentityFile)
    }

    $remoteScript = "/tmp/remote-collector-${timestamp}.sh"

    # 1. Copy collector to remote /tmp
    Write-Host "[1/5] Copying collector script to ${User}@${RemoteHost}:${remoteScript}..." -ForegroundColor Yellow
    $scpArgs = $sshOpts.ToArray() + @($collectorScript, "${User}@${RemoteHost}:${remoteScript}")
    & scp @scpArgs

    # 2. Execute collector in-situ in /tmp
    Write-Host "[2/5] Executing collector remotely in /tmp..." -ForegroundColor Yellow
    $remoteCmd = "chmod +x '$remoteScript' && '$remoteScript' '$Since' '$LogPath' '$SystemdUnit'"
    $sshArgs = $sshOpts.ToArray() + @('-T', "${User}@${RemoteHost}", $remoteCmd)
    $execOutput = & ssh @sshArgs

    $execOutput | Out-Host

    $archiveLine = $execOutput | Select-String -Pattern 'READY_FOR_COPY:(.+)' | Select-Object -First 1
    if (-not $archiveLine) {
        Write-Error "Remote collector failed to produce archive."
        & ssh @($sshOpts.ToArray() + @('-T', "${User}@${RemoteHost}", "rm -f '$remoteScript'"))
        return
    }

    $remoteArchive = $archiveLine.Matches.Groups[1].Value.Trim()
    $archiveName = [System.IO.Path]::GetFileName($remoteArchive)
    $localArchive = Join-Path -Path $OutputDir -ChildPath $archiveName

    # 3. Copy archive back to local OutputDir
    Write-Host "[3/5] Copying bundle from remote to $localArchive..." -ForegroundColor Yellow
    $fetchArgs = $sshOpts.ToArray() + @("${User}@${RemoteHost}:${remoteArchive}", $localArchive)
    & scp @fetchArgs

    # 4. Clean up remote /tmp
    Write-Host "[4/5] Cleaning up remote /tmp artifacts..." -ForegroundColor Yellow
    $cleanupCmd = "rm -f '$remoteScript' '$remoteArchive'"
    $cleanArgs = $sshOpts.ToArray() + @('-T', "${User}@${RemoteHost}", $cleanupCmd)
    & ssh @cleanArgs

    # 5. Extract bundle locally
    Write-Host "[5/5] Unpacking bundle locally..." -ForegroundColor Green
    tar -xzf $localArchive -C $OutputDir

    $extractDir = Join-Path -Path $OutputDir -ChildPath ($archiveName -replace '\.tar\.gz$', '')
    $summaryFile = Join-Path -Path $extractDir -ChildPath 'summary.txt'
    if (Test-Path -Path $summaryFile) {
        Get-Content -Path $summaryFile | Out-Host
    }

    Write-Host "Done! Extracted files located at $extractDir" -ForegroundColor Cyan
}
elseif ($TargetType -eq 'Pod') {
    $targetPods = [System.Collections.Generic.List[string]]::new()
    if ($PodName) {
        $targetPods.Add($PodName)
    }
    elseif ($LabelSelector) {
        Write-Host "[*] Discovering pods matching label '$LabelSelector'..."
        $discovered = kubectl get pods -n $Namespace -l $LabelSelector -o jsonpath='{.items[*].metadata.name}'
        if ($discovered) {
            foreach ($p in ($discovered -split '\s+')) { if ($p) { $targetPods.Add($p) } }
        }
    }
    else {
        throw "Must provide either -PodName or -LabelSelector for TargetType 'Pod'."
    }

    foreach ($pod in $targetPods) {
        $remoteScript = "/tmp/pod-collector-${timestamp}.sh"
        $containerFlag = if ($Container) { @('-c', $Container) } else { @() }
        $stagedSuccess = $false

        Write-Host "[*] Processing pod: $pod..." -ForegroundColor Yellow

        # Attempt in-situ copy & exec
        try {
            Write-Host "    Attempting in-situ collection via 'kubectl cp' to /tmp..."
            $cpToArgs = @('cp', $collectorScript, "${Namespace}/${pod}:${remoteScript}") + $containerFlag
            & kubectl @cpToArgs 2>$null

            $execCmd = "chmod +x '$remoteScript' && '$remoteScript' '$Since'"
            $execArgs = @('exec', $pod, '-n', $Namespace) + $containerFlag + @('--', '/bin/sh', '-c', $execCmd)
            $execOutput = & kubectl @execArgs 2>$null

            $archiveLine = $execOutput | Select-String -Pattern 'READY_FOR_COPY:(.+)' | Select-Object -First 1
            if ($archiveLine) {
                $remoteArchive = $archiveLine.Matches.Groups[1].Value.Trim()
                $archiveName = "${pod}_" + [System.IO.Path]::GetFileName($remoteArchive)
                $localArchive = Join-Path -Path $OutputDir -ChildPath $archiveName

                Write-Host "    Copying bundle from ${pod}:${remoteArchive} to local..."
                $cpFromArgs = @('cp', "${Namespace}/${pod}:${remoteArchive}", $localArchive) + $containerFlag
                & kubectl @cpFromArgs 2>$null

                # Cleanup in pod
                $cleanArgs = @('exec', $pod, '-n', $Namespace) + $containerFlag + @('--', 'rm', '-f', $remoteScript, $remoteArchive)
                & kubectl @cleanArgs 2>$null

                tar -xzf $localArchive -C $OutputDir
                $stagedSuccess = $true
                Write-Host "    In-situ collection succeeded: $localArchive" -ForegroundColor Green
            }
        }
        catch {
            $stagedSuccess = $false
        }

        # Fallback to streaming if cp/exec not supported
        if (-not $stagedSuccess) {
            Write-Host "    Falling back to 'kubectl logs' stream for $pod..." -ForegroundColor Yellow
            $prefix = Join-Path -Path $OutputDir -ChildPath "${Namespace}_${pod}_${timestamp}"
            $logFile = "${prefix}.log"
            $errFile = "${prefix}_errors.log"

            $logArgs = @('logs', $pod, '-n', $Namespace, "--since=$Since", '--tail=5000', '--timestamps') + $containerFlag
            & kubectl @logArgs | Out-File -FilePath $logFile -Encoding utf8

            if (Test-Path -Path $logFile) {
                $errorLines = Select-String -Path $logFile -Pattern 'error|fatal|exception|panic|fail|killed' -Context 2, 2
                if ($errorLines) {
                    $errorLines | ForEach-Object {
                        $_.ToString() -replace 'Bearer [a-zA-Z0-9._-]+', 'Bearer [REDACTED]' `
                                      -replace '(password|secret|token)=[^ &]+', '$1=[REDACTED]'
                    } | Out-File -FilePath $errFile -Encoding utf8
                }
            }

            if ($ExtractPrevious) {
                $prevFile = "${prefix}_previous_crash.log"
                $prevArgs = @('logs', $pod, '-n', $Namespace, '--previous', '--tail=5000', '--timestamps') + $containerFlag
                try {
                    & kubectl @prevArgs 2>$null | Out-File -FilePath $prevFile -Encoding utf8
                }
                catch { }
            }
        }
    }
}

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host " Extraction Complete. Artifacts saved in $OutputDir" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
