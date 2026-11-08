# Fast Searching: Grep, Ripgrep & Compressed Logs

Staff-level guide to high-throughput log filtering across raw and rotated `.gz` log files.

---

## 1. High-Performance `grep` Flags

```bash
# Extended regex search with case-insensitivity
grep -E -i 'error|fatal|exception|panic' /var/log/app.log

# Contextual inspection (crucial for capturing stack traces)
# -B 3 (3 lines before), -A 10 (10 lines after)
grep -B 3 -A 10 'NullPointerException' /var/log/app.log

# Count matching occurrences across files
grep -c '500 Internal Server Error' /var/log/nginx/access.log*

# Inverse match (filter out noisy health checks or heartbeats)
grep -E 'ERROR' /var/log/app.log | grep -v 'kube-probe' | grep -v 'healthcheck'

# Extract only the matched regex token (useful for IDs/IPs)
grep -oP 'client_ip:\K[0-9.]+' /var/log/app.log | sort | uniq -c | sort -rn
```

---

## 2. Searching Rotated Compressed Logs (`.gz`)

Enterprise systems rotate active logs into gzipped archives (e.g. `app.log.1.gz`, `app-2026-11-07.gz`):
- **Never decompress `.gz` files onto the disk**! You will exhaust node disk space and trigger node eviction.
- Use **`zgrep`** or **`zcat`** to decompress in-memory stream:

```bash
# Search across both active uncompressed and rotated compressed logs
zgrep -E 'Connection refused|TimeoutException' /var/log/app/app.log* | tail -n 200

# Stream specific compressed log through grep/awk without saving to disk
zcat /var/log/nginx/access.log.2.gz | awk '$9 >= 500 { print $0 }' | head -n 50

# Multiple gzipped files searching with filenames (-H) and line numbers (-n)
zgrep -Hn 'Out of Memory' /var/log/pods/*/*/*.log.gz
```

---

## 3. Ultra-Fast Multi-Core Scanning with `ripgrep` (`rg`)

When `ripgrep` is installed on the remote host, use it instead of `grep`. `rg` utilizes Rust regex, SIMD acceleration, and multi-threaded parallel directory walking:

```bash
# Search compressed files automatically (-z) across all subdirectories
rg -z -i 'database deadlocked' /var/log/

# Search with context lines (-C 5) and suppress binary files
rg -C 5 'panic: runtime error' /var/log/pods/

# Match specific log timestamp interval
rg '2026-11-08T1[0-2]:' /var/log/app.log | rg 'ERROR'
```

---

## 4. Time-Window Log Slicing

Extract lines between two exact timestamps without scanning the entire file:

```bash
# Using sed to slice between timestamp boundaries
sed -n '/2026-11-08 10:15:00/,/2026-11-08 10:30:00/p' /var/log/app.log | grep 'ERROR'

# Using awk for ISO-8601 timestamps
awk '$1 >= "2026-11-08T10:15:00" && $1 <= "2026-11-08T10:30:00"' /var/log/app.log
```
