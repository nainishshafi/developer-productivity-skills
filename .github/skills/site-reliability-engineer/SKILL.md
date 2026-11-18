---
name: site-reliability-engineer
description: >-
  Comprehensive Site Reliability Engineering (SRE) guidance across Linux, Windows Server, Microsoft Azure, Kubernetes, remote SSH/bastion access, and log parsing. Covers SLIs/SLOs, error budgets, burn-rate alerting, USE/RED diagnostics, OOM/CPU/disk/network triage, Azure Monitor KQL, AKS/Windows Event/ETW/IIS troubleshooting, and streaming log analysis via SSH, kubectl, journalctl, grep, awk, and jq. Use when asked to "troubleshoot production incident", "sre triage", "debug linux server", "debug windows server", "troubleshoot azure", "define slo and error budget", "analyze k8s outage", "analyze remote logs", "remote linux log analysis", "remote pod log analysis", "kubectl logs triage", "ssh log grep", "debug pod crash", "journalctl error analysis", or "parse nginx access logs".
version: 1.1.0
---

# Site Reliability Engineer (SRE)

Modular SRE operational, observability, and remote log-analysis skill. **Load only the module(s) relevant to the task.**

## Core SRE Directives

1. **Read-Only Triage & Remote Filtering First:** Gather telemetry and filter logs remotely (`--since`, `tail`, `awk`, `jq`) before restarting services or copying large archives.
2. **Error Budgets & USE/RED:** Gate risky changes with SLO burn rates; audit infra via **USE** and services via **RED**.
3. **Blast-Radius & Blameless Postmortems:** Prefer traffic draining/rollbacks over destructive mutations; document timeline, 5-Whys root cause, and toil-eliminating actions.

## Knowledge Modules

| Domain | Module(s) |
|---|---|
| **Core SRE & Incidents** | [slos-and-incident-response.md](core/slos-and-incident-response.md), [incident-triage-and-root-cause.md](analytical-recipes/incident-triage-and-root-cause.md) |
| **Linux & Systemd** | [linux-sre-and-troubleshooting.md](linux/linux-sre-and-troubleshooting.md), [systemd-and-journalctl.md](log-processing-toolkit/systemd-and-journalctl.md) |
| **Windows Server & IIS** | [windows-sre-and-troubleshooting.md](windows/windows-sre-and-troubleshooting.md) |
| **Microsoft Azure** | [azure-sre-and-resilience.md](azure/azure-sre-and-resilience.md) |
| **Kubernetes & Observability** | [k8s-and-observability.md](kubernetes-and-containers/k8s-and-observability.md), [pod-log-extraction.md](kubernetes-and-containers/pod-log-extraction.md) |
| **SSH & Remote Access** | [remote-ssh-and-log-parsing.md](logs-and-remote-access/remote-ssh-and-log-parsing.md), [ssh-execution-and-bastions.md](ssh-and-connectivity/ssh-execution-and-bastions.md), [remote-staging-and-copy-protocol.md](ssh-and-connectivity/remote-staging-and-copy-protocol.md) |
| **Log Parsing Toolkit** | [awk-and-stream-parsing.md](log-processing-toolkit/awk-and-stream-parsing.md), [grep-ripgrep-and-compressed.md](log-processing-toolkit/grep-ripgrep-and-compressed.md), [json-and-jq-parsing.md](log-processing-toolkit/json-and-jq-parsing.md) |
| **Master Reference** | [site-reliability-engineer-reference.md](references/site-reliability-engineer-reference.md) |

## Extraction Scripts (`scripts/`)

Verify target connectivity and inspect `--help` output before running; check exit code `0` and bounded stdout:
- `extract-remote-linux-logs.sh` / `remote-collector.sh` — Non-interactive SSH systemd, kernel, and host log collection.
- `extract-pod-logs.sh` — `kubectl logs` wrapper (`--previous`, multi-container, time windows).
- `extract-remote-logs.ps1` — Cross-platform PowerShell wrapper for remote Linux hosts and Kubernetes pods.
