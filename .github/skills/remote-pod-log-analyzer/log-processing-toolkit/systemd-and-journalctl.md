# Host Logging: Systemd Journal & Kernel Dmesg

Audit and diagnostic guide for Linux systemd services, container runtime daemons, and kernel events.

---

## 1. Systemd Journal Filtering (`journalctl`)

When pods fail due to host-level issues (Kubelet node pressure, Containerd failures, Docker daemon timeouts):

```bash
# Query logs for a specific systemd unit (Kubelet or Containerd)
journalctl -u kubelet --since "30 minutes ago" --no-pager

# Filter by syslog priority level (err, crit, alert, emerg)
journalctl -u containerd -p err..emerg --since "1 hour ago" --no-pager

# Follow logs in real-time
journalctl -u kubelet -f

# Output as JSON for automated parsing with jq
journalctl -u kubelet -p err --since "10 minutes ago" -o json | \
    jq -r '._SOURCE_REALTIME_TIMESTAMP, .MESSAGE'
```

---

## 2. Kernel Ring Buffer (`dmesg`) for OOM & Hardware Faults

When containers die with exit code 137 (`OOMKilled`) or processes disappear without application logs, the Linux kernel OOM-killer killed the process:

```bash
# Human-readable timestamps (-T) for kernel OOM killer events
dmesg -T | grep -iE 'killed process|oom-killer|out of memory'

# Inspect memory stats at time of OOM kill
dmesg -T | grep -A 10 -B 5 'oom_reaper: reaped process'

# Check for segmentation faults (SIGSEGV)
dmesg -T | grep -i 'segfault'

# Check for disk I/O errors or filesystem corruption
dmesg -T | grep -iE 'I/O error|EXT4-fs error|XFS error'
```

---

## 3. Node Resource Pressure Indicators

```bash
# Check memory, swap, and disk pressure
free -h
df -hT /var/log /var/lib/containerd

# Check top memory-consuming processes on the host
ps aux --sort=-%mem | head -n 10
```

