#!/usr/bin/env python3
r"""
skill-doctor.py — Diagnose unprocessed project-memory learnings, map them to skills,
audit skill health, and mark learnings as promoted or skipped.

Usage:
    .\.venv\Scripts\python.exe .github/skills/skill-doctor/scripts/skill-doctor.py diagnose [--db .project-memory/memory.db] [--skills-dir .github/skills] [--format text|json]
    .\.venv\Scripts\python.exe .github/skills/skill-doctor/scripts/skill-doctor.py mark --ids id1,id2 --status promoted|skipped --target-skill <name> [--db .project-memory/memory.db]
    .\.venv\Scripts\python.exe .github/skills/skill-doctor/scripts/skill-doctor.py audit-skills [--skills-dir .github/skills] [--format text|json]
"""

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import sqlite3
import sys
from typing import Any, Dict, List, Optional, Tuple


DEFAULT_DB_PATH = Path(".project-memory/memory.db")
DEFAULT_SKILLS_DIR = Path(".github/skills")
STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "into", "when", "where",
    "what", "avoid", "always", "never", "use", "using", "used", "should", "must",
    "only", "more", "than", "also", "have", "been", "being", "were", "will", "not",
    "all", "any", "are", "can", "was", "but", "how", "why", "its", "their", "them",
    "they", "such", "make", "made", "file", "files", "code", "run", "running",
    "session", "mistake", "learnings", "learning", "error", "errors", "fix",
}
GENERIC_TAGS = {
    "ledger", "journal", "sidecar", "session", "session-recap", "mistake",
    "mistake-avoided", "learnings", "architecture", "tooling-rule", "audit-failure",
}
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)#\s]+)(?:#[^)]*)?\)")
FRONTMATTER_RE = re.compile(r"^---\r?\n(.*?)\r?\n---", re.DOTALL)
FENCED_BLOCK_RE = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`]+`")


def tokenize(text: str) -> List[str]:
    tokens = re.findall(r"[a-z0-9][a-z0-9_-]{1,}", text.lower())
    return [t for t in tokens if len(t) > 2 and t not in STOPWORDS]


def ensure_memory_schema(conn: sqlite3.Connection) -> None:
    """Idempotently ensure skill-doctor tracking columns exist on memories."""
    cols = {row[1] for row in conn.execute("PRAGMA table_info(memories)").fetchall()}
    if not cols:
        return
    if "skill_status" not in cols:
        conn.execute("ALTER TABLE memories ADD COLUMN skill_status TEXT NOT NULL DEFAULT 'pending'")
    if "target_skill" not in cols:
        conn.execute("ALTER TABLE memories ADD COLUMN target_skill TEXT")
    if "promoted_at" not in cols:
        conn.execute("ALTER TABLE memories ADD COLUMN promoted_at TEXT")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_skill_status ON memories(skill_status)")
    conn.commit()


def parse_frontmatter(text: str) -> Dict[str, str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}
    fields: Dict[str, str] = {}
    current_key: Optional[str] = None
    multiline_parts: List[str] = []
    for line in match.group(1).splitlines():
        if line.startswith((" ", "\t")) and current_key is not None:
            multiline_parts.append(line.strip())
            continue
        if current_key is not None:
            fields[current_key] = " ".join(multiline_parts).strip()
            current_key = None
            multiline_parts = []
        if ":" in line and not line.startswith(" "):
            key, val = line.split(":", 1)
            k = key.strip()
            v = val.strip()
            if v in (">", ">-", "|", "|-"):
                current_key = k
                multiline_parts = []
            else:
                fields[k] = v.strip("'\"")
    if current_key is not None:
        fields[current_key] = " ".join(multiline_parts).strip()
    return fields


def load_skill_index(skills_dir: Path) -> Dict[str, Dict[str, Any]]:
    """Index every skill's frontmatter, markdown files, and searchable vocabulary."""
    index: Dict[str, Dict[str, Any]] = {}
    if not skills_dir.exists():
        return index

    for skill_dir in sorted(p for p in skills_dir.iterdir() if p.is_dir()):
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        md_files = sorted(skill_dir.rglob("*.md"))
        combined_parts: List[str] = []
        for md in md_files:
            try:
                combined_parts.append(md.read_text(encoding="utf-8"))
            except OSError:
                continue
        combined_text = "\n".join(combined_parts)
        fm = parse_frontmatter(skill_md.read_text(encoding="utf-8"))
        submodules = [str(p.relative_to(skill_dir)).replace("\\", "/") for p in md_files if p != skill_md]
        index[skill_dir.name] = {
            "name": fm.get("name", skill_dir.name),
            "version": fm.get("version", ""),
            "description": fm.get("description", ""),
            "skill_md": str(skill_md).replace("\\", "/"),
            "submodules": submodules,
            "is_modular": len(submodules) >= 2 and any("/" in s for s in submodules),
            "tokens": set(tokenize(skill_dir.name.replace("-", " ") + " " + combined_text)),
            "text_lower": combined_text.lower(),
        }
    return index


