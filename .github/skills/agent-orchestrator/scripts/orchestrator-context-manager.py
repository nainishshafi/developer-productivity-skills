#!/usr/bin/env python3
r"""
orchestrator-context-manager.py — Pipeline state, memory, and over-engineering audit manager for agent-orchestrator.

Manages execution state, stage artifacts, memory tracking (save-memory / load-memory),
and in-the-loop over-engineering detection across the 7 SDLC stages:
1. plan
2. develop
3. codereview
4. complexitychecks
5. architecturechecks
6. halucinationchecks
7. securitychecks

Usage:
    .\.venv\Scripts\python.exe .github/skills/agent-orchestrator/scripts/orchestrator-context-manager.py init --task "Feature name or description"
    .\.venv\Scripts\python.exe .github/skills/agent-orchestrator/scripts/orchestrator-context-manager.py status [--run-id <id>]
    .\.venv\Scripts\python.exe .github/skills/agent-orchestrator/scripts/orchestrator-context-manager.py handoff --stage <stage> [--run-id <id>]
    .\.venv\Scripts\python.exe .github/skills/agent-orchestrator/scripts/orchestrator-context-manager.py record --stage <stage> --status <PASSED|FAILED|BLOCKED|SKIPPED> --summary "Notes" [--run-id <id>]
    .\.venv\Scripts\python.exe .github/skills/agent-orchestrator/scripts/orchestrator-context-manager.py check-overengineering [--file <path> | --dir <dir> | --all] [--max-score <0-100>]
    .\.venv\Scripts\python.exe .github/skills/agent-orchestrator/scripts/orchestrator-context-manager.py report [--run-id <id>]
"""

import argparse
import datetime
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

STAGES = [
    "plan",
    "develop",
    "codereview",
    "complexitychecks",
    "architecturechecks",
    "halucinationchecks",
    "securitychecks",
]

