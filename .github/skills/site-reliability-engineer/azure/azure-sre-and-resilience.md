# Microsoft Azure SRE & Cloud Resilience

## 1. Azure Monitor & Log Analytics (KQL Triage)

Use KQL against Application Insights (`AppRequests`, `AppExceptions`, `AppDependencies`) and AKS/Container logs (`ContainerLogV2`, `AzureDiagnostics`):

```kusto
// 1. Top failing endpoints & 5xx spike timeline (5m bins)
AppRequests
| where TimeGenerated > ago(2h)
| summarize Total=count(), Failures=countif(Success == false or toint(ResultCode) >= 500),
            P95Ms=percentile(DurationMs, 95) by bin(TimeGenerated, 5m), OperationName
| extend ErrorRate = round(100.0 * Failures / Total, 2)
| where ErrorRate > 1.0 or P95Ms > 1000
| order by TimeGenerated desc

// 2. Downstream dependency bottlenecks & throttling (429 / 503)
AppDependencies
| where TimeGenerated > ago(1h) and (Success == false or toint(ResultCode) in (429, 503, 504))
| summarize Count=count(), P95Ms=percentile(DurationMs, 95) by DependencyType, Target, ResultCode
| order by Count desc

// 3. AKS Pod CrashLoopBackOff & OOMKilled spikes (Container Insights)
KubePodInventory
| where TimeGenerated > ago(1h)
| summarize arg_max(TimeGenerated, *) by Computer, Namespace, Name
| where PodStatus == "Failed" or ContainerStatusReason in ("OOMKilled", "CrashLoopBackOff")
| project TimeGenerated, Namespace, Name, ContainerStatusReason, ControllerName
```

---

## 2. Common Azure Production Failure Modes & Mitigations

| Service | Failure Mode | Root Cause | SRE Remediation |
|---|---|---|---|
| **App Service / Functions** | `SocketException` / outbound timeouts under load | **SNAT port exhaustion** (128 ports/instance default) | Reuse `HttpClient` (`IHttpClientFactory` / singleton `Agent`), deploy **NAT Gateway** on VNet integration |
| **App Service** | Slow cold starts or worker recycle drops | Idle timeout / memory limit / overlapping recycle | Enable `Always On`, configure **Health Check** path, scale out with zone redundancy |
| **AKS (Kubernetes)** | `ImagePullBackOff` or `401` on ACR | Expired SP/MI token or missing `AcrPull` role | Attach Managed Identity `AcrPull` RBAC; verify private endpoint DNS (`privatelink.azurecr.io`) |
| **AKS** | Cross-AZ latency or node pool exhaustion | Single-zone node pool or subnet IP exhaustion | Spread node pools across **Zones 1, 2, 3**; size CNI subnet CIDRs for max pods $\times$ nodes |
| **Azure SQL** | `Error 40613` / `10928` / DTU 100% | Transient failover or query plan regression | Use **retry with exponential backoff + jitter**; inspect Query Store (`sys.query_store_runtime_stats`) |
| **Cosmos DB** | `429 TooManyRequests` | Hot partition key or insufficient RU/s | Enable **Autoscale RU/s**; fix partition key cardinality; honor `x-ms-retry-after-ms` |
| **Key Vault** | `429` or `403 Forbidden` | Burst secret fetches on startup or RBAC drift | Cache secrets in memory with TTL; use **Managed Identity** + Azure RBAC (`Key Vault Secrets User`) |

---

## 3. Azure CLI (`az`) Read-Only Incident Triage

```bash
# Check active Azure Service Health / Resource Health events
az resource list --query "[].{Name:name,Type:type,RG:resourceGroup}" -o table
az monitor activity-log list --resource-group <rg> --offset 2h --status Failed -o table

# AKS cluster & node pool health
az aks show -g <rg> -n <cluster> --query "{PowerState:powerState.code,Provisioning:provisioningState,Version:kubernetesVersion}"
az aks nodepool list -g <rg> --cluster-name <cluster> -o table

# App Service metrics & recent deployment slots
az webapp show -g <rg> -n <app> --query "{State:state,Availability:availabilityState,HttpsOnly:httpsOnly}"
az webapp deployment slot list -g <rg> -n <app> -o table
```

- **Zero-Downtime Mitigation:** Use **App Service Deployment Slots** (`swap`) or **Azure Front Door / Traffic Manager** weighted routing to shift traffic off a degraded region or slot before debugging.
- **Multi-Region AKS & Managed Observability:** Orchestrate multi-cluster/multi-region AKS rollouts with **Azure Kubernetes Fleet Manager**, and centralize cluster metrics in **Azure Monitor Managed Service for Prometheus** + **Azure Managed Grafana**.
- **Proactive Fault Validation (Azure Chaos Studio):** Run Chaos Studio experiments (VMSS zone-down simulation, network latency/packet drops to Azure SQL/Service Bus, or Chaos Mesh pod faults in AKS) in staging/canary pipelines to verify timeouts, retries, and HPA/PDB behavior before incidents.
