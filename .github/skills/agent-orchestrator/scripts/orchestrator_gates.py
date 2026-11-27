"""Deterministic source, planning and workflow gates; Python standard library only."""

import argparse
import json
import math
import os
import re
from pathlib import Path

MAX_LINES = 500
MAX_BYTES = 256 * 1024
PLAN_SECTIONS = ("Scope", "Acceptance criteria", "Implementation", "Validation", "Effort", "Limits")
CHECKBOX = re.compile(r"^\s*[-*]\s+\[([ xX])\]\s+\S", re.MULTILINE)

def source_files(directory):
    require(Path(directory).is_dir(), f"Missing source directory: {directory}")
    files = []
    for root, directories, names in os.walk(directory):
        directories[:] = [d for d in directories if d not in {
            ".git", ".venv", "node_modules", "dist", "__pycache__"
        }]
        files.extend(Path(root) / name for name in names if Path(name).suffix in {
            ".py", ".ts", ".tsx", ".js", ".jsx", ".java", ".cs", ".go", ".ps1"
        })
    return files


def require(condition, message):
    if not condition:
        raise ValueError(message)


def document(file):
    require(file.is_file(), f"Missing artifact: {file}")
    require(0 < file.stat().st_size <= MAX_BYTES, f"Empty or oversized artifact: {file}")
    text = file.read_text(encoding="utf-8-sig")
    require(bool(text.strip()), f"Empty artifact: {file}")
    return text


def check_plan(run_dir):
    plan = document(run_dir / "plan.md")
    for section in PLAN_SECTIONS:
        require(re.search(rf"(?im)^(?:#+\s*)?{re.escape(section)}\b", plan),
                f"plan.md missing section: {section}")
    checklist = document(run_dir / "checklist.md")
    require(CHECKBOX.search(checklist), "checklist.md needs actionable checkbox items")


def check_sources(files, max_lines=MAX_LINES, max_bytes=MAX_BYTES):
    require(type(max_lines) is int and max_lines > 0, "max-lines must be positive")
    require(type(max_bytes) is int and max_bytes > 0, "max-bytes must be positive")
    require(bool(files), "No source files selected")
    metrics = []
    for file in files:
        file = Path(file)
        require(file.is_file(), f"Missing source file: {file}")
        size = file.stat().st_size
        require(size <= max_bytes, f"{file}: {size} bytes exceeds {max_bytes}")
        # Read at most limit+1, even if the file grows after stat.
        with file.open("rb") as source:
            raw = source.read(max_bytes + 1)
        require(len(raw) <= max_bytes, f"{file}: exceeds {max_bytes} bytes")
        lines = len(raw.decode("utf-8-sig").splitlines())
        require(lines <= max_lines, f"{file}: {lines} lines exceeds {max_lines}")
        metrics.append({"file": str(file), "lines": lines, "bytes": len(raw)})
    return metrics


def check_transition(run_dir, manifest, stages, stage, summary=None, learnings=None,
                     artifact=None, completing=False, source_files=None):
    require(stage in stages, f"Unknown stage: {stage}")
    check_plan(run_dir)
    require(manifest.get("current_stage") == stage, f"Stage {stage} is not the active stage")
    if stage != "plan":
        previous = stages[stages.index(stage) - 1]
        require(manifest["stages"][previous].get("status") == "PASSED",
                f"Predecessor {previous} must pass before {stage}")
    if not completing:
        return
    require(bool(summary and summary.strip()), "PASSED requires a nonempty summary")
    require(bool(learnings and learnings.strip()), "PASSED requires nonempty learnings")
    require(bool(artifact), "PASSED requires --artifact evidence")
    evidence = Path(artifact)
    if not evidence.is_absolute():
        evidence = run_dir / evidence
    require(evidence.is_file() and evidence.stat().st_size > 0, f"Missing or empty evidence: {evidence}")
    if stage in ("develop", "codereview", "architecturechecks"):
        check_sources(source_files)
    if stage == stages[-1]:
        require(all(manifest["stages"][s].get("status") == "PASSED" for s in stages[:-1]),
                "Every previous stage must pass before final completion")
        require(not any(mark == " " for mark in CHECKBOX.findall(document(run_dir / "checklist.md"))),
                "Final completion blocked by unchecked checklist items")


def scored_items(data):
    items = data.get("files") if isinstance(data, dict) and "files" in data else data
    if isinstance(items, dict):
        items = [items]
    require(isinstance(items, list) and bool(items), "Extractor returned no scored files")
    for item in items:
        require(isinstance(item, dict), "Malformed extractor item")
        score = item.get("overengineering_score")
        require(type(score) in (int, float) and math.isfinite(score) and 0 <= score <= 100,
                "Extractor requires a finite overengineering_score in [0,100]")
        require(isinstance(item.get("source_path"), str) and bool(item["source_path"].strip()),
                "Extractor requires source_path")
    return items


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    source = commands.add_parser("source", help="Enforce physical line and byte limits")
    source.add_argument("--file", action="append", required=True)
    source.add_argument("--max-lines", type=int, default=MAX_LINES)
    source.add_argument("--max-bytes", type=int, default=MAX_BYTES)
    plan = commands.add_parser("plan", help="Check required planning artifacts")
    plan.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "source":
            print(json.dumps(check_sources(args.file, args.max_lines, args.max_bytes), indent=2))
        else:
            check_plan(args.run_dir)
            print("Planning artifacts passed")
    except (ValueError, OSError, UnicodeError) as error:
        parser.exit(1, f"Gate FAILED: {error}\n")


if __name__ == "__main__":
    main()
