<#
.SYNOPSIS
    Automated extraction and filtering of error/troubleshooting logs from Kubernetes pods and remote Linux hosts.
.DESCRIPTION
    Extracts live, historical, and previous crashed container logs via kubectl, or queries remote Linux hosts via SSH.
    Filters error signatures, calculates frequency summaries, and writes sanitized artifacts to a local directory.
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
    ./extract-remote-logs.ps1 -TargetType Pod -Namespace prod -PodName order-service-7b4f-x8k9 -ExtractPrevious
.EXAMPLE
    ./extract-remote-logs.ps1 -TargetType LinuxHost -RemoteHost 10.0.4.15 -User ubuntu -SystemdUnit kubelet -Since "2h"
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

$timestamp = [System.DateTime]::UtcNow.ToString('yyyyMMdd_HHmmss\Z')
if (-not (Test-Path -Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host " Remote Log Extraction Started ($TargetType Mode)" -ForegroundColor Cyan
Write-Host " Output Directory: $OutputDir" -ForegroundColor Cyan
Write-Host " Timestamp (UTC) : $timestamp" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

if ($TargetType -eq 'Pod') {
    $targetPods = [System.Collections.Generic.List[string]]::new()

    if ($PodName) {
        $targetPods.Add($PodName)
    }
    elseif ($LabelSelector) {
        Write-Host "[*] Discovering pods matching label '$LabelSelector'..."
        $discovered = kubectl get pods -n $Namespace -l $LabelSelector -o jsonpath='{.items[*].metadata.name}'
        if (-not $discovered) {
            throw "No pods found matching label '$LabelSelector' in namespace '$Namespace'."
        }
        foreach ($p in ($discovered -split '\s+')) {
            if ($p) { $targetPods.Add($p) }
        }
    }
    else {
        throw "Must provide either -PodName or -LabelSelector for TargetType 'Pod'."
    }

    foreach ($pod in $targetPods) {
        $prefix = Join-Path -Path $OutputDir -ChildPath "${Namespace}_${pod}_${timestamp}"
        $logFile = "${prefix}.log"
        $errFile = "${prefix}_errors.log"

        Write-Host "[*] Extracting logs for pod: $pod..." -ForegroundColor Yellow

        $containerArgs = if ($Container) { @('-c', $Container) } else { @() }
        $kubectlArgs = @('logs', $pod, '-n', $Namespace, "--since=$Since", '--tail=5000', '--timestamps') + $containerArgs

        & kubectl @kubectlArgs | Out-File -FilePath $logFile -Encoding utf8

        if (Test-Path -Path $logFile) {
            $lineCount = (Get-Content -Path $logFile | Measure-Object).Count
            Write-Host "    Saved $lineCount lines to $logFile" -ForegroundColor Green

            # Filter error lines
            $errorLines = Select-String -Path $logFile -Pattern 'error|fatal|exception|panic|fail|killed|timeout' -Context 2, 2
            if ($errorLines) {
                $errorLines | ForEach-Object {
                    $_.ToString() -replace 'Bearer [a-zA-Z0-9._-]+', 'Bearer [REDACTED]' `
                                  -replace '(password|secret|token)=[^ &]+', '$1=[REDACTED]'
                } | Out-File -FilePath $errFile -Encoding utf8

                $errCount = (Get-Content -Path $errFile | Measure-Object).Count
                Write-Host "    Extracted $errCount error lines to $errFile" -ForegroundColor Magenta
            }
        }

        # Check previous container if requested
        if ($ExtractPrevious) {
            $prevFile = "${prefix}_previous_crash.log"
            Write-Host "[*] Checking previous crashed container logs (--previous)..." -ForegroundColor Yellow
            $prevArgs = @('logs', $pod, '-n', $Namespace, '--previous', '--tail=5000', '--timestamps') + $containerArgs

            try {
                & kubectl @prevArgs 2>$null | Out-File -FilePath $prevFile -Encoding utf8
                if ((Get-Item -Path $prevFile).Length -gt 0) {
                    Write-Host "    [!] Found crashed container logs: $prevFile" -ForegroundColor Red
                }
                else {
                    Remove-Item -Path $prevFile -Force -ErrorAction SilentlyContinue
                }
            }
            catch {
                # No previous container instance
            }
        }
    }
}
elseif ($TargetType -eq 'LinuxHost') {
    if (-not $RemoteHost -or -not $User) {
        throw "Both -RemoteHost and -User are required for TargetType 'LinuxHost'."
    }

    $prefix = Join-Path -Path $OutputDir -ChildPath "${RemoteHost}_${timestamp}"
    $sshArgs = [System.Collections.Generic.List[string]]::new()
    $sshArgs.Add('-o')
    $sshArgs.Add('BatchMode=yes')
    $sshArgs.Add('-o')
    $sshArgs.Add('ConnectTimeout=5')
    $sshArgs.Add('-o')
    $sshArgs.Add('StrictHostKeyChecking=accept-new')
    $sshArgs.Add('-T')

    if ($Bastion) {
        $sshArgs.Add('-J')
        $sshArgs.Add($Bastion)
    }
    if ($IdentityFile) {
        $sshArgs.Add('-i')
        $sshArgs.Add($IdentityFile)
    }

    $sshArgs.Add("$User@$RemoteHost")

    # 1. Systemd extraction
    if ($SystemdUnit) {
        $journalFile = "${prefix}_journal_${SystemdUnit}.log"
        Write-Host "[*] Querying remote systemd unit '$SystemdUnit'..." -ForegroundColor Yellow
        $cmd = "journalctl -u '$SystemdUnit' --since '$Since' -p err..emerg --no-pager"
        $execArgs = $sshArgs.ToArray() + @($cmd)
        & ssh @execArgs | Out-File -FilePath $journalFile -Encoding utf8
        Write-Host "    Saved journal logs to $journalFile" -ForegroundColor Green
    }

    # 2. File extraction
    if ($LogPath) {
        $fileLog = "${prefix}_file.log"
        Write-Host "[*] Querying remote log path '$LogPath'..." -ForegroundColor Yellow
        $cmd = "zgrep -E -i -C 2 'error|fatal|exception|panic|fail' '$LogPath' | tail -n 5000"
        $execArgs = $sshArgs.ToArray() + @($cmd)
        & ssh @execArgs | Out-File -FilePath $fileLog -Encoding utf8
        Write-Host "    Saved remote file errors to $fileLog" -ForegroundColor Green
    }

    # 3. Kernel OOM inspection
    $dmesgFile = "${prefix}_dmesg_oom.log"
    Write-Host "[*] Checking remote kernel for OOM killer events..." -ForegroundColor Yellow
    $dmesgCmd = "dmesg -T | grep -iE 'killed process|oom-killer|out of memory' | tail -n 50"
    $execArgs = $sshArgs.ToArray() + @($dmesgCmd)
    & ssh @execArgs | Out-File -FilePath $dmesgFile -Encoding utf8
    if ((Get-Item -Path $dmesgFile).Length -gt 0) {
        Write-Host "    [!] Found kernel OOM events: $dmesgFile" -ForegroundColor Red
    }
    else {
        Remove-Item -Path $dmesgFile -Force -ErrorAction SilentlyContinue
    }
}

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host " Extraction Complete. Artifacts saved in $OutputDir" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

