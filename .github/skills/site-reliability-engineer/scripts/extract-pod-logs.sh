#!/usr/bin/env bash
# extract-pod-logs.sh — Copies collector to pod /tmp, executes in-situ, copies back bundle via kubectl cp
# Falls back to kubectl logs stream if container root is read-only or lacks shell/tar.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COLLECTOR_SCRIPT="${SCRIPT_DIR}/remote-collector.sh"

# Defaults
NAMESPACE="default"
POD_NAME=""
CONTAINER=""
LABEL_SELECTOR=""
OUTPUT_DIR="./extracted-logs"
SINCE="1h"
CHECK_PREVIOUS=false
TAIL_LINES=5000

print_usage() {
    cat << 'EOF'
Usage: extract-pod-logs.sh [OPTIONS]

Workflow:
  1. Copies 'remote-collector.sh' to pod '/tmp/' via 'kubectl cp'
  2. Executes in-situ in pod to process logs locally without WAN latency
  3. Copies the resulting '/tmp/log-bundle-<timestamp>.tar.gz' back to local directory
  4. Cleans up temporary artifacts in pod '/tmp'
  * Automatically falls back to 'kubectl logs' if container lacks shell or has read-only root.

Options:
  -n, --namespace <ns>       Kubernetes namespace (default: "default")
  -p, --pod <pod-name>       Target pod name
  -l, --label <selector>     Label selector (e.g. "app=payment-service")
  -c, --container <name>     Container name (optional, for multi-container pods)
  -s, --since <duration>     Time window to query (e.g. "30m", "2h", default: "1h")
  -t, --tail <lines>         Max lines to inspect (default: 5000)
  -o, --output-dir <dir>     Local directory to write logs (default: "./extracted-logs")
  --previous                 Also extract previous crashed instance logs (CrashLoopBackOff)
  -h, --help                 Show this help message
EOF
    exit "${1:-0}"
}

# Parse command line flags
while [[ $# -gt 0 ]]; do
    case "$1" in
        -n|--namespace) NAMESPACE="$2"; shift 2 ;;
        -p|--pod) POD_NAME="$2"; shift 2 ;;
        -l|--label) LABEL_SELECTOR="$2"; shift 2 ;;
        -c|--container) CONTAINER="$2"; shift 2 ;;
        -s|--since) SINCE="$2"; shift 2 ;;
        -t|--tail) TAIL_LINES="$2"; shift 2 ;;
        -o|--output-dir) OUTPUT_DIR="$2"; shift 2 ;;
        --previous) CHECK_PREVIOUS=true; shift ;;
        -h|--help) print_usage 0 ;;
        *) echo "Error: Unknown argument '$1'"; print_usage 1 ;;
    esac
done

if [[ -z "$POD_NAME" && -z "$LABEL_SELECTOR" ]]; then
    echo "Error: Must specify either --pod <name> or --label <selector>"
    print_usage 1
fi

mkdir -p "$OUTPUT_DIR"
TIMESTAMP=$(date -u +"%Y%m%d_%H%M%SZ")

# Resolve pods to inspect
PODS=()
if [[ -n "$POD_NAME" ]]; then
    PODS+=("$POD_NAME")