def match_learning_to_skill(
    memory: Dict[str, Any], skill_index: Dict[str, Dict[str, Any]]
) -> Tuple[Optional[str], float, bool]:
    """Return (best_skill, confidence_score, already_covered_hint)."""
    tags = [t.lower() for t in memory.get("tags", [])]
    mem_tokens = set(tokenize(f"{memory['title']} {memory['summary']} {memory['learnings']} {' '.join(tags)}"))
    if not mem_tokens:
        return None, 0.0, False

    best_skill: Optional[str] = None
    best_score = 0.0
    for skill_name, info in skill_index.items():
        name_parts = set(skill_name.split("-"))
        overlap = len(mem_tokens & info["tokens"])
        desc_tokens = set(tokenize(info["description"]))
        desc_overlap = len(mem_tokens & desc_tokens)
        tag_boost = sum(3.0 for t in tags if t in name_parts or t == skill_name)
        desc_tag_boost = sum(1.2 for t in tags if t in desc_tokens)
        size_norm = math.sqrt(max(len(info["tokens"]), 1))
        score = (overlap / size_norm) + (desc_overlap / max(len(mem_tokens), 1)) + ((tag_boost + desc_tag_boost) * 0.15)
        if score > best_score:
            best_score = score
            best_skill = skill_name

    if not best_skill or best_score < 0.35:
        return None, round(best_score, 3), False

    learning_tokens = tokenize(memory["learnings"])
    if learning_tokens:
        covered_hits = sum(1 for tok in set(learning_tokens) if tok in skill_index[best_skill]["text_lower"])
        coverage = covered_hits / len(set(learning_tokens))
    else:
        coverage = 0.0
    return best_skill, round(best_score, 3), coverage >= 0.72


def pick_target_file(skill_info: Dict[str, Any], memory: Dict[str, Any]) -> str:
    """Suggest the cleanest target file inside a skill without bloating modular routers."""
    if not skill_info["is_modular"] or not skill_info["submodules"]:
        return skill_info["skill_md"]

    text = f"{memory['title']} {memory['learnings']} {' '.join(memory.get('tags', []))}".lower()
    submodules: List[str] = skill_info["submodules"]
    keyword_routes = [
        (("security", "auth", "token", "secret", "injection", "xss"), "security"),
        (("test", "mock", "fixture", "pytest", "vitest", "playwright"), "test"),
        (("async", "thread", "concurrency", "lock", "event loop"), "concurren"),
        (("memory", "closure", "leak", "gc", "cache"), "memory"),
    ]
    for keywords, path_hint in keyword_routes:
        if any(k in text for k in keywords):
            for sub in submodules:
                if path_hint in sub.lower():
                    return str(Path(skill_info["skill_md"]).parent / sub).replace("\\", "/")
    return str(Path(skill_info["skill_md"]).parent / submodules[0]).replace("\\", "/")


def fetch_pending_memories(db_path: Path) -> List[Dict[str, Any]]:
    if not db_path.exists():
        return []
    conn = sqlite3.connect(str(db_path))
    try:
        table_exists = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='memories'"
        ).fetchone()
        if not table_exists:
            return []
        ensure_memory_schema(conn)
        rows = conn.execute(
            """
            SELECT id, category, title, summary, learnings, tags, created_at, updated_at
            FROM memories
            WHERE skill_status = 'pending' AND category IN ('journal', 'ledger')
            ORDER BY updated_at DESC
            """
        ).fetchall()
    finally:
        conn.close()

    memories: List[Dict[str, Any]] = []
    for row in rows:
        memories.append({
            "id": row[0],
            "category": row[1],
            "title": row[2],
            "summary": row[3],
            "learnings": row[4],
            "tags": json.loads(row[5] or "[]"),
            "created_at": row[6],
            "updated_at": row[7],
        })
    return memories


