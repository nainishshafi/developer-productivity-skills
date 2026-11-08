#!/usr/bin/env bash
# extract-remote-linux-logs.sh — Extract and filter error logs from remote Linux hosts over SSH
# Usage:
#   ./extract-remote-linux-logs.sh -h <host> -u <user> [-J <bastion>] [-i <key>] [-p <log-path>] [-s <systemd-unit>]

set -euo pipefail

# Defaults
HOST=""
USER=""
BASTION=""
IDENTITY_FILE=""
LOG_PATH=""
SYSTEMD_UNIT=""
SINCE="1h"
OUTPUT_DIR="./extracted-logs"
TIMEOUT=5

print_usage() {
    cat << 'EOF'
Usage: extract-remote-linux-logs.sh [OPTIONS]

Options:
  -h, --host <hostname/ip>     Remote Linux server hostname or IP address
  -u, --user <username>        SSH user
  -J, --bastion <bastion>      SSH jump host (e.g. "jumpuser@bastion.corp.net")
  -i, --identity <path>        Path to private SSH key
  -p, --log-path <path>        Remote log file path (e.g. "/var/log/app.log" or "/var/log/nginx/error.log")
  -s, --systemd <unit>         Systemd service unit to query via journalctl (e.g. "kubelet", "nginx")
  --since <duration>           Time window (e.g. "30 minutes ago", "2 hours ago", default: "1h")
  -o, --output-dir <dir>       Local output directory (default: "./extracted-logs")
  --help                       Show this help message
EOF
    exit "${1:-0}"
}

# Parse command line flags
while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--host) HOST="$2"; shift 2 ;;
        -u|--user) USER="$2"; shift 2 ;;
        -J|--bastion) BASTION="$2"; shift 2 ;;
        -i|--identity) IDENTITY_FILE="$2"; shift 2 ;;
        -p|--log-path) LOG_PATH="$2"; shift 2 ;;
        -s|--systemd) SYSTEMD_UNIT="$2"; shift 2 ;;
        --since) SINCE="$2"; shift 2 ;;
        -o|--output-dir) OUTPUT_DIR="$2"; shift 2 ;;
        --help) print_usage 0 ;;
        *) echo "Error: Unknown argument '$1'"; print_usage 1 ;;
    esac
done

if [[ -z "$HOST" || -z "$USER" ]]; then
    echo "Error: Both --host and --user are required."
    print_usage 1
fi

if [[ -z "$LOG_PATH" && -z "$SYSTEMD_UNIT" ]]; then
    echo "Error: Must specify either --log-path <path> or --systemd <unit>."
    print_usage 1
fi

mkdir -p "$OUTPUT_DIR"
TIMESTAMP=$(date -u +"%Y%m%d_%H%M%SZ")
TARGET_PREFIX="${OUTPUT_DIR}/${HOST}_${TIMESTAMP}"

# Build SSH options
SSH_OPTS=(
    "-o" "BatchMode=yes"
    "-o" "ConnectTimeout=${TIMEOUT}"
    "-o" "StrictHostKeyChecking=accept-new"
    "-o" "ServerAliveInterval=15"
    "-T"
)

if [[ -n "$BASTION" ]]; then
    SSH_OPTS+=("-J" "$BASTION")
fi

if [[ -n "$IDENTITY_FILE" ]]; then
    SSH_OPTS+=("-i" "$IDENTITY_FILE")
fi

echo "========================================================"
echo " Remote Linux Log Extraction Started"
echo " Target Host      : $USER@$HOST"
echo " Jump Bastion     : ${BASTION:-None}"
echo " Output Directory : $OUTPUT_DIR"
echo "========================================================"

# Test connection
echo "[*] Testing SSH connectivity..."
if ! ssh "${SSH_OPTS[@]}" "${USER}@${HOST}" "uptime" >/dev/null 2>&1; then
    echo "Error: Unable to connect to ${USER}@${HOST} over SSH."
    exit 1
fi
echo "    Connected successfully."

# 1. Systemd journal extraction if specified
if [[ -n "$SYSTEMD_UNIT" ]]; then
    JOURNAL_OUT="${TARGET_PREFIX}_journal_${SYSTEMD_UNIT}.log"
    echo "[*] Querying journalctl for unit: $SYSTEMD_UNIT (since $SINCE)..."
    ssh "${SSH_OPTS[@]}" "${USER}@${HOST}" \
        "journalctl -u '$SYSTEMD_UNIT' --since '$SINCE' -p err..emerg --no-pager" > "$JOURNAL_OUT" 2>&1 || true
    echo "    Saved $(wc -l < "$JOURNAL_OUT") lines to $JOURNAL_OUT"
fi

# 2. File log extraction if specified
if [[ -n "$LOG_PATH" ]]; then
    FILE_OUT="${TARGET_PREFIX}_file.log"
    echo "[*] Extracting and filtering remote log: $LOG_PATH..."
    ssh "${SSH_OPTS[@]}" "${USER}@${HOST}" bash -s -- "$LOG_PATH" << 'EOF' > "$FILE_OUT" 2>&1 || true
        TARGET_FILE="$1"
        if [ ! -f "$TARGET_FILE" ]; then
            echo "Error: Remote file '$TARGET_FILE' does not exist."
            exit 1
        fi

        # Check if file is gzipped or raw
        if [[ "$TARGET_FILE" == *.gz ]]; then
            zgrep -E -i -C 2 'error|fatal|exception|panic|fail|killed' "$TARGET_FILE" | tail -n 5000
        else
            grep -E -i -C 2 'error|fatal|exception|panic|fail|killed' "$TARGET_FILE" | tail -n 5000
        fi
EOF
    echo "    Saved $(wc -l < "$FILE_OUT") lines to $FILE_OUT"
fi

# 3. Always inspect kernel dmesg for OOM-killer events
DMESG_OUT="${TARGET_PREFIX}_dmesg_oom.log"
echo "[*] Checking remote kernel dmesg for OOM killer events..."
ssh "${SSH_OPTS[@]}" "${USER}@${HOST}" \
    "dmesg -T | grep -iE 'killed process|oom-killer|out of memory' | tail -n 50" > "$DMESG_OUT" 2>&1 || true

if [[ -s "$DMESG_OUT" ]]; then
    echo "    [!] Found $(wc -l < "$DMESG_OUT") kernel OOM events: $DMESG_OUT"
else
    rm -f "$DMESG_OUT"
    echo "    No kernel OOM events detected."
fi

echo "========================================================"
echo " Extraction Complete. Artifacts saved in $OUTPUT_DIR"
echo "========================================================"

