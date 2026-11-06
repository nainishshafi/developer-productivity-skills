#!/usr/bin/env python3
"""
orchestrator-context-manager.py — Pipeline state and context handoff manager for agent-orchestrator.

Manages execution state, stage artifacts, and context packaging across the 6 SDLC stages:
1. plan
2. develop
3. codereview
4. architecturechecks
5. halucinationchecks
6. securitychecks

Usage:
    python orchestrator-context-manager.py init --task "Feature name or description"
    python orchestrator-context-manager.py status [--run-id <id>]
    python orchestrator-context-manager.py handoff --stage <stage> [--run-id <id>]
    python orchestrator-context-manager.py record --stage <stage> --status <PASSED|FAILED|BLOCKED|SKIPPED> --summary "Notes" [--run-id <id>]
    python orchestrator-context-manager.py report [--run-id <id>]
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
    "architecturechecks",
    "halucinationchecks",
    "securitychecks",
]

STAGE_SKILLS_MAP = {
    "plan": {
        "primary_skill": "architectural-planning",
        "supporting_skills": ["trace-code-context", "load-memory"],
        "subagent_role": "Architecture & Planning Specialist",
        "description": "System design, requirements breakdown, component boundaries, and contract definition.",
    },
    "develop": {
        "primary_skill": "python-developer / typescript-developer / java-developer",
        "supporting_skills": ["load-memory", "save-memory"],
        "subagent_role": "Core Implementation & Test Engineer",
        "description": "Production code authoring, automated unit/integration tests, and implementation of planned specs.",
    },
    "codereview": {
        "primary_skill": "code-reviewer",
        "supporting_skills": ["python-linter", "design-pattern-detector"],
        "subagent_role": "Senior Code Reviewer",
        "description": "Code quality, readability, style conformance, idiomatic usage, error handling, and clean code inspection.",
    },
    "architecturechecks": {
        "primary_skill": "detect-overengineering",
        "supporting_skills": ["design-pattern-detector", "trace-code-context"],
        "subagent_role": "Principal Architecture Auditor",
        "description": "Structural analysis, detection of premature abstractions (YAGNI), layer bloat, anti-patterns, and dependency call-graphs.",
    },
    "halucinationchecks": {
        "primary_skill": "scan-halucinated-tests",
        "supporting_skills": ["trace-code-context"],
        "subagent_role": "Ground-Truth Verification Auditor",
        "description": "Verification of test symbols, non-existent imports, fabricated APIs, and phantom dependencies against ground-truth source code.",
    },
    "securitychecks": {
        "primary_skill": "github-security-scanner-hook",
        "supporting_skills": ["semgrep", "detect-secrets"],
        "subagent_role": "Application Security Auditor",
        "description": "Secrets scanning, API key leakage detection, OWASP vulnerability audit (injections, traversal, shell execution), and secure defaults.",
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

    args = parser.parse_args()

    if args.subcommand == "init":
        cmd_init(args)
    elif args.subcommand == "status":
        cmd_status(args)
    elif args.subcommand == "handoff":
        cmd_handoff(args)
    elif args.subcommand == "record":
        cmd_record(args)
    elif args.subcommand == "report":
        cmd_report(args)


if __name__ == "__main__":
    main()

