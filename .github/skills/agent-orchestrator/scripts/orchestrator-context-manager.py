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

Use --help for commands and SKILL.md for workflow and evidence requirements.
"""

import argparse
import datetime
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from orchestrator_gates import check_sources, check_transition, scored_items, source_files
from orchestrator_reporting import emit_handoff, emit_report
from orchestrator_specs import STAGE_SKILLS_MAP

STAGES = [
    "plan",
    "develop",
    "codereview",
    "complexitychecks",
    "architecturechecks",
    "halucinationchecks",
    "securitychecks",
]

SLICE_LOOP_STAGES = [
    "develop",
    "codereview",
    "complexitychecks",
    "architecturechecks",
    "halucinationchecks",
]

BASE_DIR = Path(".orchestrator")
RUNS_DIR = BASE_DIR / "runs"

MAJOR_CHANGE_RE = re.compile(
    r"\b(security|refactor|migrat\w*|architect\w*|redesign|rewrite|auth\w*|schema|database|breaking|across|all|mcp|pipeline)\b",
    re.IGNORECASE,
)


def is_major_change_task(task: str) -> bool:
    return bool(MAJOR_CHANGE_RE.search(task))


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

    major_change = bool(getattr(args, "major", False) or is_major_change_task(args.task))
    manifest: Dict[str, Any] = {
        "run_id": run_id,
        "task": args.task,
        "created_at": now.isoformat(),
        "status": "IN_PROGRESS",
        "current_stage": "plan",
        "is_major_change": major_change,
        "judge_reviewed": False,
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
    if major_change:
        print("Major change detected: Stage 'plan' requires 'llm-as-judge' arbitration (--judge-verdict) before 'develop'.")


def get_active_slice(manifest: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    bdd = manifest.get("bdd_slices")
    if not bdd or not bdd.get("items"):
        return None
    idx = bdd.get("current_index", 0)
    items = bdd["items"]
    if 0 <= idx < len(items):
        return {
            "index": idx,
            "total": len(items),
            "name": items[idx]["name"],
            "items": items,
        }
    return None


def cmd_slices(args: argparse.Namespace) -> None:
    run_dir = get_run_dir(args.run_id)
    manifest = load_manifest(run_dir)
    bdd = manifest.setdefault("bdd_slices", {"items": [], "current_index": 0})

    if args.add:
        existing = {item["name"] for item in bdd["items"]}
        added = []
        for raw in args.add:
            for name in [p.strip() for p in raw.split(",") if p.strip()]:
                if name not in existing:
                    bdd["items"].append({"name": name, "status": "PENDING", "completed_at": None})
                    existing.add(name)
                    added.append(name)
        if bdd["items"] and all(i["status"] == "PENDING" for i in bdd["items"]):
            bdd["current_index"] = 0
            bdd["items"][0]["status"] = "IN_PROGRESS"
        save_manifest(run_dir, manifest)
        print(f"Registered {len(added)} BDD slice(s): {', '.join(added) if added else '(none new)'}")

    items = bdd.get("items", [])
    if not items:
        print("No BDD feature slices registered for this run.")
        return
    idx = bdd.get("current_index", 0)
    print(f"BDD Feature Slices ({len(items)} total, active index {idx + 1}/{len(items)}):")
    for i, item in enumerate(items):
        marker = "->" if i == idx and item["status"] != "PASSED" else "  "
        print(f"  {marker} [{i + 1}/{len(items)}] {item['name']} ({item['status']})")


def cmd_status(args: argparse.Namespace) -> None:
    run_dir = get_run_dir(args.run_id)
    manifest = load_manifest(run_dir)

    print("=" * 70)
    print(f"ORCHESTRATOR RUN: {manifest['run_id']}")
    print(f"Task: {manifest['task']}")
    print(f"Overall Status: {manifest['status']} | Current Stage: {manifest.get('current_stage', 'done')}")
    active_slice = get_active_slice(manifest)
    if active_slice:
        print(f"Active BDD Slice: [{active_slice['index'] + 1}/{active_slice['total']}] {active_slice['name']}")
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
    check_transition(run_dir, manifest, STAGES, stage)

    is_major = bool(manifest.get("is_major_change") or len(manifest.get("bdd_slices", {}).get("items", [])) >= 2)
    if stage == "develop" and is_major and not manifest.get("judge_reviewed"):
        print(
            "Gate BLOCKED: Cannot hand off to 'develop' on a major change before 'plan' passes 'llm-as-judge' arbitration.",
            file=sys.stderr,
        )
        sys.exit(1)

    active = get_active_slice(manifest) if stage in SLICE_LOOP_STAGES else None
    emit_handoff(stage, manifest, STAGES, STAGE_SKILLS_MAP, active)


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

    is_major = bool(manifest.get("is_major_change") or len(manifest.get("bdd_slices", {}).get("items", [])) >= 2)
    judge_verdict = getattr(args, "judge_verdict", None)
    if status == "PASSED":
        manifest["status"] = "IN_PROGRESS"
        check_transition(run_dir, manifest, STAGES, stage, args.summary, args.learnings,
                         args.artifact, completing=True, source_files=args.source_file)
    if stage == "plan" and status == "PASSED" and is_major:
        if not judge_verdict or not judge_verdict.strip():
            print(
                "Gate BLOCKED: Major change detected for stage 'plan'. Run 'llm-as-judge' (Pessimist, Contrarian, "
                "Pragmatist, Specialist) on the plan first, then pass --judge-verdict \"<verdict>\".",
                file=sys.stderr,
            )
            sys.exit(1)
        manifest["judge_reviewed"] = True

    now_iso = datetime.datetime.now().isoformat()
    stage_data = manifest["stages"].setdefault(stage, {})
    stage_data["status"] = status
    stage_data["completed_at"] = now_iso
    stage_data["summary"] = args.summary or ""
    stage_data["learnings"] = args.learnings or ""
    if judge_verdict:
        stage_data["judge_verdict"] = judge_verdict.strip()

    if args.artifact:
        artifacts = stage_data.setdefault("artifacts", [])
        if args.artifact not in artifacts:
            artifacts.append(args.artifact)

    # Determine next stage (handling BDD feature-slice inner loop at halucinationchecks)
    stage_idx = STAGES.index(stage)
    active_slice = get_active_slice(manifest)
    if status == "PASSED":
        if stage == "halucinationchecks" and active_slice:
            bdd = manifest["bdd_slices"]
            cur_idx = active_slice["index"]
            bdd["items"][cur_idx]["status"] = "PASSED"
            bdd["items"][cur_idx]["completed_at"] = now_iso

            if cur_idx + 1 < len(bdd["items"]):
                bdd["current_index"] = cur_idx + 1
                bdd["items"][cur_idx + 1]["status"] = "IN_PROGRESS"
                for loop_stage in SLICE_LOOP_STAGES:
                    s_entry = manifest["stages"][loop_stage]
                    history = s_entry.setdefault("slice_history", [])
                    history.append({
                        "slice": active_slice["name"],
                        "status": s_entry.get("status"),
                        "summary": s_entry.get("summary"),
                        "artifacts": list(s_entry.get("artifacts", [])),
                    })
                    s_entry["status"] = "PENDING"
                    s_entry["summary"] = None
                    s_entry["completed_at"] = None
                    s_entry["artifacts"] = []
                manifest["current_stage"] = "develop"
                manifest["stages"]["develop"]["status"] = "READY"
                save_manifest(run_dir, manifest)
                next_slice = bdd["items"][cur_idx + 1]["name"]
                print(f"Successfully recorded stage '{stage}' as {status} for slice '{active_slice['name']}'.")
                print(f"Advancing BDD slice [{cur_idx + 2}/{len(bdd['items'])}]: '{next_slice}' -> looping back to stage 'develop'.")
                return

        if stage_idx + 1 < len(STAGES):
            manifest["current_stage"] = STAGES[stage_idx + 1]
            manifest["stages"][manifest["current_stage"]]["status"] = "READY"
        else:
            manifest["current_stage"] = "COMPLETED"
            manifest["status"] = "PASSED"
    elif status in ["FAILED", "BLOCKED", "SKIPPED"]:
        manifest["status"] = f"STOPPED_AT_{stage.upper()}"
        manifest["current_stage"] = stage
        for later in STAGES[stage_idx + 1:]:
            manifest["stages"][later]["status"] = "PENDING"

    save_manifest(run_dir, manifest)
    print(f"Successfully recorded stage '{stage}' as {status}.")
    if manifest["current_stage"] != "COMPLETED":
        print(f"Next stage in pipeline: {manifest['current_stage']}")
    else:
        print("All pipeline stages completed successfully!")


def cmd_skill_doctor(args: argparse.Namespace) -> None:
    doctor_script = Path(".github/skills/skill-doctor/scripts/skill-doctor.py")
    if not doctor_script.exists():
        print(f"Error: skill-doctor.py not found at {doctor_script}", file=sys.stderr)
        sys.exit(1)
    import subprocess
    cmd = [sys.executable, str(doctor_script), "diagnose", "--format", args.format]
    result = subprocess.run(cmd)
    sys.exit(result.returncode)


def cmd_report(args: argparse.Namespace) -> None:
    run_dir = get_run_dir(args.run_id)
    manifest = load_manifest(run_dir)

    emit_report(run_dir, manifest, STAGES, STAGE_SKILLS_MAP)


def cmd_check_overengineering(args: argparse.Namespace) -> None:
    if sum(bool(value) for value in (args.file, args.dir, args.all)) != 1:
        raise ValueError("Select exactly one of --file, --dir or --all")
    if not 0 < args.max_score <= 100:
        raise ValueError("--max-score must be in (0,100]")
    selected = [Path(args.file)] if args.file else source_files(args.dir or ".")
    check_sources(selected)
    extract_script = Path(".github/skills/detect-overengineering/scripts/extract-signals.py")
    if not extract_script.exists():
        extract_script = Path(__file__).resolve().parents[2] / "detect-overengineering/scripts/extract-signals.py"
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
    except json.JSONDecodeError as error:
        raise ValueError("Extractor returned invalid JSON") from error

    max_allowed = args.max_score
    items = scored_items(data)
    if {Path(item["source_path"]).resolve() for item in items} != {file.resolve() for file in selected}:
        raise ValueError("Extractor must cover exactly the selected source files")

    failed = []
    print("=" * 70)
    print("OVER-ENGINEERING IN-THE-LOOP AUDIT")
    print(f"Max Allowed Risk Score: {max_allowed}/100")
    print("=" * 70)
    for item in items:
        score = item["overengineering_score"]
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
    p_init.add_argument("--major", action="store_true", help="Explicitly mark task as a major change requiring llm-as-judge in plan")

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
    p_record.add_argument("--learnings", help="Required nonempty learnings for PASSED")
    p_record.add_argument("--source-file", action="append", help="Changed source file; repeat for develop/code/architecture gates")
    p_record.add_argument("--artifact", help="Path to primary artifact generated")
    p_record.add_argument("--judge-verdict", help="Required for major changes in 'plan' after llm-as-judge arbitration")
    p_record.add_argument("--run-id", help="Optional run ID (defaults to latest)")

    # report
    p_report = subparsers.add_parser("report", help="Generate full markdown report")
    p_report.add_argument("--run-id", help="Optional run ID (defaults to latest)")

    # skill-doctor
    p_doctor = subparsers.add_parser("skill-doctor", help="Run periodic skill-doctor diagnostics on pending memory learnings")
    p_doctor.add_argument("--format", choices=["text", "json"], default="text")

    # slices
    p_slices = subparsers.add_parser("slices", help="Register or list BDD feature slices for the inner loop")
    p_slices.add_argument("--add", nargs="+", help="BDD .feature file(s) or @tag phase(s) to register")
    p_slices.add_argument("--run-id", help="Optional run ID (defaults to latest)")

    # check-overengineering
    p_check_oe = subparsers.add_parser("check-overengineering", help="Audit files for over-engineering and accidental complexity in the loop")
    p_check_oe.add_argument("--file", help="Path to single source file to audit")
    p_check_oe.add_argument("--dir", help="Directory of source files to audit")
    p_check_oe.add_argument("--all", action="store_true", help="Analyze all source files in repository")
    p_check_oe.add_argument("--max-score", type=int, default=40, help="Maximum allowable over-engineering score (default: 40)")
    p_check_oe.add_argument("--force", action="store_true", help="Force re-analysis even if cached report is up to date")

    args = parser.parse_args()

    handlers = {
        "init": cmd_init,
        "status": cmd_status,
        "handoff": cmd_handoff,
        "record": cmd_record,
        "slices": cmd_slices,
        "check-overengineering": cmd_check_overengineering,
        "report": cmd_report,
        "skill-doctor": cmd_skill_doctor,
    }
    handlers[args.subcommand](args)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, UnicodeError) as error:
        print(f"Gate FAILED: {error}", file=sys.stderr)
        sys.exit(1)
