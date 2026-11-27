"""Render bounded stage handoffs and final reports without changing pipeline state."""

import sqlite3
from contextlib import closing
from pathlib import Path


def emit_handoff(stage, manifest, stages, specs, active_slice):
    spec = specs[stage]
    print(f"# Stage handoff: {stage}")
    print(f"Task: {manifest['task']}")
    for key in ("subagent_role", "primary_skill", "description", "memory_load", "memory_save"):
        print(f"{key}: {spec[key]}")
    print(f"Supporting skills: {', '.join(spec['supporting_skills'])}")
    if stage == "plan" and manifest.get("is_major_change"):
        print("Major change: run llm-as-judge four-archetype arbitration before development.")
    if active_slice:
        print(f"Active BDD slice: {active_slice['name']} ({active_slice['index'] + 1}/{active_slice['total']})")
        print("Scope implementation and verification to this slice; full regression on the final slice.")
    print("Upstream evidence:")
    for previous in stages[:stages.index(stage)]:
        data = manifest["stages"][previous]
        print(f"- {previous}: {data['status']} — {data.get('summary')}")
        for artifact in data.get("artifacts", []):
            print(f"  Artifact: {artifact}")
    print("Read the run's plan.md and checklist.md. Keep this stage scoped.")
    print("Record PASSED only with summary, learnings and existing artifact evidence.")
    if stage in ("develop", "codereview", "architecturechecks"):
        print("Supply --source-file for each changed source; physical line and byte limits apply.")


def count_pending_learnings():
    db_path = Path(".project-memory/memory.db")
    if not db_path.exists():
        return None
    with closing(sqlite3.connect(str(db_path))) as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(memories)")}
        if not columns:
            return 0
        query = (
            "SELECT COUNT(*) FROM memories WHERE category IN ('journal', 'ledger') AND skill_status = 'pending'"
            if "skill_status" in columns
            else "SELECT COUNT(*) FROM memories WHERE category IN ('journal', 'ledger')"
        )
        return conn.execute(query).fetchone()[0]


def emit_report(run_dir, manifest, stages, specs):
    lines = [
        f"# Agent Orchestrator Execution Report: {manifest['run_id']}",
        f"Task: {manifest['task']}",
        f"Date: {manifest.get('created_at', 'Unknown')}",
        f"Overall status: {manifest.get('status', 'IN_PROGRESS')}",
        "",
        "| Stage | Status | Skill | Summary |",
        "| --- | --- | --- | --- |",
    ]
    clean = lambda value: str(value or "").replace("\n", " ").replace("|", "\\|")
    for stage in stages:
        data = manifest["stages"].get(stage, {})
        lines.append(f"| {stage} | {data.get('status', 'PENDING')} | "
                     f"{clean(specs[stage]['primary_skill'])} | {clean(data.get('summary'))} |")
        for artifact in data.get("artifacts", []):
            lines.append(f"\n{stage} artifact: {artifact}")
    slices = manifest.get("bdd_slices", {}).get("items", [])
    if slices:
        lines.extend(["", "## BDD slices", ""])
        lines.extend(f"- {item['name']}: {item['status']}" for item in slices)
    pending = count_pending_learnings()
    if pending is not None:
        lines.extend(["", f"Pending learnings: {pending}. "
                      "Promote reusable learnings immediately; reconcile pending entries before delivery."])
    report = "\n".join(lines) + "\n"
    report_file = run_dir / "summary-report.md"
    report_file.write_text(report, encoding="utf-8")
    print(report)
    print(f"Report written to: {report_file}")
