# Kubernetes Pod & Container Log Extraction

Staff-level guide to extracting logs from live, crashed, and multi-container Kubernetes pods and nodes.

---

## 1. Essential `kubectl logs` Patterns

```bash
# Basic log retrieval with tail
kubectl logs <pod-name> -n <namespace> --tail=500

# Specify container in multi-container pod (sidecar / proxy / init container)
kubectl logs <pod-name> -c <container-name> -n <namespace> --tail=500

# Stream logs in real-time
kubectl logs -f <pod-name> -n <namespace>

# Time-bounded retrieval (crucial for incident triage)
kubectl logs <pod-name> -n <namespace> --since=30m --timestamps
kubectl logs <pod-name> -n <namespace> --since-time="2026-11-08T10:00:00Z"
```

---

## 2. Multi-Pod & Multi-Container Extraction

Instead of checking individual pods one-by-one, query entire deployments or replica sets using label selectors:

```bash
# Query all pods matching label across all containers with prefix
kubectl logs -n prod -l app=payment-service --all-containers=true --prefix=true --tail=200

# Follow logs from entire deployment
kubectl logs -n prod deployment/order-service -f --max-log-requests=10

# Extract logs from an init container (e.g. migration or setup failure)
kubectl logs <pod-name> -c init-db-migrate -n prod
```

---

## 3. The Crashed Pod Dilemma (`--previous`)

When a pod enters **`CrashLoopBackOff`** or restarts, running `kubectl logs <pod-name>` only shows the newly started container's boot logs, which is useless for root-cause analysis.

### Always Check the Terminated Instance:
```bash
# Extract logs from the previous instance immediately before the crash
kubectl logs <pod-name> -n <namespace> --previous

# Check pod termination state and exit code
kubectl get pod <pod-name> -n <namespace> -o jsonpath='{range .status.containerStatuses[*]}{.name}{": ExitCode="}{.lastState.terminated.exitCode}{" Reason="}{.lastState.terminated.reason}{" FinishedAt="}{.lastState.terminated.finishedAt}{"\n"}{end}'
```

### Exit Code Diagnosis Matrix
| Exit Code | Reason | Meaning & Investigation Path |
|---|---|---|
| **137** | `OOMKilled` | Container exceeded cgroup memory limit (`limits.memory`). Check `dmesg` or pod events. |
| **143** | `Terminated` | SIGTERM issued (Kubernetes graceful termination or pre-emption). |
| **1** | `Error` | Application threw uncaught exception, runtime panic, or fatal assertion. |
| **2** | `Misuse of shell builtins` | Shell script syntax error in `entrypoint` / `command`. |
| **127** | `Command not found` | Binary or script path specified in `command` does not exist in container image. |
| **126** | `Command invoked cannot execute` | Permission denied on executable script (missing `chmod +x`). |

---

## 4. Node-Level Direct Extraction (`/var/log/pods/` & `crictl`)

If `kubectl logs` fails (e.g., API server down, pod evicted, or node not ready), extract logs directly from the node via SSH:

### Standard Kubernetes Log Paths on Node
```bash
# Path format: /var/log/pods/<namespace>_<pod-name>_<pod-uid>/<container-name>/<restart-count>.log
ls -lah /var/log/pods/prod_order-service-*/order-service/*.log

# Search directly on the node using zgrep/grep
zgrep -E 'ERROR|FATAL' /var/log/pods/prod_payment-*/*/*.log | tail -n 100
```

### Container Runtime CLI (`crictl`)
```bash
# List containers on node
sudo crictl ps -a --name payment-service

# Inspect logs of specific container ID
sudo crictl logs --tail=100 <container-id>
```