STAGE_SKILLS_MAP = {
    "plan": {
        "primary_skill": "architectural-planning",
        "supporting_skills": ["scan-repo-readme", "trace-code-context", "load-memory", "save-memory", "researcher-poc-tester", "rag-pipeline", "llm-as-judge", "api-security", "caching-queues-reviewer", "sql-executor"],
        "subagent_role": "Architecture & Planning Specialist",
        "description": "System design, empirical PoC benchmarking, requirements breakdown, component boundaries, and contract definition.",
        "memory_load": "load_memory(category='ledger') for architecture truths; load_memory(category='journal') for design traps.",
        "memory_save": "save_memory(category='ledger') for ADRs/contracts; save_memory(category='journal') for plan learnings.",
    },
    "develop": {
        "primary_skill": "python-developer / typescript-developer / react-developer / java-developer / csharp-developer / python-api-writer / powershell-writer",
        "supporting_skills": ["rag-pipeline", "detect-overengineering", "load-memory", "save-memory", "troubleshoot-and-fix", "remote-pod-log-analyzer", "legacy-code-modernization", "test-data-creator", "sql-connector", "nodejs-executor", "skill-creator", "sync-github-forks"],
        "subagent_role": "Core Implementation & Test Engineer",
        "description": "Production code authoring, synthetic testbed seeding, automated unit/integration tests, legacy code modernization, and embedded over-engineering checks in the loop.",
        "memory_load": "load_memory(category='ledger') for plan contracts; load_memory(category='sidecar') for active WIP; search_memory for domain traps.",
        "memory_save": "save_memory(category='sidecar') for WIP state & touched files; save_memory(category='journal') for implementation lessons.",
    },
    "codereview": {
        "primary_skill": "code-reviewer",
        "supporting_skills": ["detect-overengineering", "python-linter", "design-pattern-detector", "caching-queues-reviewer", "react-developer", "load-memory", "save-memory"],
        "subagent_role": "Senior Code Reviewer",
        "description": "Code quality, readability, style conformance, idiomatic usage, error handling, and in-the-loop over-engineering detection.",
        "memory_load": "load_memory(category='sidecar') for WIP context; search_memory for past review patterns and missed bugs.",
        "memory_save": "save_memory(category='journal') for review findings and traps detected.",
    },
    "complexitychecks": {
        "primary_skill": "algorithmic-complexity-analyzer",
        "supporting_skills": ["trace-code-context", "sql-executor", "sql-connector", "nodejs-executor", "researcher-poc-tester", "load-memory", "save-memory"],
        "subagent_role": "Algorithmic Complexity & Performance Auditor",
        "description": "Asymptotic Big-O time and space complexity analysis, empirical doubling benchmarks, hidden quadratic loop detection, and SQL query execution plan audits.",
        "memory_load": "search_memory for known performance bottlenecks, full table scans, or quadratic loop patterns.",
        "memory_save": "save_memory(category='journal') for complexity fixes and asymptotic efficiency learnings.",
    },
    "architecturechecks": {
        "primary_skill": "detect-overengineering",
        "supporting_skills": ["detect-overengineering", "design-pattern-detector", "trace-code-context", "load-memory", "save-memory"],
        "subagent_role": "Principal Architecture Auditor",
        "description": "Structural analysis, detection of premature abstractions (YAGNI), layer bloat, anti-patterns, and dependency call-graphs.",
        "memory_load": "load_memory(category='ledger') for architecture rules; search_memory for past over-engineering traps.",
        "memory_save": "save_memory(category='ledger') for approved structural conventions; save_memory(category='journal') for YAGNI lessons.",
    },
    "halucinationchecks": {
        "primary_skill": "scan-halucinated-tests",
        "supporting_skills": ["trace-code-context", "playwright-bdd-tester", "rag-pipeline", "llm-as-judge", "load-memory", "save-memory"],
        "subagent_role": "Ground-Truth Verification Auditor",
        "description": "Verification of test symbols, non-existent imports, E2E BDD Playwright flows, RAG 5-layer evaluation, and fabricated APIs against ground-truth source code.",
        "memory_load": "load_memory(category='ledger') for verified API contracts; search_memory for mock drift lessons.",
        "memory_save": "save_memory(category='journal') for hallucinated test corrections and ground-truth verification learnings.",
    },
    "securitychecks": {
        "primary_skill": "github-security-scanner-hook",
        "supporting_skills": ["semgrep", "detect-secrets", "api-security", "sql-connector", "load-memory", "save-memory"],
        "subagent_role": "Application Security Auditor",
        "description": "Secrets scanning, API key leakage detection, OWASP vulnerability audit (injections, traversal, shell execution), and secure defaults.",
        "memory_load": "load_memory(category='ledger') for security invariants & token rules; search_memory for OWASP patterns.",
        "memory_save": "save_memory(category='ledger') for permanent security rules; save_memory(category='journal') for vulnerabilities prevented.",
    },
}

BASE_DIR = Path(".orchestrator")
RUNS_DIR = BASE_DIR / "runs"


def slugify(text: str) -> str:
    cleaned = re.sub(r"[^\w\s-]", "", text.lower()).strip()
    return re.sub(r"[-\s]+", "-", cleaned)[:40] or "task"


def get_latest_run_id() -> Optional[str]:
    if not RUNS_DIR.exists():
        return None
    runs = [d for d in RUNS_DIR.iterdir() if d.is_dir() and (d / "manifest.json").exists()]
    if not runs:
        return None
    runs.sort(key=lambda d: d.stat().st_mtime, reverse=True)
    return runs[0].name


def get_run_dir(run_id: Optional[str] = None) -> Path:
    if run_id:
        target = RUNS_DIR / run_id
        if not target.exists():
            print(f"Error: Run ID '{run_id}' not found in {RUNS_DIR}", file=sys.stderr)
            sys.exit(1)
        return target
    latest = get_latest_run_id()
    if not latest:
        print("Error: No existing orchestrator runs found. Run 'init' first.", file=sys.stderr)
        sys.exit(1)
    return RUNS_DIR / latest


