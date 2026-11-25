# Pull Request Reviewer

Review a GitHub pull request with [code-reviewer](../code-reviewer/SKILL.md) and produce an offline HTML report from a reusable template. The agent performs the assessment and authors the behavioral diagrams; the Python CLI collects evidence, validates report inputs, and renders the HTML.

The report includes:

- A verdict and behavioral summary.
- Source-cited before/after flow diagrams, including relevant failure paths.
- P0–P3 findings with evidence, impact, and focused fixes.
- Changed-file descriptions, inspection coverage, verification, and limitations.
- Expandable unified diffs.

## Requirements

- Python 3.10+ with the standard library; use the repository virtual environment for all Python commands.
- The [code-reviewer skill](../code-reviewer/SKILL.md), including relevant language and domain modules.
- Authenticated GitHub CLI (`gh`) for live PR collection. Confirm availability with `gh --version` and authentication with `gh auth status`.

Rendering, tests, and synthetic previews do not require `gh`. This workspace uses `.\.venv\Scripts\python.exe`; use the configured Python environment when running in another repository.

## Agent usage

```text
Use Skill: pull-request-reviewer https://github.com/OWNER/REPOSITORY/pull/123
```

Follow [SKILL.md](SKILL.md) for the full workflow and [the report contract](references/report-contract.md) for the review JSON format.

For a local commit, request `Use Skill: pull-request-reviewer the last commit`. The agent can compare the commit against its parent with read-only Git commands and identify the report as a commit review. The CLI's `collect` command accepts GitHub PRs; it does not provide a commit selector. Commit citations should refer to the exact reviewed source, with embedded local evidence when remote source links are unavailable.

## Output layout

Run the following examples from the workspace root. Save final HTML under `reports/pull-request-reviewer/`. The workspace's `/reports/` ignore rule excludes generated reports from Git.

Keep snapshot JSON, supporting diffs, and agent-authored review JSON in a temporary directory outside the workspace. The renderer creates the report directory when needed.

```powershell
$skillRoot = Join-Path (Get-Location) '.github\skills\pull-request-reviewer'
$scratchRoot = Join-Path ([System.IO.Path]::GetTempPath()) ('pr-review-' + [guid]::NewGuid().ToString('N'))
$reportRoot = Join-Path (Get-Location) 'reports\pull-request-reviewer'
```

## Collect, review, and render

Collect a PR using its number and repository:

```powershell
.\.venv\Scripts\python.exe "$skillRoot\scripts\pr-review.py" collect --pr 123 --repo OWNER/REPOSITORY --output "$scratchRoot\snapshot.json"
```

A PR URL can replace `--pr 123 --repo OWNER/REPOSITORY`. The collector records base, head, and comparison merge-base SHAs, fetches paginated file metadata, and writes `snapshot.json` with a neighboring `snapshot.diff`. It fails if revisions move during collection or the file manifest is incomplete.

Next, have the agent inspect the complete diff and surrounding source at those revisions using `code-reviewer`. Save its findings, inspection coverage, verification evidence, and source-grounded graphs to `$scratchRoot\review.json`, following [the report contract](references/report-contract.md). Review JSON is authored by the agent; neither CLI command generates review findings.

Render the report:

```powershell
.\.venv\Scripts\python.exe "$skillRoot\scripts\pr-review.py" render --snapshot "$scratchRoot\snapshot.json" --review "$scratchRoot\review.json" --output "$reportRoot\pr-123-review.html"
```

Open the HTML and verify the flow, citations, findings, and expandable diffs. It works offline without JavaScript, external images, or CDN resources. Source links for PR reports point to the recorded GitHub revisions.

## Template preview

Render the included synthetic inputs without a GitHub connection:

```powershell
.\.venv\Scripts\python.exe "$skillRoot\scripts\pr-review.py" render --snapshot "$skillRoot\assets\sample-snapshot.json" --review "$skillRoot\assets\sample-review.json" --output "$reportRoot\pull-request-reviewer-preview.html"
```

The preview demonstrates presentation only. Its repository, revisions, code, and findings are synthetic; source links do not point to real commits.

## Verification and current constraints

```powershell
.\.venv\Scripts\python.exe "$skillRoot\tests\test_pr_review.py"
```

The tests use temporary files and mocked GitHub responses to check pagination, revision drift, merge-base links, verdict rules, source references, and HTML escaping. They do not establish live GitHub integration.

- Always give the collector a `.json` output filename. A `.diff` output currently collides with the supporting diff path.
- Missing API patches generate collection notes. The current validator blocks `APPROVE` whenever those notes remain, including after additional source inspection.
- Structural validation checks references and coverage declarations; the agent must verify that citations and claims match the actual source.
- Collection does not execute PR code. A local report does not submit a review, comment, approval, merge, or push to GitHub.

## Files

| Path | Purpose |
|---|---|
| [SKILL.md](SKILL.md) | Agent execution instructions |
| [scripts/pr-review.py](scripts/pr-review.py) | Snapshot collection and HTML rendering |
| [assets/report-template.html](assets/report-template.html) | Reusable HTML layout |
| [references/report-contract.md](references/report-contract.md) | Review JSON and evidence contract |
| [assets/sample-snapshot.json](assets/sample-snapshot.json) | Synthetic snapshot |
| [assets/sample-review.json](assets/sample-review.json) | Synthetic review and flow graphs |
| [tests/test_pr_review.py](tests/test_pr_review.py) | Collector and renderer regression checks |
