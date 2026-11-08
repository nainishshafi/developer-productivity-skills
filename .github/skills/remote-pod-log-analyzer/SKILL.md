---
name: remote-pod-log-analyzer
description: Analyzes remote Linux host and Kubernetes pod/container logs using SSH, kubectl, journalctl, grep, awk, sed, ripgrep, and jq. Troubleshoots CrashLoopBackOff, OOMKilled (Exit Code 137), distributed trace correlations, and high-cardinality error spikes without transferring giant files locally. Use when asked to "analyze remote logs", "remote linux log analysis", "remote pod log analysis", "kubectl logs triage", "ssh log grep", "debug pod crash", "journalctl error analysis", or "parse nginx access logs".
version: 1.0.0
---

# Remote Pod & Linux Log Analyzer

Staff-level operational framework for searching, streaming, and statistically analyzing remote Linux and Kubernetes pod logs over SSH and kubectl without downloading giant log files locally.

---

## When to Use This Skill

- Investigating production incidents, latency spikes, and 5xx HTTP error cascades.
- Diagnosing Kubernetes container restarts, `CrashLoopBackOff`, and `OOMKilled` (Exit Code 137).
- Querying remote servers behind SSH bastions (`-J`) without interactive password hangs (`BatchMode=yes`).
- Searching uncompressed (`.log`) and rotated compressed (`.gz`) logs in-stream using `zgrep`, `ripgrep`, or `sed`.
- Aggregating error distributions, calculating latency percentiles (P50/P95/P99), and filtering JSON logs (`jq`).
- Correlating distributed traces (`trace_id`, `correlation_id`) across microservices and reverse proxies (Nginx/Envoy).

---

## Architectural Philosophy: Remote Stream Processing

- **Compute Where the Data Lives**: Never download multi-gigabyte log files over SSH just to search them locally. Filter and aggregate on the remote host, streaming only the distilled results.
- **Fail Fast on SSH Handshakes**: Always enforce non-interactive flags (`-o BatchMode=yes -o ConnectTimeout=5`) to prevent script hangs.
- **Check Terminated Containers**: For crashed pods, inspect `kubectl logs --previous` and check exit codes.
- **Never Unpack `.gz` to Disk**: Stream compressed logs with `zcat` or `zgrep` to protect node disk space.

---

## Core Knowledge Modules

Load the relevant module based on your task:

| Domain | Description | Module File |
|---|---|---|
| **SSH & Bastions** | Non-interactive SSH flags, bastion hopping (`-J`), remote heredoc execution | [SSH Execution & Bastions](file:///.github/skills/remote-pod-log-analyzer/ssh-and-connectivity/ssh-execution-and-bastions.md) |
| **Kubernetes & Pods** | `kubectl logs`, multi-container, `--previous`, exit codes (137 OOMKilled), node logs | [Pod Log Extraction](file:///.github/skills/remote-pod-log-analyzer/kubernetes-and-containers/pod-log-extraction.md) |
| **Grep & Ripgrep** | High-performance regex, context (`-C`), rotated `.gz` files (`zgrep`), time slicing | [Grep & Compressed Logs](file:///.github/skills/remote-pod-log-analyzer/log-processing-toolkit/grep-ripgrep-and-compressed.md) |
| **Awk Stream Parsing** | Field extraction, status code distributions, latency percentiles (P95/P99), stack traces | [Awk & Stream Parsing](file:///.github/skills/remote-pod-log-analyzer/log-processing-toolkit/awk-and-stream-parsing.md) |
| **JSON & JQ Parsing** | Structured JSON logs (`ndjson`), filtering by level, extracting trace IDs, `@tsv` tables | [JSON & JQ Parsing](file:///.github/skills/remote-pod-log-analyzer/log-processing-toolkit/json-and-jq-parsing.md) |
| **Journalctl & Dmesg** | Systemd unit logs (`-u`), kernel ring buffer (`dmesg -T`), hardware/OOM faults | [Systemd & Kernel Dmesg](file:///.github/skills/remote-pod-log-analyzer/log-processing-toolkit/systemd-and-journalctl.md) |
| **Incident Triage** | 5-step triage runbook, error signature clustering, Nginx/Envoy access logs | [Incident Triage Runbook](file:///.github/skills/remote-pod-log-analyzer/analytical-recipes/incident-triage-and-root-cause.md) |

---

## References

- [Remote Pod Log Analyzer Reference Guide](file:///.github/skills/remote-pod-log-analyzer/references/remote-pod-log-analyzer-reference.md) — Master command cheatsheet and diagnostic flows.
- [Troubleshoot and Fix](file:///.github/skills/troubleshoot-and-fix/SKILL.md) — Isolated reproduction testbeds and circuit breaker remediation.
- [Algorithmic Complexity Analyzer](file:///.github/skills/algorithmic-complexity-analyzer/SKILL.md) — Algorithmic time and space analysis.