def load_manifest(run_dir: Path) -> Dict[str, Any]:
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.exists():
        print(f"Error: Manifest not found at {manifest_path}", file=sys.stderr)
        sys.exit(1)
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_manifest(run_dir: Path, data: Dict[str, Any]) -> None:
    manifest_path = run_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def cmd_init(args: argparse.Namespace) -> None:
    now = datetime.datetime.now()
    timestamp = now.strftime("%Y%m%d-%H%M%S")
    slug = slugify(args.task)
    run_id = f"{timestamp}-{slug}"
    run_dir = RUNS_DIR / run_id

    run_dir.mkdir(parents=True, exist_ok=True)
    for stage in STAGES:
        (run_dir / "stages" / stage).mkdir(parents=True, exist_ok=True)

    manifest: Dict[str, Any] = {
        "run_id": run_id,
        "task": args.task,
        "created_at": now.isoformat(),
        "status": "IN_PROGRESS",
        "current_stage": "plan",
        "stages": {
            stage: {
                "status": "PENDING",
                "assigned_skill": STAGE_SKILLS_MAP[stage]["primary_skill"],
                "subagent_role": STAGE_SKILLS_MAP[stage]["subagent_role"],
                "started_at": None,
                "completed_at": None,
                "summary": None,
                "artifacts": [],
            }
            for stage in STAGES
        },
    }

    save_manifest(run_dir, manifest)
    print(f"Initialized orchestrator run: {run_id}")
    print(f"Directory: {run_dir}")
    print(f"Initial stage: plan")


def cmd_status(args: argparse.Namespace) -> None:
    run_dir = get_run_dir(args.run_id)
    manifest = load_manifest(run_dir)

    print("=" * 70)
    print(f"ORCHESTRATOR RUN: {manifest['run_id']}")
    print(f"Task: {manifest['task']}")
    print(f"Overall Status: {manifest['status']} | Current Stage: {manifest.get('current_stage', 'done')}")
    print("=" * 70)
    print(f"{'Stage':<22} | {'Status':<12} | {'Skill / Tool':<28}")
    print("-" * 70)

    for stage in STAGES:
        s_info = manifest["stages"].get(stage, {})
        status = s_info.get("status", "PENDING")
        skill = s_info.get("assigned_skill", STAGE_SKILLS_MAP[stage]["primary_skill"])
        print(f"{stage:<22} | {status:<12} | {skill:<28}")

    print("=" * 70)


def cmd_handoff(args: argparse.Namespace) -> None:
    stage = args.stage.lower()
    if stage not in STAGES:
        print(f"Error: Invalid stage '{stage}'. Must be one of: {', '.join(STAGES)}", file=sys.stderr)
        sys.exit(1)

    run_dir = get_run_dir(args.run_id)
    manifest = load_manifest(run_dir)
    stage_idx = STAGES.index(stage)

    # Collect previous stages context
    previous_context: List[Dict[str, Any]] = []
    for prev in STAGES[:stage_idx]:
        prev_data = manifest["stages"].get(prev, {})
        previous_context.append({
            "stage": prev,
            "status": prev_data.get("status"),
            "summary": prev_data.get("summary"),
            "artifacts": prev_data.get("artifacts", []),
        })

    stage_spec = STAGE_SKILLS_MAP[stage]

    # Output context markdown suitable for passing directly into subagent prompt
    print("# " + "=" * 60)
    print(f"# SUBAGENT HANDOFF PAYLOAD: STAGE [{stage.upper()}]")
    print("# " + "=" * 60)
    print(f"**Target Stage:** `{stage}`")
    print(f"**Assigned Sub-Agent Role:** `{stage_spec['subagent_role']}`")
    print(f"**Primary Skill to Execute:** `{stage_spec['primary_skill']}`")
    print(f"**Supporting Skills:** `{', '.join(stage_spec['supporting_skills'])}`")
    print(f"**Goal:** {stage_spec['description']}")
    print("\n## Task Objective")
    print(f"{manifest['task']}")

    print("\n## Upstream Pipeline Context & Findings")
    if not previous_context:
        print("_This is the first stage in the pipeline (no upstream stages)._")
    else:
        for prev in previous_context:
            print(f"- **Stage `{prev['stage']}`** [{prev['status']}]: {prev['summary'] or 'No summary recorded.'}")
            if prev["artifacts"]:
                for art in prev["artifacts"]:
                    print(f"    - Artifact: `{art}`")

    print("\n## Stage Instructions for Sub-Agent")
    print(f"1. Activate skill: `{stage_spec['primary_skill']}`.")
    print("2. Focus strictly on this stage's scope. Do not regress upstream stage decisions.")
    print("3. Write stage findings and generated files into the workspace.")
    print(f"4. Record results with: python orchestrator-context-manager.py record --stage {stage} --status PASSED --summary \"<findings>\"")
    print("# " + "=" * 60)