def cmd_diagnose(args: argparse.Namespace) -> None:
    db_path = Path(args.db)
    skills_dir = Path(args.skills_dir)
    memories = fetch_pending_memories(db_path)
    skill_index = load_skill_index(skills_dir)

    recommendations: List[Dict[str, Any]] = []
    unmapped_tags: Counter = Counter()

    for mem in memories:
        matched_skill, confidence, already_covered = match_learning_to_skill(mem, skill_index)
        if matched_skill:
            action = "ALREADY_COVERED_CANDIDATE" if already_covered else "UPDATE_EXISTING_SKILL"
            target_file = pick_target_file(skill_index[matched_skill], mem)
        else:
            action = "UNMAPPED_CANDIDATE"
            target_file = None
            for tag in mem["tags"]:
                if tag.lower() not in GENERIC_TAGS:
                    unmapped_tags[tag.lower()] += 1

        recommendations.append({
            "id": mem["id"],
            "category": mem["category"],
            "title": mem["title"],
            "learnings": mem["learnings"],
            "tags": mem["tags"],
            "action": action,
            "candidate_skill": matched_skill,
            "confidence": confidence,
            "target_file": target_file,
        })

    new_skill_clusters = [{"tag": tag, "count": count} for tag, count in unmapped_tags.items() if count >= 2]
    payload = {
        "db_path": str(db_path).replace("\\", "/"),
        "pending_count": len(memories),
        "skills_indexed": len(skill_index),
        "recommendations": recommendations,
        "new_skill_clusters": new_skill_clusters,
    }

    if args.format == "json":
        print(json.dumps(payload, indent=2))
        return

    print("=" * 72)
    print("SKILL DOCTOR DIAGNOSTIC REPORT")
    print(f"Database: {payload['db_path']} | Pending Learnings: {len(memories)} | Indexed Skills: {len(skill_index)}")
    print("=" * 72)
    if not recommendations:
        print("No pending journal/ledger learnings found. Skills are up to date.")
        return

    for rec in recommendations:
        print(f"- [{rec['category']}] {rec['id']} | {rec['title']}")
        print(f"  Action: {rec['action']} | Candidate: {rec['candidate_skill'] or 'none'} (score={rec['confidence']})")
        if rec["target_file"]:
            print(f"  Target File: {rec['target_file']}")
        print(f"  Learning: {rec['learnings']}")
    if new_skill_clusters:
        print("\nNew Skill Cluster Candidates (>= 2 unmapped learnings):")
        for cluster in new_skill_clusters:
            print(f"  * tag '{cluster['tag']}' ({cluster['count']} learnings) -> consider skill-creator")


def cmd_mark(args: argparse.Namespace) -> None:
    db_path = Path(args.db)
    if not db_path.exists():
        print(f"Error: Memory database not found at {db_path}", file=sys.stderr)
        sys.exit(1)

    ids = [i.strip() for i in args.ids.split(",") if i.strip()]
    if not ids:
        print("Error: Provide at least one memory ID via --ids.", file=sys.stderr)
        sys.exit(1)

    now = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(str(db_path))
    try:
        ensure_memory_schema(conn)
        updated = 0
        for mem_id in ids:
            cur = conn.execute(
                "UPDATE memories SET skill_status = ?, target_skill = ?, promoted_at = ? WHERE id = ?",
                (args.status, args.target_skill.strip(), now, mem_id),
            )
            updated += cur.rowcount
        conn.commit()
    finally:
        conn.close()

    print(json.dumps({
        "updated_count": updated,
        "status": args.status,
        "target_skill": args.target_skill.strip(),
        "promoted_at": now,
    }, indent=2))


def audit_skill_quality(sdir: Path, content: str, fm: Dict[str, str]) -> List[Dict[str, str]]:
    """Diagnose trigger quality, instruction bloat, orphan files, and missing verification."""
    warnings: List[Dict[str, str]] = []
    desc = fm.get("description", "")
    desc_lower = desc.lower()
    if desc and (len(desc) < 80 or ('"' not in desc and "'" not in desc and "use when" not in desc_lower)):
        warnings.append({
            "skill": sdir.name,
            "severity": "WARN",
            "issue": "Vague trigger description (add 'Use when...' scenarios and quoted trigger phrases).",
        })

    lines = content.splitlines()
    submodules = [p for p in sdir.rglob("*.md") if p.name != "SKILL.md" and "references" not in p.parts]
    is_modular = len(submodules) >= 2
    if is_modular and len(lines) > 65:
        warnings.append({
            "skill": sdir.name,
            "severity": "WARN",
            "issue": f"Modular SKILL.md router is {len(lines)} lines (> 65); move details into topical submodules.",
        })
    elif not is_modular and len(lines) > 1000:
        warnings.append({
            "skill": sdir.name,
            "severity": "WARN",
            "issue": f"SKILL.md is {len(lines)} lines (> 1000); split supporting details into references/.",
        })

    scripts = [
        p for p in (sdir / "scripts").rglob("*")
        if p.is_file() and p.name != ".gitkeep" and "__pycache__" not in p.parts
    ] if (sdir / "scripts").exists() else []
    refs = list((sdir / "references").rglob("*.md")) if (sdir / "references").exists() else []
    for asset in scripts + refs:
        if asset.name not in content:
            rel = str(asset.relative_to(sdir)).replace("\\", "/")
            warnings.append({
                "skill": sdir.name,
                "severity": "WARN",
                "issue": f"Orphan asset '{rel}' is not referenced in SKILL.md.",
            })

    if scripts and not any(k in content.lower() for k in ("verify", "validate", "test", "exit code", "output")):
        warnings.append({
            "skill": sdir.name,
            "severity": "WARN",
            "issue": "Skill includes scripts/ but lacks verification or expected-output guidance in SKILL.md.",
        })

    for block in FENCED_BLOCK_RE.findall(content):
        for bline in block.splitlines():
            stripped = bline.strip()
            if re.match(r"^(python3?|py)\s+", stripped) and "venv" not in stripped:
                warnings.append({
                    "skill": sdir.name,
                    "severity": "WARN",
                    "issue": f"Bare Python command '{stripped[:50]}' in SKILL.md; prefer .venv Python resolution.",
                })
                break
    return warnings


