# Auto Ontology

Use this skill to build a semantic layer that connects business metrics to database tables, columns, and joins. You can check a mapping offline before using it in a live NVIDIA Auto Ontology deployment.

## Run the Offline Example

From the repository root, run the validator against the [net-revenue fixture](assets/net-revenue.json). It uses the Python standard library and does not require Docker, a database connection, or NVIDIA credentials.

```powershell
.\.venv\Scripts\python.exe .github/skills/auto-ontology/scripts/validate-mapping.py .github/skills/auto-ontology/assets/net-revenue.json
```

On Linux or macOS, use `.venv/bin/python` in place of `.\.venv\Scripts\python.exe`.

The JSON report should show `"status": "pass"` and no structural errors. It should also flag the one-to-many orders-to-refunds join under `human_review`: joining refund rows directly can count the same order subtotal more than once.

| Exit code | Meaning |
| --- | --- |
| `0` | Structural checks passed against the supplied metadata. |
| `1` | The mapping has structural errors. See `errors` in the JSON report. |
| `2` | The input could not be read as a JSON object, or the invocation was invalid. |

## Check Your Own Mapping

Use the fixture as a template. Replace the schema and metric with approved metadata and your proposed mapping, then pass that JSON file to [the validator](scripts/validate-mapping.py). Join cardinality is declared from `left` to `right`.

A pass does not verify actual join cardinality, validate the business formula, or certify the metric. The validator does not execute SQL, and its JSON input is not a NVIDIA import format. Before publishing, reconcile totals and breakdowns against an approved report using the same grain, dates, and filters, then obtain data-owner approval.

See [SKILL.md](SKILL.md) for the deployment and certification workflow.
