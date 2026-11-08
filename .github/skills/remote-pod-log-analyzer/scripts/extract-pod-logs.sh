#!/usr/bin/env bash
# extract-pod-logs.sh — Stream and extract error/troubleshooting logs from Kubernetes pods to local files
# Usage:
#   ./extract-pod-logs.sh -n <namespace> -p <pod-name> [-c <container>] [-o <output-dir>] [--since <duration>] [--previous]
#   ./extract-pod-logs.sh -n <namespace> -l <label-selector> [-o <output-dir>] [--since <duration>]

set -euo pipefail

# Defaults
NAMESPACE="default"
POD_NAME=""
CONTAINER=""
LABEL_SELECTOR=""
OUTPUT_DIR="./extracted-logs"
SINCE="1h"
CHECK_PREVIOUS=false
FILTER_ERRORS=true
TAIL_LINES=5000

print_usage() {
    cat << 'EOF'
Usage: extract-pod-logs.sh [OPTIONS]

Options:
  -n, --namespace <ns>       Kubernetes namespace (default: "default")
  -p, --pod <pod-name>       Target pod name
  -l, --label <selector>     Label selector (e.g. "app=payment-service")
  -c, --container <name>     Container name (optional, for multi-container pods)
  -s, --since <duration>     Time window to query (e.g. "30m", "2h", default: "1h")
  -t, --tail <lines>         Max lines to inspect (default: 5000)
  -o, --output-dir <dir>     Local directory to write logs (default: "./extracted-logs")
  --previous                 Also extract previous crashed instance logs (CrashLoopBackOff)
  --raw                      Extract full raw logs without filtering for ERROR/FATAL
  -h, --help                 Show this help message
EOF
    exit 1
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
        --raw) FILTER_ERRORS=false; shift ;;
        -h|--help) print_usage ;;
        *) echo "Error: Unknown argument '$1'"; print_usage ;;
    esac
done

if [[ -z "$POD_NAME" && -z "$LABEL_SELECTOR" ]]; then
    echo "Error: Must specify either --pod <name> or --label <selector>"
    print_usage
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
echo " Kubernetes Pod Log Extraction Started"
echo " Target Namespace : $NAMESPACE"
echo " Pods to Extract  : ${PODS[*]}"
echo " Time Window      : Since $SINCE"
echo " Output Directory : $OUTPUT_DIR"
echo "========================================================"

for POD in "${PODS[@]}"; do
    TARGET_CONTAINER_FLAG=""
    if [[ -n "$CONTAINER" ]]; then
        TARGET_CONTAINER_FLAG="-c $CONTAINER"
    fi

    OUT_PREFIX="${OUTPUT_DIR}/${NAMESPACE}_${POD}_${TIMESTAMP}"
    LOG_FILE="${OUT_PREFIX}.log"
    ERR_FILE="${OUT_PREFIX}_errors.log"

    echo "[*] Extracting logs for pod: $POD..."

    # Stream logs to local file
    if kubectl logs "$POD" -n "$NAMESPACE" $TARGET_CONTAINER_FLAG --since="$SINCE" --tail="$TAIL_LINES" --timestamps > "$LOG_FILE" 2>&1; then
        TOTAL_LINES=$(wc -l < "$LOG_FILE")
        echo "    Saved $TOTAL_LINES log lines to $LOG_FILE"
    else
        echo "    Warning: Failed to extract logs for $POD (pod might be terminated or pending)"
        continue
    fi

    # Check for previous crashed instance if requested
    if [[ "$CHECK_PREVIOUS" == true ]]; then
        PREV_LOG_FILE="${OUT_PREFIX}_previous_crash.log"
        echo "[*] Checking previous crashed container instance (--previous)..."
        if kubectl logs "$POD" -n "$NAMESPACE" $TARGET_CONTAINER_FLAG --previous --tail="$TAIL_LINES" --timestamps > "$PREV_LOG_FILE" 2>/dev/null; then
            PREV_LINES=$(wc -l < "$PREV_LOG_FILE")
            echo "    [!] Found crashed container logs ($PREV_LINES lines): $PREV_LOG_FILE"
        else
            rm -f "$PREV_LOG_FILE"
            echo "    No previous terminated container found for $POD."
        fi
    fi

    # Extract distilled errors and stack traces
    if [[ "$FILTER_ERRORS" == true && -s "$LOG_FILE" ]]; then
        echo "[*] Filtering error signatures and scrubbing secrets..."
        grep -E -i -C 3 'error|fatal|exception|panic|fail|killed|timeout' "$LOG_FILE" | \
            sed -E 's/Bearer [a-zA-Z0-9._-]+/Bearer [REDACTED]/g' | \
            sed -E 's/(password|secret|token)=[^ &]+/\1=[REDACTED]/g' > "$ERR_FILE" || true

        ERROR_COUNT=$(wc -l < "$ERR_FILE")
        echo "    Extracted $ERROR_COUNT error/context lines to $ERR_FILE"

        # Generate top error signatures summary
        SUMMARY_FILE="${OUT_PREFIX}_summary.txt"
        {
            echo "Log Extraction Summary for $POD ($TIMESTAMP)"
            echo "Total Log Lines: $TOTAL_LINES"
            echo "Error Lines: $ERROR_COUNT"
            echo ""
            echo "Top 10 Error Signatures:"
            grep -E -i 'error|fatal|exception|panic' "$ERR_FILE" | \
                sed -E 's/[0-9a-fA-F-]{36}/<UUID>/g; s/[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}/<IP>/g' | \
                awk '{for(i=4;i<=NF;i++) printf "%s ", $i; print ""}' | \
                sort | uniq -c | sort -rn | head -n 10 || echo "No recurring patterns found."
        } > "$SUMMARY_FILE"
        echo "    Summary report written to $SUMMARY_FILE"
    fi
done

echo "========================================================"
echo " Extraction Complete. Artifacts saved in $OUTPUT_DIR"
echo "========================================================"