def cmd_audit_skills(args: argparse.Namespace) -> None:
    skills_dir = Path(args.skills_dir)
    if not skills_dir.exists():
        print(f"Error: Skills directory not found at {skills_dir}", file=sys.stderr)
        sys.exit(1)

    issues: List[Dict[str, str]] = []
    skill_dirs = sorted(p for p in skills_dir.iterdir() if p.is_dir())
    if args.skill:
        skill_dirs = [p for p in skill_dirs if p.name == args.skill]
        if not skill_dirs:
            print(f"Error: Skill '{args.skill}' not found in {skills_dir}", file=sys.stderr)
            sys.exit(1)

    for sdir in skill_dirs:
        skill_md = sdir / "SKILL.md"
        if not skill_md.exists():
            issues.append({"skill": sdir.name, "severity": "ERROR", "issue": "Missing SKILL.md"})
            continue
        content = skill_md.read_text(encoding="utf-8")
        fm = parse_frontmatter(content)
        for req in ("name", "description"):
            if not fm.get(req):
                issues.append({"skill": sdir.name, "severity": "ERROR", "issue": f"Missing '{req}' in frontmatter"})
        for md_file in sdir.rglob("*.md"):
            md_text = FENCED_BLOCK_RE.sub("", md_file.read_text(encoding="utf-8"))
            md_text = INLINE_CODE_RE.sub("", md_text)
            for link in LINK_RE.findall(md_text):
                if link.startswith(("http://", "https://", "mailto:", "file://")) or "{" in link or link == "url":
                    continue
                target = (md_file.parent / link).resolve()
                if not target.exists():
                    rel = str(md_file.relative_to(skills_dir)).replace("\\", "/")
                    issues.append({"skill": sdir.name, "severity": "ERROR", "issue": f"Broken link '{link}' in {rel}"})
        issues.extend(audit_skill_quality(sdir, content, fm))

    errors = [i for i in issues if i["severity"] == "ERROR"]
    warnings = [i for i in issues if i["severity"] == "WARN"]
    result = {
        "skills_audited": len(skill_dirs),
        "errors_count": len(errors),
        "warnings_count": len(warnings),
        "issues": issues,
    }
    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        print(f"Audited {len(skill_dirs)} skill(s) | Errors: {len(errors)} | Warnings: {len(warnings)}")
        for item in issues:
            print(f"  [{item['severity']}] {item['skill']}: {item['issue']}")
    if errors or (args.strict and warnings):
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Skill Doctor — Evolve repository skills from project-memory learnings.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_diag = subparsers.add_parser("diagnose", help="Inspect unprocessed learnings and map them to skills")
    p_diag.add_argument("--db", default=str(DEFAULT_DB_PATH), help="Path to SQLite memory.db")
    p_diag.add_argument("--skills-dir", default=str(DEFAULT_SKILLS_DIR), help="Path to skills directory")
    p_diag.add_argument("--format", choices=["text", "json"], default="text")

    p_mark = subparsers.add_parser("mark", help="Mark memory IDs as promoted or skipped")
    p_mark.add_argument("--ids", required=True, help="Comma-separated memory IDs")
    p_mark.add_argument("--status", required=True, choices=["promoted", "skipped"])
    p_mark.add_argument("--target-skill", required=True, help="Target skill name or 'none'")
    p_mark.add_argument("--db", default=str(DEFAULT_DB_PATH), help="Path to SQLite memory.db")

    p_audit = subparsers.add_parser("audit-skills", help="Audit SKILL.md frontmatter, links, and skill quality")
    p_audit.add_argument("--skills-dir", default=str(DEFAULT_SKILLS_DIR), help="Path to skills directory")
    p_audit.add_argument("--skill", help="Optional single skill name to audit")
    p_audit.add_argument("--strict", action="store_true", help="Exit non-zero on WARN findings as well as ERRORs")
    p_audit.add_argument("--format", choices=["text", "json"], default="text")

    args = parser.parse_args()
    if args.command == "diagnose":
        cmd_diagnose(args)
    elif args.command == "mark":
        cmd_mark(args)
    elif args.command == "audit-skills":
        cmd_audit_skills(args)


if __name__ == "__main__":
    main()
