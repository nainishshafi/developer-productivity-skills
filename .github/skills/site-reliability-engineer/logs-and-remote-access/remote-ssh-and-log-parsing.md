# OS-Specific Log Formats & Cloud Remote Access

> For generic SSH/bastion flags (`BatchMode=yes`, `-J`), see [ssh-execution-and-bastions.md](../ssh-and-connectivity/ssh-execution-and-bastions.md).
> For `awk`, `grep`/`zgrep`, `jq`, and `journalctl` stream recipes, see `log-processing-toolkit/`.

## 1. Cloud VM & Windows Remote Access

```bash
# Azure Bastion & Run-Command (for private VMs/virtual appliances without public SSH)
az network bastion ssh --name <bastion> --resource-group <rg> --target-resource-id <vm-id> --auth-type AAD
az vm run-command invoke -g <rg> -n <vm-name> --command-id RunShellScript --scripts "systemctl status <svc> --no-pager"
```

```powershell
# Windows Remote Triage (WinRM / PowerShell Remoting)
Invoke-Command -ComputerName <win-host> -ScriptBlock {
  Get-WinEvent -FilterHashtable @{LogName='Application'; Level=1,2; StartTime=(Get-Date).AddMinutes(-30)} -MaxEvents 30
}
```

---

## 2. Linux Auth, Syslog & Audit Logs

| Log Path | Purpose | Quick Triage Command |
|---|---|---|
| `/var/log/syslog` or `/var/log/messages` | Kernel, systemd, daemon errors | `grep -iE "oom|kill|segfault|i/o error|readonly" /var/log/syslog \| tail -n 40` |
| `/var/log/auth.log` or `/var/log/secure` | SSH logins, sudo, PAM failures | `grep -E "Failed password|Invalid user|sudo:" /var/log/auth.log \| tail -n 40` |
| `/var/log/audit/audit.log` | SELinux / AppArmor / syscall denials | `ausearch -m AVC,USER_AVC -ts recent` |

---

## 3. Windows IIS W3C, `HTTPERR` & Offline `.evtx` Logs

```powershell
# 1. Parse IIS W3C logs (skip # header comments, filter HTTP 5xx)
Get-Content C:\inetpub\logs\LogFiles\W3SVC1\u_ex*.log |
  Where-Object { $_ -notmatch '^#' } |
  Select-String '\s(50[0-9])\s' |
  Select-Object -Last 30

# 2. Check HTTP.sys kernel-level drops (QueueFull / 503)
Select-String -Path C:\Windows\System32\LogFiles\HTTPERR\httperr*.log -Pattern "QueueFull|Connection_Abandoned|Timer_" |
  Select-Object -Last 30

# 3. Parse exported offline .evtx file
Get-WinEvent -FilterHashtable @{Path='C:\dumps\system.evtx'; Level=1,2} -MaxEvents 50 |
  Select-Object TimeCreated, ProviderName, Id, Message
```
