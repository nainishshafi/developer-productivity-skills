# Linux SRE & Production Troubleshooting

Apply the **USE Method** (Utilization, Saturation, Errors) for every subsystem using **non-destructive, read-only commands** first.

## 1. 60-Second First-Response Checklist

```bash
uptime                         # Load averages (1m, 5m, 15m) vs CPU count (nproc)
dmesg -T | tail -n 30          # Kernel OOM-killer, hardware, or filesystem errors
vmstat 1 5                     # CPU run-queue (r), blocked I/O (b), swap (si/so), steal (st)
mpstat -P ALL 1 3              # Per-core %usr, %sys, %iowait, %soft, %steal
pidstat 1 3                    # Top CPU/I/O-consuming processes per second
free -h                        # Available memory vs buffers/cache (never panic on low 'free')
df -h && df -i                 # Filesystem space AND inode exhaustion
ss -s                          # Socket summary (TIME_WAIT, SYN-RECV, orphaned sockets)
```

---

## 2. Systemd & Journalctl Diagnostics

```bash
systemctl --failed                              # List failed units
systemctl status <service> --no-pager -l        # Unit state, exit code, MainPID, cgroup memory
journalctl -u <service> -p err --since "1h ago" --no-pager
journalctl -k --since "30 min ago"              # Kernel ring buffer via journald
```

- **Exit Code `137` (`SIGKILL`):** Usually cgroup/kernel OOM killer (`oom_kill_event` in `dmesg -T` or `MemoryCurrent` hitting `MemoryMax`).
- **Exit Code `143` (`SIGTERM`):** Graceful stop / orchestrator eviction / timeout.

---

## 3. CPU, Memory & OOM Triage

- **Load Average > `nproc`:** Check `vmstat 1 5`:
  - High `r` (runnable threads) + high `%usr`/`%sys` $\to$ CPU saturation. Profile with `perf top` or language profiler.
  - High `b` (uninterruptible sleep `D` state) + high `%iowait` $\to$ Disk/NFS/storage stall (`iostat -xz 1`).
  - High `%steal` (`st`) $\to$ Hypervisor noisy-neighbor throttling on cloud VM.
- **Memory & OOM:**
  - Check `cat /proc/meminfo` (`MemAvailable`, `Slab`, `SUnreclaim`, `Dirty`, `PageTables`).
  - Check cgroup v2 limits (containers/systemd): `cat /sys/fs/cgroup/memory.current` vs `/sys/fs/cgroup/memory.max` and `/sys/fs/cgroup/memory.events`.
  - Inspect per-process RSS/PSS: `ps aux --sort=-%mem | head -n 15`.

---

## 4. Disk, Filesystem & Deleted-Open-File Leaks

- **Disk full (`df -h` = 100%) but `du -sh` disagrees:** A process is holding an open file descriptor to a deleted file. Find and release it without rebooting:
  ```bash
  lsof +L1                       # Show unlinked files still held open by PIDs
  ```
  *Safe remediation:* Reload/gracefully restart the owning service or truncate `/proc/<pid>/fd/<fd>` only if safe for that log file.
- **Inode exhaustion (`df -i` = 100%):** Millions of small files (sessions, tmp, mail spool) prevent creating new files even with free GBs.
- **Block I/O saturation:** `iostat -xz 1 5` — watch `await` (latency ms), `aqu-sz` (queue depth), and `%util` (near 100% on single-queue devices).

---

## 5. Network & Socket Triage

```bash
ss -tulnp                                    # Listening ports & owning processes
ss -tan state syn-recv | wc -l               # SYN backlog saturation
ss -tan state time-wait | wc -l              # Ephemeral port pressure
cat /proc/sys/net/ipv4/ip_local_port_range   # Available ephemeral ports
conntrack -S 2>/dev/null || true             # Netfilter conntrack drops/table full
```

- **Connection refused vs Timeout:** `ECONNREFUSED` = service not listening or local port closed; timeout = firewall/NSG drop, routing blackhole, or `tcp_max_syn_backlog` / `somaxconn` overflow (`netstat -s | grep -iE "listen|drop|overflow"`).
- **Packet capture (read-only, bounded count):** `tcpdump -ni any -c 200 host <ip> and port <port>`.

---

## 6. eBPF Zero-Code Kernel & Network Observability

When standard metrics miss kernel-level stalls or legacy binaries cannot be re-instrumented:
- **TCP Retransmissions & Latency (`bpftrace` / BCC):** Trace `tcp_retransmit_skb` or `biolatency` in real time without app restarts or sidecar overhead.
- **Zero-Code RED Telemetry:** Use OpenTelemetry eBPF auto-instrumentation to capture HTTP/gRPC request rates, errors, and tail latency directly from kernel socket/TLS probes.