def cmd_record(args: argparse.Namespace) -> None:
    stage = args.stage.lower()
    if stage not in STAGES:
        print(f"Error: Invalid stage '{stage}'. Must be one of: {', '.join(STAGES)}", file=sys.stderr)
        sys.exit(1)

    status = args.status.upper()
    valid_statuses = ["PASSED", "FAILED", "BLOCKED", "SKIPPED"]
    if status not in valid_statuses:
        print(f"Error: Invalid status '{status}'. Must be one of: {', '.join(valid_statuses)}", file=sys.stderr)
        sys.exit(1)

    run_dir = get_run_dir(args.run_id)
    manifest = load_manifest(run_dir)

    now_iso = datetime.datetime.now().isoformat()
    stage_data = manifest["stages"].setdefault(stage, {})
    stage_data["status"] = status
    stage_data["completed_at"] = now_iso
    stage_data["summary"] = args.summary or ""

    if args.artifact:
        artifacts = stage_data.setdefault("artifacts", [])
        if args.artifact not in artifacts:
            artifacts.append(args.artifact)

    # Determine next stage
    stage_idx = STAGES.index(stage)
    if status == "PASSED" or status == "SKIPPED":
        if stage_idx + 1 < len(STAGES):
            manifest["current_stage"] = STAGES[stage_idx + 1]
            manifest["stages"][manifest["current_stage"]]["status"] = "READY"
        else:
            manifest["current_stage"] = "COMPLETED"
            manifest["status"] = "PASSED"
    elif status in ["FAILED", "BLOCKED"]:
        manifest["status"] = f"STOPPED_AT_{stage.upper()}"

    save_manifest(run_dir, manifest)
    print(f"Successfully recorded stage '{stage}' as {status}.")
    if manifest["current_stage"] != "COMPLETED":
        print(f"Next stage in pipeline: {manifest['current_stage']}")
    else:
        print("All pipeline stages completed successfully!")


def cmd_report(args: argparse.Namespace) -> None:
    run_dir = get_run_dir(args.run_id)
    manifest = load_manifest(run_dir)

    report_lines = [
        f"# Agent Orchestrator Execution Report: {manifest['run_id']}",
        f"\n**Task:** {manifest['task']}",
        f"**Date:** {manifest.get('created_at', 'Unknown')}",
        f"**Overall Status:** `{manifest.get('status', 'IN_PROGRESS')}`",
        "\n---",
        "\n## Stage Verification Summary\n",
        "| Stage | Status | Assigned Skill | Sub-Agent Role | Summary |",
        "|---|---|---|---|---|",
    ]

    for stage in STAGES:
        s = manifest["stages"].get(stage, {})
        status = s.get("status", "PENDING")
        skill = s.get("assigned_skill", STAGE_SKILLS_MAP[stage]["primary_skill"])
        role = s.get("subagent_role", STAGE_SKILLS_MAP[stage]["subagent_role"])
        summary = (s.get("summary") or "").replace("\n", " ").strip()
        report_lines.append(f"| `{stage}` | **{status}** | `{skill}` | {role} | {summary} |")

    report_lines.append("\n## Stage Artifacts & Deliverables\n")
    has_artifacts = False
    for stage in STAGES:
        s = manifest["stages"].get(stage, {})
        artifacts = s.get("artifacts", [])
        if artifacts:
            has_artifacts = True
            report_lines.append(f"### Stage: `{stage}`")
            for art in artifacts:
                report_lines.append(f"- `{art}`")
    if not has_artifacts:
        report_lines.append("_No discrete file artifacts registered in manifest._")

    report_content = "\n".join(report_lines) + "\n"
    report_file = run_dir / "summary-report.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report_content)

    print(report_content)
    print(f"Report written to: {report_file}")


