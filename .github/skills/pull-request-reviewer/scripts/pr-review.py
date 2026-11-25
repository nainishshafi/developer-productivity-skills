"""Collect immutable GitHub PR evidence and render agent-authored reviews as offline HTML.

Collection uses read-only gh commands; rendering validates evidence references and escapes
all source text before inserting it into the reusable template. No PR code is executed.
"""

import argparse
from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import quote
import textwrap


PR_FIELDS = (
    "number,title,url,body,baseRefName,headRefName,baseRefOid,headRefOid,"
    "changedFiles,additions,deletions,author,state,statusCheckRollup"
)


def gh(*args):
    """Pass arguments directly, never through a shell; propagate failures and timeouts."""
    try:
        result = subprocess.run(
            ["gh", *args], capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=180, check=False,
        )
    except FileNotFoundError as error:
        raise ValueError("GitHub CLI (gh) is required; install it and run gh auth login") from error
    if result.returncode:
        raise ValueError(f"gh {args[0]} failed: {result.stderr.strip()}")
    return result.stdout


def collect(args):
    """Capture the complete PR diff and manifest, checking revisions before and after."""
    if args.pr.isdigit() and int(args.pr) > 0:
        if not args.repo:
            raise ValueError("--repo owner/repository is required for a PR number")
        repo, number = args.repo, args.pr
    else:
        match = re.fullmatch(r"https://github\.com/([^/]+/[^/]+)/pull/([1-9]\d*)/?", args.pr)
        if not match:
            raise ValueError("--pr must be a GitHub PR URL or positive number")
        repo, number = match.groups()
        if args.repo and args.repo != repo:
            raise ValueError("--repo conflicts with the PR URL")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise ValueError("Invalid owner/repository")
    before = json.loads(gh("pr", "view", number, "--repo", repo, "--json", PR_FIELDS))
    merge_base = gh(
        "api", f"repos/{repo}/compare/{before['baseRefOid']}...{before['headRefOid']}",
        "--jq", ".merge_base_commit.sha",
    ).strip()
    if not re.fullmatch(r"[0-9a-f]{40}", merge_base):
        raise ValueError("Unable to resolve the PR comparison merge base")
    pages = json.loads(gh(
        "api", f"repos/{repo}/pulls/{number}/files?per_page=100", "--paginate", "--slurp",
    ))
    files = [
        {
            "path": item["filename"], "status": item["status"],
            "additions": item["additions"], "deletions": item["deletions"],
            **({"previous_path": item["previous_filename"]} if "previous_filename" in item else {}),
            "has_patch": bool(item.get("patch")),
        }
        for page in pages for item in page
    ]
    if len(files) != before["changedFiles"] or len({f["path"] for f in files}) != len(files):
        raise ValueError("Incomplete PR file list; use a full Git comparison before reviewing")
    diff = gh("pr", "diff", number, "--repo", repo, "--color", "never")
    after = json.loads(gh(
        "pr", "view", number, "--repo", repo, "--json", "baseRefOid,headRefOid,changedFiles",
    ))
    if any(before[key] != after[key] for key in after):
        raise ValueError("PR changed during collection; recollect before reviewing")
    notes = [
        f"No API textual patch for {item['path']}; verify full text or binary evidence separately."
        for item in files if not item["has_patch"]
    ]
    snapshot = {
        **before, "mergeBaseOid": merge_base, "repo": repo, "files": files, "diff": diff,
        "collection_notes": notes, "collected_at": datetime.now(timezone.utc).isoformat(),
    }
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.with_suffix(".diff").write_text(diff, encoding="utf-8")
    destination.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Collected {repo}#{number}: {len(files)} files -> {destination}")


