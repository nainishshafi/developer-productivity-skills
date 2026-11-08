# Structured JSON Log Analysis with JQ

Staff-level guide to filtering, slicing, and aggregating JSON logs emitted by containerized microservices.

---

## 1. Fast Filtering by Log Level & Attributes

Cloud-native applications (Go, Node.js, Python, Java) emit structured JSON lines (`ndjson` / `jsonl`):

```bash
# Filter error and fatal logs only
kubectl logs <pod-name> | jq -c 'select(.level == "error" or .level == "fatal")'

# Filter by HTTP status code >= 500
kubectl logs <pod-name> | jq -c 'select(.status >= 500)'

# Extract specific fields into clean readable columns
kubectl logs <pod-name> | jq -r '[.time, .level, .status, .duration_ms, .message] | @tsv' | column -t
```

---

## 2. Distributed Tracing & Correlation ID Isolation

When debugging distributed requests spanning across multiple microservices:

```bash
# Find all log entries matching a specific trace_id across pods
kubectl logs -l app=order-service --tail=2000 | \
    jq -c 'select(.trace_id == "4bf92f3577b34da6a3ce929d0e0e4736")'

# Extract the root cause exception and stack trace from JSON
kubectl logs <pod-name> | \
    jq -r 'select(.error != null) | "=== \(.time) \(.msg) ===\n\(.error.stack // .error)"'
```

---

## 3. Aggregations & Frequency Counts with `jq`

```bash
# Count error types and rank by frequency
kubectl logs <pod-name> --since=1h | \
    jq -r 'select(.level == "error") | .error.type // .message' | \
    sort | uniq -c | sort -rn | head -n 10

# Calculate average response time from JSON logs
kubectl logs <pod-name> | jq -s 'map(.duration_ms // 0) | (add / length)'
```

---

## 4. In-Stream Unpacking for Mixed Output

Sometimes third-party tools mix raw text and JSON in stdout:

```bash
# Safely parse JSON lines, skipping unparseable raw text lines
kubectl logs <pod-name> | jq -R 'fromjson? | select(.level == "error")'
```