else
    echo "Discovering pods matching label '$LABEL_SELECTOR' in namespace '$NAMESPACE'..."
    mapfile -t PODS < <(kubectl get pods -n "$NAMESPACE" -l "$LABEL_SELECTOR" -o jsonpath='{.items[*].metadata.name}' | tr ' ' '\n')
    if [[ ${#PODS[@]} -eq 0 ]]; then
        echo "Error: No pods found matching label '$LABEL_SELECTOR' in namespace '$NAMESPACE'"
        exit 1
    fi
fi

echo "========================================================"
echo " Kubernetes Pod Log Extraction & Copy"
echo " Target Namespace : $NAMESPACE"
echo " Pods to Extract  : ${PODS[*]}"
echo " Time Window      : Since $SINCE"
echo " Output Directory : $OUTPUT_DIR"
echo "========================================================"

for POD in "${PODS[@]}"; do
    CONTAINER_FLAG=""
    CP_CONTAINER_FLAG=""
    if [[ -n "$CONTAINER" ]]; then
        CONTAINER_FLAG="-c $CONTAINER"
        CP_CONTAINER_FLAG="-c $CONTAINER"
    fi

    echo "[*] Processing pod: $POD..."
    POD_STAGED_SUCCESS=false
    REMOTE_SCRIPT="/tmp/pod-collector-${TIMESTAMP}.sh"

    # Attempt In-Situ Execution in pod /tmp via kubectl cp
    if [[ -f "$COLLECTOR_SCRIPT" ]]; then
        echo "    Attempting in-situ collection via 'kubectl cp' to /tmp..."
        if kubectl cp "$COLLECTOR_SCRIPT" "${NAMESPACE}/${POD}:${REMOTE_SCRIPT}" $CP_CONTAINER_FLAG 2>/dev/null; then
            echo "    Staged collector to ${POD}:${REMOTE_SCRIPT}. Executing..."
            EXEC_OUT=$(kubectl exec "$POD" -n "$NAMESPACE" $CONTAINER_FLAG -- /bin/sh -c "chmod +x '$REMOTE_SCRIPT' && '$REMOTE_SCRIPT' '$SINCE'" 2>/dev/null || true)
            
            REMOTE_ARCHIVE=$(echo "$EXEC_OUT" | grep 'READY_FOR_COPY:' | tail -n 1 | cut -d':' -f2 | tr -d '\r\n')
            if [[ -n "$REMOTE_ARCHIVE" ]]; then
                LOCAL_TAR="${OUTPUT_DIR}/${POD}_$(basename "$REMOTE_ARCHIVE")"
                echo "    Copying bundle from ${POD}:${REMOTE_ARCHIVE} to ${LOCAL_TAR}..."
                if kubectl cp "${NAMESPACE}/${POD}:${REMOTE_ARCHIVE}" "$LOCAL_TAR" $CP_CONTAINER_FLAG 2>/dev/null; then
                    echo "    Copy successful. Cleaning remote pod /tmp..."
                    kubectl exec "$POD" -n "$NAMESPACE" $CONTAINER_FLAG -- rm -f "$REMOTE_SCRIPT" "$REMOTE_ARCHIVE" 2>/dev/null || true
                    tar -xzf "$LOCAL_TAR" -C "$OUTPUT_DIR"
                    POD_STAGED_SUCCESS=true
                fi
            fi
        fi
    fi

    # Fallback to direct kubectl logs streaming if in-situ execution was unavailable
    if [[ "$POD_STAGED_SUCCESS" == false ]]; then
        echo "    Notice: Pod does not support direct cp/exec. Falling back to 'kubectl logs' stream..."
        OUT_PREFIX="${OUTPUT_DIR}/${NAMESPACE}_${POD}_${TIMESTAMP}"
        LOG_FILE="${OUT_PREFIX}.log"
        ERR_FILE="${OUT_PREFIX}_errors.log"

        if kubectl logs "$POD" -n "$NAMESPACE" $CONTAINER_FLAG --since="$SINCE" --tail="$TAIL_LINES" --timestamps > "$LOG_FILE" 2>&1; then
            echo "    Streamed $(wc -l < "$LOG_FILE") lines to $LOG_FILE"
            grep -E -i -C 2 'error|fatal|exception|panic|fail|killed' "$LOG_FILE" | \
                sed -E 's/Bearer [a-zA-Z0-9._-]+/Bearer [REDACTED]/g' | \
                sed -E 's/(password|secret|token)=[^ &]+/\1=[REDACTED]/g' > "$ERR_FILE" || true
            echo "    Saved $(wc -l < "$ERR_FILE") error lines to $ERR_FILE"
        fi

        # Check crashed instance if requested
        if [[ "$CHECK_PREVIOUS" == true ]]; then
            PREV_LOG_FILE="${OUT_PREFIX}_previous_crash.log"
            echo "    Checking previous crashed container logs (--previous)..."
            if kubectl logs "$POD" -n "$NAMESPACE" $CONTAINER_FLAG --previous --tail="$TAIL_LINES" --timestamps > "$PREV_LOG_FILE" 2>/dev/null; then
                echo "    [!] Found crashed container logs: $PREV_LOG_FILE"
            else
                rm -f "$PREV_LOG_FILE"
            fi
        fi
    fi
done

echo "========================================================"
echo " Extraction Complete. Artifacts saved in $OUTPUT_DIR"
echo "========================================================"