def validate(snapshot, review):
    """Validate report structure and coverage without pretending to judge source semantics."""
    for key in ("baseRefOid", "headRefOid", "mergeBaseOid"):
        if not re.fullmatch(r"[0-9a-f]{40}", snapshot[key]):
            raise ValueError(f"Invalid snapshot {key}")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", snapshot["repo"]):
        raise ValueError("Invalid snapshot repository")
    if (review["base_sha"], review["head_sha"]) != (
        snapshot["baseRefOid"], snapshot["headRefOid"],
    ):
        raise ValueError("Review SHAs do not match the collected PR")
    if review["merge_base_sha"] != snapshot["mergeBaseOid"]:
        raise ValueError("Review merge base does not match the PR comparison")
    verdict = review["verdict"]
    if verdict not in {"APPROVE", "COMMENT", "REQUEST_CHANGES"}:
        raise ValueError("Invalid verdict")
    for key in ("strengths", "inspected_files", "context_files", "limitations", "verification"):
        if not isinstance(review[key], list) or not all(isinstance(v, str) for v in review[key]):
            raise ValueError(f"{key} must be a list of strings")
    if not isinstance(review["summary"], str) or not review["summary"].strip():
        raise ValueError("A behavioral summary is required")
    if not review["verification"]:
        raise ValueError("Record actual verification or explicitly state it was not run")
    paths = {item["path"] for item in snapshot["files"]}
    inspected = review["inspected_files"]
    if len(set(inspected)) != len(inspected) or not set(inspected) <= paths:
        raise ValueError("Inspected files must be unique changed paths")
    changes = review["file_changes"]
    if len(changes) != len(paths) or {c["file"] for c in changes} != paths:
        raise ValueError("file_changes must cover each changed path exactly once")
    for change in changes:
        if not isinstance(change["description"], str) or not change["description"].strip():
            raise ValueError("Each file needs a behavioral description")
    known = paths | set(review["context_files"]) | {
        item["previous_path"] for item in snapshot["files"] if "previous_path" in item
    }
    for path in known:
        if path.startswith(("/", "\\")) or ".." in path.split("/") or "\\" in path:
            raise ValueError("Citations must use repository-relative paths")

    def citation(ref):
        if ref["file"] not in known or ref["side"] not in {"head", "base"}:
            raise ValueError("Citation has an unknown path or revision side")
        if type(ref["line"]) is not int or ref["line"] < 1:
            raise ValueError("Citation requires a positive source line number")

    blocking = False
    for finding in review["findings"]:
        citation(finding)
        if finding["priority"] not in {"P0", "P1", "P2", "P3"}:
            raise ValueError("Invalid finding priority")
        for key in ("title", "evidence", "impact", "fix"):
            if not isinstance(finding[key], str) or not finding[key].strip():
                raise ValueError(f"Finding requires {key}")
        blocking |= finding["priority"] in {"P0", "P1"}
    if blocking and verdict != "REQUEST_CHANGES":
        raise ValueError("P0/P1 findings require REQUEST_CHANGES")
    if verdict == "APPROVE" and (
        set(inspected) != paths or review["limitations"] or snapshot["collection_notes"]
    ):
        raise ValueError("APPROVE requires complete coverage and no evidence limitations")
    if not review["flows"]:
        raise ValueError("At least one source-grounded behavioral flow is required")
    for flow in review["flows"]:
        nodes = flow["nodes"]
        ids = {node["id"] for node in nodes}
        if not 1 <= len(nodes) <= 20 or len(ids) != len(nodes):
            raise ValueError("Flows need 1–20 nodes with unique IDs")
        for item in [*nodes, *flow["edges"]]:
            if not isinstance(item["label"], str) or not item["label"].strip():
                raise ValueError("Flow nodes and edges need labels")
            if not item["evidence"]:
                raise ValueError("Every flow node and edge requires source evidence")
            for ref in item["evidence"]:
                citation(ref)
        for node in nodes:
            if node["status"] not in {"added", "modified", "removed", "unchanged"}:
                raise ValueError("Invalid flow node change status")
        for edge in flow["edges"]:
            if edge["from"] not in ids or edge["to"] not in ids:
                raise ValueError("Flow edge refers to an unknown node")


def esc(value):
    return escape(str(value), quote=True)


def list_html(values, empty="None recorded."):
    return "<ul>" + "".join(f"<li class='prose'>{esc(v)}</li>" for v in values) + "</ul>" if values else f"<p class='muted'>{esc(empty)}</p>"


def source_link(snapshot, ref):
    sha = snapshot["headRefOid"] if ref["side"] == "head" else snapshot["mergeBaseOid"]
    url = f"https://github.com/{snapshot['repo']}/blob/{sha}/{quote(ref['file'], safe='/')}#L{ref['line']}"
    label = f"{ref['file']}:{ref['line']} ({ref['side']})"
    return f'<a href="{esc(url)}">{esc(label)}</a>'


