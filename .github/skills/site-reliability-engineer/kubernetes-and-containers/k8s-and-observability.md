# Kubernetes & Observability SRE

## 1. Pod & Node Triage Runbook

```bash
kubectl get events -A --sort-by='.lastTimestamp' | tail -n 30
kubectl get pods -A --field-selector=status.phase!=Running
kubectl describe pod <pod> -n <ns>                 # Check Events, Conditions, Last State (Exit Code)
kubectl logs <pod> -n <ns> --previous --tail=200   # Logs from crashed container before restart
kubectl top nodes && kubectl top pods -n <ns> --sort-by=memory
```

| Symptom | Common Root Cause | Verification & Fix |
|---|---|---|
| **`OOMKilled` (Exit `137`)** | Container RSS exceeded `resources.limits.memory` | Check `kubectl describe pod` `Last State: Terminated (Reason: OOMKilled)`; raise limit or fix memory leak / set JVM `-XX:MaxRAMPercentage=75.0` |
| **`CrashLoopBackOff`** | App startup failure, missing env/secret, or failing `livenessProbe` | Inspect `kubectl logs --previous`; verify `startupProbe` gives slow apps time to boot before `livenessProbe` kills them |
| **`Pending`** | Insufficient CPU/memory, PVC bind failure, or node taint/affinity mismatch | Check `kubectl describe pod` `Events` (`FailedScheduling`) and `kubectl describe nodes` allocatable capacity |
| **`ImagePullBackOff`** | Wrong tag, registry auth secret expired, or rate limit | Verify `imagePullSecrets` / Managed Identity and registry connectivity |
| **DNS Timeouts (`5s` spikes)** | `conntrack` race or CoreDNS CPU throttling | Check CoreDNS pod CPU/logs (`kubectl logs -n kube-system -l k8s-app=kube-dns`); enable `NodeLocal DNSCache` |

---

## 2. Resilience Controls (HPA, PDB, QoS)

- **PodDisruptionBudget (PDB):** Always define `minAvailable` or `maxUnavailable` for multi-replica stateful/critical services so node drains and cluster upgrades never take down all replicas simultaneously.
- **QoS Classes:** Set `requests.memory == limits.memory` (`Guaranteed` QoS) for latency-sensitive/critical pods to prevent eviction under node memory pressure.
- **Graceful Shutdown:** Handle `SIGTERM` in app code + add `preStop: { exec: { command: ["sh", "-c", "sleep 5"] } }` so EndpointSlice removal propagates to Ingress/kube-proxy before the process stops accepting connections.

---

## 3. Prometheus / PromQL Golden Signals (RED)

```promql
# 1. Request Rate (RPS)
sum(rate(http_requests_total{service="api"}[5m]))

# 2. Error Rate (% 5xx)
100 * sum(rate(http_requests_total{service="api",status=~"5.."}[5m]))
  / sum(rate(http_requests_total{service="api"}[5m]))

# 3. Latency P95 & P99 (histogram)
histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{service="api"}[5m])) by (le))
histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket{service="api"}[5m])) by (le))
```

- **OpenTelemetry Collector & Distributed Tracing:** Deploy **OpenTelemetry Collectors** as DaemonSets or Sidecars to batch, filter, and route traces/metrics/logs vendor-neutrally, propagating `traceparent` (W3C Trace Context) across HTTP/gRPC/Kafka headers so slow `P99` spans correlate end-to-end.
- **eBPF Pod-to-Pod Observability:** Use Cilium Hubble or OpenTelemetry eBPF instrumentation to inspect cross-node packet drops, DNS failures, and TCP retransmissions without modifying container images.
