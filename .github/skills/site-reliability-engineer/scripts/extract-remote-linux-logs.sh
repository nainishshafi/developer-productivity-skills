#!/usr/bin/env bash
# extract-remote-linux-logs.sh — Copies collector to remote /tmp, executes in-situ, copies back the bundle, and cleans up
# Usage:
#   ./extract-remote-linux-logs.sh -h <host> -u <user> [-J <bastion>] [-i <key>] [-p <log-path>] [-s <systemd-unit>]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COLLECTOR_SCRIPT="${SCRIPT_DIR}/remote-collector.sh"

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

Workflow:
  1. Copies 'remote-collector.sh' to remote host '/tmp/remote-collector.sh' via SCP
  2. Executes the collector remotely in '/tmp' to search logs, dmesg, and journalctl
  3. Copies the resulting '/tmp/log-bundle-<timestamp>.tar.gz' back to local directory via SCP
  4. Cleans up temporary collector and archive files on the remote host
  5. Unpacks and displays the diagnostic summary locally

Options:
  -h, --host <hostname/ip>     Remote Linux server hostname or IP address
  -u, --user <username>        SSH user
  -J, --bastion <bastion>      SSH jump host (e.g. "jumpuser@bastion.corp.net")
  -i, --identity <path>        Path to private SSH key
  -p, --log-path <path>        Remote log file path (e.g. "/var/log/app.log")
  -s, --systemd <unit>         Systemd service unit to query via journalctl (e.g. "kubelet")
  --since <duration>           Time window (default: "1h")
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

if [[ ! -f "$COLLECTOR_SCRIPT" ]]; then
    echo "Error: Local collector script '$COLLECTOR_SCRIPT' not found."
    exit 1
fi

mkdir -p "$OUTPUT_DIR"
TIMESTAMP=$(date -u +"%Y%m%d_%H%M%SZ")

# Build SSH / SCP options
SSH_OPTS=(
    "-o" "BatchMode=yes"
    "-o" "ConnectTimeout=${TIMEOUT}"
    "-o" "StrictHostKeyChecking=accept-new"
    "-o" "ServerAliveInterval=15"
)

if [[ -n "$BASTION" ]]; then
    SSH_OPTS+=("-J" "$BASTION")
fi

if [[ -n "$IDENTITY_FILE" ]]; then
    SSH_OPTS+=("-i" "$IDENTITY_FILE")
fi

echo "========================================================"
echo " Remote Staging & In-Situ Log Extraction"
echo " Target Host      : $USER@$HOST"
echo " Jump Bastion     : ${BASTION:-None}"
echo " Local Output Dir : $OUTPUT_DIR"
echo "========================================================"

# Step 1: Copy collector script to remote /tmp
REMOTE_SCRIPT="/tmp/remote-collector-${TIMESTAMP}.sh"
echo "[1/5] Copying collector script to remote ${USER}@${HOST}:${REMOTE_SCRIPT}..."
scp "${SSH_OPTS[@]}" "$COLLECTOR_SCRIPT" "${USER}@${HOST}:${REMOTE_SCRIPT}"

# Step 2: Execute collector in /tmp on remote host
echo "[2/5] Executing collector remotely in /tmp..."
EXEC_OUTPUT=$(ssh "${SSH_OPTS[@]}" -T "${USER}@${HOST}" \
    "chmod +x '$REMOTE_SCRIPT' && '$REMOTE_SCRIPT' '$SINCE' '$LOG_PATH' '$SYSTEMD_UNIT'")

echo "$EXEC_OUTPUT"

# Extract archive path from remote output marker
REMOTE_ARCHIVE=$(echo "$EXEC_OUTPUT" | grep 'READY_FOR_COPY:' | tail -n 1 | cut -d':' -f2 | tr -d '\r\n')

if [[ -z "$REMOTE_ARCHIVE" ]]; then
    echo "Error: Remote collector failed to produce archive."
    ssh "${SSH_OPTS[@]}" -T "${USER}@${HOST}" "rm -f '$REMOTE_SCRIPT'" || true
    exit 1
fi

ARCHIVE_BASENAME=$(basename "$REMOTE_ARCHIVE")
LOCAL_ARCHIVE="${OUTPUT_DIR}/${ARCHIVE_BASENAME}"

# Step 3: Copy generated bundle back to local output directory
echo "[3/5] Copying bundle from ${USER}@${HOST}:${REMOTE_ARCHIVE} to ${LOCAL_ARCHIVE}..."
scp "${SSH_OPTS[@]}" "${USER}@${HOST}:${REMOTE_ARCHIVE}" "$LOCAL_ARCHIVE"

# Step 4: Clean up remote /tmp artifacts
echo "[4/5] Cleaning up remote /tmp artifacts..."
ssh "${SSH_OPTS[@]}" -T "${USER}@${HOST}" "rm -f '$REMOTE_SCRIPT' '$REMOTE_ARCHIVE'"
echo "    Remote cleanup verified."

# Step 5: Unpack bundle locally and display summary
echo "[5/5] Unpacking bundle locally..."
LOCAL_EXTRACT_DIR="${OUTPUT_DIR}/${ARCHIVE_BASENAME%.tar.gz}"
mkdir -p "$LOCAL_EXTRACT_DIR"
tar -xzf "$LOCAL_ARCHIVE" -C "$OUTPUT_DIR"

if [[ -f "${LOCAL_EXTRACT_DIR}/summary.txt" ]]; then
    echo ""
    cat "${LOCAL_EXTRACT_DIR}/summary.txt"
fi

echo "========================================================"
echo " Success! Bundle copied and unpacked in: $LOCAL_EXTRACT_DIR"
echo "========================================================"