def graph_html(snapshot, flow, index):
    """Draw bounded vertical graphs with explicit, cited edges, including branches."""
    colors = {"added": "#dff4e7", "modified": "#fff1d4", "removed": "#fbe3e7", "unchanged": "#e8eef5"}
    positions = {node["id"]: 50 + i * 130 for i, node in enumerate(flow["nodes"])}
    width = 720 + len(flow["edges"]) * 45
    height = 40 + len(flow["nodes"]) * 130
    marker = f"arrow-{index}"
    parts = [
        f'<h3>{esc(flow["title"])}</h3><div class="graph"><svg viewBox="0 0 {width} {height}" role="img" aria-labelledby="flow-{index}">',
        f'<title id="flow-{index}">{esc(flow["title"])}</title>',
        f'<defs><marker id="{marker}" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#526579"/></marker></defs>',
    ]
    for edge_index, edge in enumerate(flow["edges"]):
        start, end = positions[edge["from"]] + 40, positions[edge["to"]] + 40
        lane = 620 + edge_index * 45
        if start == end:
            end += 22
        parts.append(
            f'<path d="M540 {start} H{lane} V{end} H540" fill="none" stroke="#526579" marker-end="url(#{marker})"/>'
            f'<text x="{lane + 12}" y="{min(start, end) + 12}" class="edge-label">E{edge_index + 1}</text>'
        )
    for node in flow["nodes"]:
        y = positions[node["id"]]
        parts.append(f'<rect x="30" y="{y}" width="510" height="80" rx="10" fill="{colors[node["status"]]}" stroke="#bccbd8"/>')
        lines = textwrap.wrap(node["label"], width=58)
        for line_index, line in enumerate(lines[:3]):
            parts.append(f'<text x="48" y="{y + 22 + line_index * 20}" class="flow-label">{esc(line)}</text>')
    parts.append("</svg></div>")
    edge_labels = [
        f'E{i + 1}: {edge["from"]} → {edge["to"]} — {edge["label"]}'
        for i, edge in enumerate(flow["edges"])
    ]
    parts.append(list_html(edge_labels, "This flow has one evidenced step."))
    parts.append("<details><summary>Flow labels and source evidence</summary><ul>")
    for node in flow["nodes"]:
        refs = ", ".join(source_link(snapshot, ref) for ref in node["evidence"])
        parts.append(f'<li><strong>{esc(node["label"])}</strong> · {esc(node["status"])} — {refs}</li>')
    for edge_index, edge in enumerate(flow["edges"]):
        refs = ", ".join(source_link(snapshot, ref) for ref in edge["evidence"])
        parts.append(f'<li>E{edge_index + 1}: {esc(edge["label"])} ({esc(edge["from"])} → {esc(edge["to"])}) — {refs}</li>')
    parts.append("</ul></details>")
    return "".join(parts)


def diff_html(diff):
    """Preserve all captured diff text, grouped by Git file headers without path parsing."""
    sections = re.split(r"(?=^diff --git )", diff, flags=re.MULTILINE)
    rendered = []
    for section in filter(None, sections):
        lines = section.splitlines()
        body = []
        for line in lines:
            css = "hunk" if line.startswith("@@") else "add" if line.startswith("+") else "del" if line.startswith("-") else ""
            body.append(f'<span class="diff-line {css}">{esc(line)}</span>')
        rendered.append(f"<details><summary>{esc(lines[0])}</summary><pre>{''.join(body)}</pre></details>")
    return "".join(rendered) or "<p>No textual diff returned. See file metadata and limitations.</p>"


