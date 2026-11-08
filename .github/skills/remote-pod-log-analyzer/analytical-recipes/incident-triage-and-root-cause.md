# Incident Triage & Root Cause Analysis Runbook

Battle-tested workflows for rapid root-cause isolation during production outages and log spikes.

---

## 1. The 5-Step Incident Triage Workflow

```
[1. Isolate Time Window] ──> [2. Cluster Error Signatures] ──> [3. Trace Request & Correlation ID]
                                                                        │
[5. Resolve or Escalate] <── [4. Inspect Host & Resource Limits] <──────┘
```

### Step 1: Establish Time Boundary
- Pinpoint when alerts fired or latency spiked (e.g. `2026-11-08 14:20 UTC`).
- Restrict all log queries to `[Spike - 15m, Spike + 15m]` to eliminate noise:
```bash
kubectl logs <pod-name> -n prod --since-time="2026-11-08T14:05:00Z" --timestamps > triage.log
```

### Step 2: Cluster Top Error Signatures
- Count and rank error messages to find the dominant failure mode:
```bash
grep -E 'ERROR|FATAL' triage.log | \
    sed -E 's/[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}/<UUID>/g' | \
    sed -E 's/[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}/<IP>/g' | \
    sed -E 's/id=[0-9]+/<ID>/g' | \
    awk '{for(i=4;i<=NF;i++) printf "%s ", $i; print ""}' | \
    sort | uniq -c | sort -rn | head -n 10
```

### Step 3: Extract Representative Trace
- Take one instance of the top error signature and extract its `trace_id` or `correlation_id`.
- Follow the request journey upstream and downstream across microservices:
```bash
kubectl logs -l app=ingress-nginx -n ingress --since=1h | grep "<trace-id>"
kubectl logs -l app=order-service -n prod --since=1h | grep "<trace-id>"
kubectl logs -l app=payment-service -n prod --since=1h | grep "<trace-id>"
```

### Step 4: Check Pod Lifecycles & Host Resources
- Did the pod restart? Run `kubectl get pod <pod-name> -o yaml` and check `restartCount` and `lastState`.
- Check exit codes:
  - `137` = `OOMKilled` (increase `limits.memory` or fix memory leak).
  - `143` = `Graceful termination` (check if HPA scale-down or spot instance preemption occurred).
- Check kernel events:
  ```bash
  ssh user@node "dmesg -T | grep -iE 'killed process|oom-killer' | tail -n 10"
  ```

### Step 5: Formulate Fix or Circuit Break
- Reference [`troubleshoot-and-fix`](file:///.github/skills/troubleshoot-and-fix/SKILL.md) to isolate the reproduction in a standalone testbed before patching production.

---

## 2. Ingress & Reverse Proxy Access Log Analysis (Nginx / Envoy)

```bash
# Top 10 paths returning 5xx errors
awk '$9 >= 500 { print $7 }' /var/log/nginx/access.log | sort | uniq -c | sort -rn | head -n 10

# Count requests per minute to detect traffic spikes or DDoS
awk '{print substr($4, 2, 17)}' /var/log/nginx/access.log | sort | uniq -c

# Top 10 user agents triggering 404 / 403 (bot scanner detection)
awk -F'"' '$3 ~ / 40[34] / { print $6 }' /var/log/nginx/access.log | sort | uniq -c | sort -rn | head -n 10
```
