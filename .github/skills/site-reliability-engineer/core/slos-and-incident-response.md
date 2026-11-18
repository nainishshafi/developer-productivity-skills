# Core SRE: SLIs, SLOs, Error Budgets & Incident Response

## 1. SLIs, SLOs & Error Budgets

- **SLI (Service Level Indicator):** Quantitative ratio of good events to valid events:
  $$\text{SLI} = \frac{\text{Good Events}}{\text{Valid Events}} \times 100\%$$
  - *Availability SLI:* Non-5xx HTTP responses / total valid requests (excluding synthetic health probes if they skew traffic).
  - *Latency SLI:* Requests served faster than threshold $\tau$ (e.g., $P99 < 250\text{ms}$) / total valid requests.
  - *Freshness / Pipeline SLI:* Partitions or messages processed within SLA window / total scheduled runs.
- **SLO (Service Level Objective):** Target reliability over a rolling window (typically 28 or 30 days), e.g. `99.9%` availability (`43.2` minutes/month downtime budget) or `99.95%` (`21.6` minutes/month).
- **Error Budget Policy:**
  - Remaining budget $> 20\%$: Normal feature velocity.
  - Budget burned $> 50\%$ mid-window or multi-window burn rate $> 14.4\times$: Freeze non-essential feature deploys; prioritize reliability fixes and rollback recent changes.

### Multi-Window, Multi-Burn-Rate Alerting (Google SRE Standard)
Avoid paging on single-point spikes or slow-burn noise. Page only when budget burn threatens the 30-day SLO:

| Severity | Short Window | Long Window | Burn Rate | 30-Day Budget Consumed | Action |
|---|---|---|---|---|---|
| **Page (SEV1/2)** | `5m` | `1h` | `14.4x` | `2%` in 1h | Immediate page |
| **Page (SEV2)** | `30m` | `6h` | `6.0x` | `5%` in 6h | Immediate page |
| **Ticket (SEV3)** | `6h` | `3d` | `1.0x` | `10%` in 3d | Create ticket / Slack alert |

---

## 2. Incident Command System (ICS) & Severity Matrix

| Severity | Impact | Response Target | Roles Needed |
|---|---|---|---|
| **SEV1 (Critical)** | Full outage, data loss risk, or active security breach | Immediate (`< 5m`), 24/7 | Incident Commander (IC), Ops Lead, Comms Lead |
| **SEV2 (High)** | Major feature degraded or regional/tier-1 customer impact | `< 15m` | IC + Service Owner |
| **SEV3 (Medium)** | Partial degradation with workaround; slow error budget burn | Next business hour | On-call Engineer |
| **SEV4 (Low)** | Minor cosmetic/non-customer-facing defect | Planned sprint | Ticket owner |

### Triage Priorities During Active Incidents
1. **Mitigate First, Root-Cause Second:** Roll back the last deployment, shift traffic away from an unhealthy zone, scale out, or shed non-critical load before deep-diving into code.
2. **Preserve Forensic Evidence:** Before restarting a wedged process, capture thread/heap dumps (`jcmd`/`dotnet-dump`/`gcore`) or copy volatile logs if safe to do so.
3. **Time-Boxed Hypotheses:** Never spend > 15 minutes on an unverified theory without checking metrics/logs; rotate hypotheses or escalate.

---

## 3. Blameless Postmortem Template

1. **Summary & Impact:** Duration, affected SLOs, % error budget consumed, user-facing symptoms.
2. **Timeline (UTC):** Detection $\to$ Triage $\to$ Mitigation $\to$ Full Recovery.
3. **Root Cause & Contributing Factors:** Technical chain of events (5 Whys), avoiding *"human error"* as a terminal cause—ask *why* the system allowed a single human action to cause an outage.
4. **What Went Well / What Got Lucky:** Observability wins and hidden fragility exposed.
5. **Action Items (Prevent, Detect, Mitigate):** Each with an owner, priority, and due date (e.g., automated canary rollback, circuit breaker, pre-commit guardrail).

---

## 4. Chaos Engineering, GameDays & Toil Cap

- **Automated Failure Injection:** Run continuous chaos experiments (e.g., node termination, CPU/memory pressure, DB latency, packet loss) in staging/canary environments to verify SLO burn-rate alerts fire *before* users notice and automated failovers trigger cleanly.
- **GameDays:** Schedule periodic cross-functional drills simulating zone outages or dependency brownouts to validate runbooks and incident-command muscle memory.
- **Toil Automation:** Cap repetitive manual operational toil at `< 50%` of engineering time; convert recurring manual mitigations into idempotent scripts, GitOps rollbacks, or self-healing automation.