def cmd_check_overengineering(args: argparse.Namespace) -> None:
    extract_script = Path(".github/skills/detect-overengineering/scripts/extract-signals.py")
    if not extract_script.exists():
        print(f"Error: extract-signals.py not found at {extract_script}", file=sys.stderr)
        sys.exit(1)

    cmd = [sys.executable, str(extract_script)]
    if args.file:
        cmd.append(args.file)
    elif args.dir:
        cmd.extend(["--dir", args.dir])
    elif args.all:
        cmd.append("--all")
    else:
        print("Error: Specify --file <path>, --dir <dir>, or --all", file=sys.stderr)
        sys.exit(1)

    if args.force:
        cmd.append("--force")

    import subprocess
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Extraction failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(result.returncode)

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(result.stdout)
        return

    max_allowed = args.max_score
    if isinstance(data, dict) and "files" in data:
        items = data["files"]
    elif isinstance(data, list):
        items = data
    else:
        items = [data]

    failed = []
    print("=" * 70)
    print("OVER-ENGINEERING IN-THE-LOOP AUDIT")
    print(f"Max Allowed Risk Score: {max_allowed}/100")
    print("=" * 70)
    for item in items:
        score = item.get("overengineering_score", 0)
        severity = item.get("severity", "clean")
        src = item.get("source_path", "unknown")
        smells = item.get("smells", [])
        status = "PASSED" if score < max_allowed else "FAILED"
        print(f"[{status}] {src:<50} | Score: {score:>3}/100 | Severity: {severity}")
        if score >= max_allowed:
            failed.append(item)
            for smell in smells:
                print(f"   ⚠️  Line {smell.get('line', '?')}: {smell.get('name', 'Smell')} — {smell.get('description', '')}")

    print("=" * 70)
    if failed:
        print(f"❌ Over-engineering gate FAILED: {len(failed)} file(s) exceed score threshold ({max_allowed}).")
        print("Remediation Loop required: Simplify abstractions, eliminate 1:1 interfaces, or inline trampoline methods.")
        sys.exit(1)
    else:
        print(f"✅ Over-engineering gate PASSED: All files within threshold (< {max_allowed}).")


def main() -> None:
    parser = argparse.ArgumentParser(description="Agent Orchestrator Pipeline & Context Manager")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # init
    p_init = subparsers.add_parser("init", help="Initialize a new orchestrator run")
    p_init.add_argument("--task", required=True, help="Task description or objective")

    # status
    p_status = subparsers.add_parser("status", help="Show pipeline status")
    p_status.add_argument("--run-id", help="Optional run ID (defaults to latest)")

    # handoff
    p_handoff = subparsers.add_parser("handoff", help="Package context for subagent handoff")
    p_handoff.add_argument("--stage", required=True, help="Target stage to handoff to")
    p_handoff.add_argument("--run-id", help="Optional run ID (defaults to latest)")

    # record
    p_record = subparsers.add_parser("record", help="Record completion of a stage")
    p_record.add_argument("--stage", required=True, help="Stage completed")
    p_record.add_argument("--status", required=True, choices=["PASSED", "FAILED", "BLOCKED", "SKIPPED"])
    p_record.add_argument("--summary", help="Summary of findings or results")
    p_record.add_argument("--artifact", help="Path to primary artifact generated")
    p_record.add_argument("--run-id", help="Optional run ID (defaults to latest)")

    # report
    p_report = subparsers.add_parser("report", help="Generate full markdown report")
    p_report.add_argument("--run-id", help="Optional run ID (defaults to latest)")

    # check-overengineering
    p_check_oe = subparsers.add_parser("check-overengineering", help="Audit files for over-engineering and accidental complexity in the loop")
    p_check_oe.add_argument("--file", help="Path to single source file to audit")
    p_check_oe.add_argument("--dir", help="Directory of source files to audit")
    p_check_oe.add_argument("--all", action="store_true", help="Analyze all source files in repository")
    p_check_oe.add_argument("--max-score", type=int, default=40, help="Maximum allowable over-engineering score (default: 40)")
    p_check_oe.add_argument("--force", action="store_true", help="Force re-analysis even if cached report is up to date")

    args = parser.parse_args()

    if args.subcommand == "init":
        cmd_init(args)
    elif args.subcommand == "status":
        cmd_status(args)
    elif args.subcommand == "handoff":
        cmd_handoff(args)
    elif args.subcommand == "record":
        cmd_record(args)
    elif args.subcommand == "check-overengineering":
        cmd_check_overengineering(args)
    elif args.subcommand == "report":
        cmd_report(args)


if __name__ == "__main__":
    main()

