---
name: auto-ontology
description: Build and check NVIDIA Auto Ontology maps. Use when asked to "set up Auto Ontology", "build a semantic layer", "validate a metric mapping", or "check text-to-SQL". Not for schema design.
version: 1.1.0
---

# NVIDIA Auto Ontology

## Choose The Starting Point

| Inputs available | Action |
| --- | --- |
| Running Auto Ontology and an approved read-only source | Confirm the deployment version and connector, then generate a scoped draft. |
| Only an approved schema export, glossary, or report SQL | Draft the map from those artifacts. Run the offline validator once table and column metadata is available. Do not claim NVIDIA ingestion or certification. |
| No approved business definition or baseline | Identify the data owner and list unresolved decisions. Do not invent formulas from column names. |

## Offline Mapping Check

1. Make a JSON bundle using [the net-revenue fixture](assets/net-revenue.json) as the template. Supply a `schema` object mapping exact table names to column lists, and a `metric` object with `name`, `owner`, `grain`, `calculation`, `columns`, and `joins`. Use `table.column` references (or `schema.table.column` for qualified tables); list join endpoints as `left` and `right`, and declare cardinality from left to right. Use `[]` for `joins` on a single-table metric.
2. Run [the validator](scripts/validate-mapping.py) from the repository root. First run the sample, then replace the last argument with the prepared bundle.

   ```powershell
   .\.venv\Scripts\python.exe .github/skills/auto-ontology/scripts/validate-mapping.py .github/skills/auto-ontology/assets/net-revenue.json
   ```

   On Linux/macOS, use `.venv/bin/python`. For a reusable report, redirect stdout to a new file such as `ontology-validation.json`.
3. Read the report: `metric`, `status`, `errors`, and `human_review`. Exit `0` means the structural checks passed; `1` means the report has validation errors; `2` means the input could not be read as a JSON object or the invocation was invalid. The sample should pass and flag its one-to-many join for fan-out review.

This is a local input format, not a NVIDIA import format. The check does not connect to a database, execute SQL, verify actual cardinality, or certify a definition. Keep the mapping draft until real-data reconciliation and owner approval are recorded.

## Local Quickstart

Use the [upstream quickstart](https://github.com/NVIDIA/auto-ontology#quickstart) matching the checkout. For a new local Compose deployment, confirm Docker Compose v2 is available and run from the root of the NVIDIA checkout. Copy the environment template only if `.env` does not already exist, then fill in the model endpoint credentials, app credentials, and approved source configuration described by that checkout. Keep credentials out of the repo and agent output.

```powershell
if (-not (Test-Path -LiteralPath .env)) {
    Copy-Item -LiteralPath .env.example -Destination .env
}
# Configure .env before starting the services.
docker compose config --services
docker compose up -d --wait postgres
docker compose up -d --build
docker compose ps
```

Use the frontend URL from the deployment configuration. Confirm that the app opens and that the approved source can be inspected before starting ingestion. For Kubernetes, use the [NVIDIA deployment overview](https://catalog.ngc.nvidia.com/orgs/nvidia/-/helm-charts/auto-ontology/-). Do not guess connector support, UI labels, API paths, or CLI flags; verify them for the installed release. Before enabling profiling or a hosted model, check whether schema names, sample values, or query history may leave the environment.

## Generate And Certify

1. **Scope one question.** Record the expected metric, reporting grain (what one output row represents), approved tables or views, owner, and known-good report or query. Start with existing business definitions and exclude unrelated schemas.
2. **Generate the draft.** Use the ingestion and generation workflow for the installed release. Inspect the draft for business terms and aliases, table and column mappings, join conditions, and proposed SQL expressions. Distinguish declared keys from inferred relationships and mark assumptions that need confirmation.
3. **Check how rows join.** Write down the grain of each source and the expected cardinality. Test whether combining them drops unmatched rows or multiplies amounts. Aggregate child rows to the parent grain before combining amounts when the business definition requires it.
4. **Reconcile the generated answer.** Capture the generated SQL. Compare the result with the approved baseline using identical dates, time zone, filters, and grain. Compare at least one breakdown as well as the total so offsetting errors cannot hide. Check a boundary case and an ambiguous question. On ambiguous terms, ask for clarification instead of guessing.
5. **Publish only after approval.** Record the owner, reviewed definition, evidence, and limitations. Expose certified terms over the supported MCP, API, or CLI surface, and verify the agent returns the intended definition and respects source permissions. Re-run the checks when mappings or business rules change.

## Worked Example: Net Revenue

For this synthetic pilot only, assume an approved policy of order subtotal before tax minus completed refunds, with refunds attributed back to the order's fiscal quarter.

| Map entry | Example |
| --- | --- |
| `Order` | `orders.order_id`, one row per order; `booked_at` determines fiscal quarter |
| `Refund` | `refunds.refund_id`, one row per refund; link `refunds.order_id` to `orders.order_id` (many refunds to one order) |
| `Net revenue` | Sum order subtotal less completed refunds aggregated by order. Keep orders with no refunds and treat their refund total as zero. |
| Ground truth | Order A: subtotal 100, completed refunds 10 and 15; order B: subtotal 50, no refunds. Expected per-order values: 75 and 50. Expected total: 125. |
| Regression checks | A direct join can incorrectly count order A's subtotal twice. A pending refund must not change the total. A refund paid in the next quarter still applies to the order's quarter under this example policy. |

Ask the real owner to confirm tax treatment, refund status and attribution, currency, and the fiscal calendar before applying these rules to production.

## Handoff

For each metric, return the name and aliases, owner and definition source, tables and columns, grain and joins, calculation and filters, date semantics, and reconciliation evidence. Use `draft`, `validated`, or `owner-approved` as handoff labels, not assumed product states. List unresolved rules and checks you could not run.
