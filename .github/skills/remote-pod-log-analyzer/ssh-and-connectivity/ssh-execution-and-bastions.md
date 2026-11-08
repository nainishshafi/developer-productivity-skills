# Remote SSH Execution, Bastions & Non-Interactive Pipelines

Staff-level guide to executing fast, reliable, and secure log extraction commands over SSH.

---

## 1. Non-Interactive SSH Flag Discipline

When executing remote commands from scripts or agents, SSH must never hang waiting for passwords, host key confirmations, or interactive prompts.

### Standard Production SSH Flags
```bash
ssh -o BatchMode=yes \
    -o ConnectTimeout=5 \
    -o StrictHostKeyChecking=accept-new \
    -o ServerAliveInterval=15 \
    -o ServerAliveCountMax=3 \
    -T user@remote-host "command"
```

| Flag | Purpose |
|---|---|
| `-o BatchMode=yes` | Disables password and passphrase prompting. Fails fast (`exit 255`) if SSH key auth fails. |
| `-o ConnectTimeout=5` | Times out TCP handshake in 5 seconds instead of hanging for minutes. |
| `-o StrictHostKeyChecking=accept-new` | Automatically accepts new host keys without interactive `(yes/no)` prompt. |
| `-T` | Disables pseudo-terminal allocation (prevents carriage return `\r\n` mangling and raw ANSI control codes). |
| `-t` (Alternative) | Forces pseudo-terminal allocation; use **only** when remote command requires a TTY (e.g. `sudo`). |
| `-q` | Quiet mode (suppresses warning banners and motd messages). |

---

## 2. Bastion / Jump Host Hopping (`-J`)

In enterprise cloud topologies (AWS private VPCs, GCP private GKE clusters, Azure private subnets), Kubernetes nodes and Linux hosts are behind a Bastion / Jump Box:

```bash
# Jump through single bastion
ssh -o BatchMode=yes -J bastion-user@bastion.corp.net:22 app-user@10.0.4.15 "grep 'FATAL' /var/log/app.log"

# Multi-hop jump (Public Bastion -> Internal DMZ -> Private Node)
ssh -J user@bastion-ext.corp.com,user@bastion-int.corp.com user@10.200.1.42 "hostname"
```

### SSH Config Profile (`~/.ssh/config`)
```ssh-config
Host bastion-prod
    HostName bastion.corp.net
    User ops-admin
    IdentityFile ~/.ssh/id_ed25519

Host k8s-node-*
    User ubuntu
    ProxyJump bastion-prod
    IdentityFile ~/.ssh/k8s_node_key
    StrictHostKeyChecking accept-new
```

---

## 3. Remote Execution without Transferring Big Files

**Cardinal Rule**: Never download multi-gigabyte log files over SSH just to search them locally.
- Run `grep`, `awk`, `sed`, or `jq` **on the remote host**, streaming only the filtered output across the network:

```bash
# BAD: Transfers 10 GB file over network
scp user@remote:/var/log/app/huge.log ./
grep "Exception" huge.log

# GOOD: Remote executes search, transfers only matching lines (10 KB)
ssh -T user@remote "grep -E 'ERROR|FATAL' /var/log/app/huge.log" > local-errors.txt
```

---

## 4. Multi-Line Remote Scripts via Heredoc

Execute complex multi-step pipelines remotely without quoting escape hell:

```bash
ssh -T user@remote-host bash -s << 'EOF'
set -euo pipefail

echo "=== System OOM Events ==="
dmesg -T | grep -iE 'killed process|oom-killer|out of memory' | tail -n 10 || true

echo "=== Container Disk Usage ==="
df -h /var/log /var/lib/docker || true

echo "=== Top 5 Error Signatures in Last Hour ==="
journalctl -u kubelet --since "1 hour ago" -p err..alert --no-pager | \
    awk '{for(i=5;i<=NF;i++) printf "%s ", $i; print ""}' | \
    sort | uniq -c | sort -rn | head -n 5
EOF
```
*Note: Quoting `'EOF'` ensures variables (`$i`, `$NF`) are evaluated on the **remote server**, not locally.*