def render(args):
    snapshot = json.loads(Path(args.snapshot).read_text(encoding="utf-8"))
    review = json.loads(Path(args.review).read_text(encoding="utf-8"))
    validate(snapshot, review)
    findings = []
    for item in sorted(review["findings"], key=lambda f: f["priority"]):
        findings.append(
            f'<article class="card finding"><span class="badge {item["priority"]}">{item["priority"]}</span>'
            f'<h3>{esc(item["title"])}</h3>{source_link(snapshot, item)}'
            f'<p class="prose"><strong>Evidence: </strong>{esc(item["evidence"])}</p>'
            f'<p class="prose"><strong>Impact: </strong>{esc(item["impact"])}</p>'
            f'<p class="prose"><strong>Suggested fix: </strong>{esc(item["fix"])}</p></article>'
        )
    descriptions = {item["file"]: item["description"] for item in review["file_changes"]}
    inspected = set(review["inspected_files"])
    rows = []
    for item in snapshot["files"]:
        previous = f" (from {item['previous_path']})" if "previous_path" in item else ""
        rows.append(
            f'<tr><td>{esc(item["path"] + previous)}</td><td>{esc(item["status"])}</td>'
            f'<td>+{esc(item["additions"])} / −{esc(item["deletions"])}</td>'
            f'<td>{esc(descriptions[item["path"]])}</td><td>{"Inspected" if item["path"] in inspected else "Not inspected"}</td></tr>'
        )
    notes = [*snapshot["collection_notes"], *review["limitations"]]
    missing = [f"Not inspected: {f['path']}" for f in snapshot["files"] if f["path"] not in inspected]
    checks = snapshot.get("statusCheckRollup") or []
    ci = [f"Reported GitHub check: {c.get('name', c.get('context', 'unnamed'))} — {c.get('conclusion') or c.get('status') or c.get('state', 'unknown')}" for c in checks]
    meta = f'{snapshot["repo"]} · PR #{snapshot["number"]} · {snapshot.get("state", "unknown")}'
    url = snapshot["url"]
    if re.fullmatch(r"https://github\.com/[^/]+/[^/]+/pull/[1-9]\d*/?", url):
        meta = f'<a href="{esc(url)}">{esc(meta)}</a>'
    else:
        meta = esc(meta)
    meta += f'<br>Base {esc(snapshot["baseRefOid"])}<br>Head {esc(snapshot["headRefOid"])}'
    meta += f'<br>Comparison merge base {esc(snapshot["mergeBaseOid"])}'
    stats = [
        (len(snapshot["files"]), "Changed files"),
        (len(inspected), "Inspected files"),
        (sum(f["additions"] for f in snapshot["files"]), "Added lines"),
        (len(review["findings"]), "Findings"),
    ]
    values = {
        "TITLE": esc(snapshot["title"]), "META": meta, "VERDICT": review["verdict"],
        "SUMMARY": esc(review["summary"]), "STRENGTHS": list_html(review["strengths"]),
        "STATS": '<div class="stats">' + "".join(f'<div class="stat"><strong>{count}</strong><span class="muted">{label}</span></div>' for count, label in stats) + "</div>",
        "FLOWS": "".join(graph_html(snapshot, flow, i) for i, flow in enumerate(review["flows"])),
        "FINDINGS": "".join(findings) or "<p>No actionable defects identified in inspected scope. See coverage limits.</p>",
        "FILES": '<div class="table-wrap"><table><thead><tr><th>File</th><th>Status</th><th>Lines</th><th>Behavior change</th><th>Coverage</th></tr></thead><tbody>' + "".join(rows) + "</tbody></table></div>",
        "VERIFICATION": list_html([*review["verification"], *ci]),
        "LIMITATIONS": list_html([*notes, *missing], "No evidence limitations recorded."),
        "DIFF": diff_html(snapshot["diff"]),
        "FOOTER": esc(f"Generated {datetime.now(timezone.utc).isoformat()} · Local review using code-reviewer; no GitHub review submitted."),
    }
    template = (Path(__file__).resolve().parents[1] / "assets" / "report-template.html").read_text(encoding="utf-8")
    # Single substitution pass prevents user text resembling template tokens being reprocessed.
    html = re.sub(r"\{\{([A-Z]+)\}\}", lambda match: values[match[1]], template)
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(html, encoding="utf-8")
    print(f"Rendered {review['verdict']} report -> {destination}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    collector = commands.add_parser("collect", help="Read a GitHub PR into a stable snapshot")
    collector.add_argument("--pr", required=True)
    collector.add_argument("--repo")
    collector.add_argument("--output", required=True)
    renderer = commands.add_parser("render", help="Render a reviewed snapshot with the HTML template")
    renderer.add_argument("--snapshot", required=True)
    renderer.add_argument("--review", required=True)
    renderer.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        (collect if args.command == "collect" else render)(args)
    except (ValueError, KeyError, TypeError, OSError, subprocess.TimeoutExpired) as error:
        parser.exit(1, f"Error: {error}\n")


if __name__ == "__main__":
    main()
