#!/usr/bin/env bash
# remote-collector.sh — Standalone diagnostic collector that runs in /tmp on remote Linux host or container
# This script executes LOCALLY on the target host/pod to process logs in-situ without network latency.
# Produces /tmp/log-bundle-<timestamp>.tar.gz containing sanitized error logs and summary.

set -euo pipefail

SINCE="${1:-1h}"
LOG_PATH="${2:-}"
SYSTEMD_UNIT="${3:-}"

WORKDIR="/tmp"
TIMESTAMP=$(date -u +"%Y%m%d_%H%M%SZ")
BUNDLE_NAME="log-bundle-${TIMESTAMP}"
TARGET_DIR="${WORKDIR}/${BUNDLE_NAME}"

mkdir -p "$TARGET_DIR"

echo "=== Remote Diagnostic Collection Started in $TARGET_DIR ==="
echo "Timestamp (UTC) : $TIMESTAMP"
echo "Time Window     : Since $SINCE"

# 1. Systemd journal extraction if systemd is available
if command -v journalctl >/dev/null 2>&1; then
    if [[ -n "$SYSTEMD_UNIT" ]]; then
        echo "[*] Collecting systemd unit: $SYSTEMD_UNIT..."
        journalctl -u "$SYSTEMD_UNIT" --since "$SINCE" -p err..emerg --no-pager > "${TARGET_DIR}/journal_${SYSTEMD_UNIT}.log" 2>&1 || true
    else
        echo "[*] Collecting systemd priority errors across all units..."
        journalctl --since "$SINCE" -p err..emerg --no-pager > "${TARGET_DIR}/journal_system_errors.log" 2>&1 || true
    fi
fi

# 2. Kernel dmesg OOM and hardware fault extraction
if command -v dmesg >/dev/null 2>&1; then
    echo "[*] Collecting kernel dmesg OOM & fault events..."
    dmesg -T 2>/dev/null | grep -iE 'killed process|oom-killer|out of memory|segfault|I/O error' | tail -n 100 > "${TARGET_DIR}/dmesg_faults.log" || true
    if [ ! -s "${TARGET_DIR}/dmesg_faults.log" ]; then
        rm -f "${TARGET_DIR}/dmesg_faults.log"
    fi
fi

# 3. Remote file log extraction if specified
if [[ -n "$LOG_PATH" && -e "$LOG_PATH" ]]; then
    echo "[*] Scanning remote log file: $LOG_PATH..."
    OUT_FILE="${TARGET_DIR}/app_errors.log"
    if [[ "$LOG_PATH" == *.gz ]]; then
        zgrep -E -i -C 2 'error|fatal|exception|panic|fail|killed|timeout' "$LOG_PATH" | tail -n 5000 > "$OUT_FILE" 2>&1 || true
    elif [ -f "$LOG_PATH" ]; then
        grep -E -i -C 2 'error|fatal|exception|panic|fail|killed|timeout' "$LOG_PATH" | tail -n 5000 > "$OUT_FILE" 2>&1 || true
    fi
fi

# 4. Container runtime logs if on container host (/var/log/pods/)
if [ -d "/var/log/pods" ]; then
    echo "[*] Scanning node /var/log/pods/ for recent errors..."
    find /var/log/pods -name "*.log" -mmin -60 -type f 2>/dev/null | head -n 30 | while read -r podlog; do
        POD_ERRS=$(grep -E -i 'error|fatal|exception|panic' "$podlog" | tail -n 50 || true)
        if [ -n "$POD_ERRS" ]; then
            SAFE_NAME=$(echo "$podlog" | tr '/' '_')
            echo "$POD_ERRS" > "${TARGET_DIR}/pod${SAFE_NAME}.log"
        fi
    done
fi

# 5. Scrub sensitive tokens (Bearer tokens, passwords) across all extracted logs
echo "[*] Scrubbing sensitive tokens and secrets from extracted files..."
find "$TARGET_DIR" -type f -name "*.log" | while read -r f; do
    sed -i -E 's/Bearer [a-zA-Z0-9._-]+/Bearer [REDACTED]/g; s/(password|secret|token)=[^ &]+/\1=[REDACTED]/g; s/[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{4}/[CARD_REDACTED]/g' "$f"
done

# 6. Generate summary report
SUMMARY_FILE="${TARGET_DIR}/summary.txt"
{
    echo "========================================================"
    echo " Diagnostic Collection Summary ($TIMESTAMP)"
    echo " Hostname        : $(hostname 2>/dev/null || cat /etc/hostname 2>/dev/null || echo 'unknown')"
    echo " Kernel          : $(uname -r 2>/dev/null || echo 'unknown')"
    echo " Uptime          : $(uptime 2>/dev/null || echo 'unknown')"
    echo " Disk Usage      : $(df -h / /tmp 2>/dev/null | awk 'NR>1 {print $6, $5, $4 " free"}' || true)"
    echo "========================================================"
    echo ""
    echo "Files Extracted:"
    ls -lah "$TARGET_DIR"
    echo ""
    echo "Top Recurring Error Signatures:"
    find "$TARGET_DIR" -type f -name "*.log" -exec grep -E -i 'error|fatal|exception|panic' {} + 2>/dev/null | \
        sed -E 's/[0-9a-fA-F-]{36}/<UUID>/g; s/[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}/<IP>/g' | \
        awk '{for(i=4;i<=NF;i++) printf "%s ", $i; print ""}' | \
        sort | uniq -c | sort -rn | head -n 10 || echo "No recurring error signatures detected."
} > "$SUMMARY_FILE"

# 7. Package everything into tar.gz
ARCHIVE="${WORKDIR}/${BUNDLE_NAME}.tar.gz"
echo "[*] Packaging bundle into $ARCHIVE..."
tar -czf "$ARCHIVE" -C "$WORKDIR" "$BUNDLE_NAME"

# Clean up raw uncompressed target dir
rm -rf "$TARGET_DIR"

echo "=== SUCCESS: Remote bundle created at $ARCHIVE ==="
echo "READY_FOR_COPY:$ARCHIVE"

