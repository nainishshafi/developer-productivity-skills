# Report contract

The collector writes `snapshot.json` and a neighboring `.diff` file. The JSON embeds the same diff so the renderer needs only the snapshot and the review. Required snapshot fields are `repo`, `number`, `title`, `url`, `body`, `baseRefOid`, `headRefOid`, `mergeBaseOid`, `files`, `diff`, and `collection_notes`. PR/check metadata is retained as returned by `gh`.

Each file has `path`, `status`, `additions`, `deletions`, and optional `previous_path`. Treat the snapshot as immutable; the reviewer supplies this separate structure:

```json
{
  "base_sha": "COPY snapshot.baseRefOid",
  "head_sha": "COPY snapshot.headRefOid",
  "merge_base_sha": "COPY snapshot.mergeBaseOid",
  "verdict": "COMMENT",
  "summary": "Concrete before/after behavior and practical impact.",
  "strengths": ["A verified property of the implementation."],
  "inspected_files": ["src/service.py"],
  "context_files": ["src/caller.py"],
  "limitations": ["Explain unavailable evidence or unresolved questions."],
  "verification": ["Not run — static inspection only."],
  "file_changes": [
    {"file": "src/service.py", "description": "What changed and why it matters."}
  ],
  "findings": [
    {
      "priority": "P2",
      "title": "Concrete defect",
      "file": "src/service.py",
      "line": 12,
      "side": "head",
      "evidence": "Observed source logic and triggering input.",
      "impact": "Observable failure or regression.",
      "fix": "Smallest useful correction."
    }
  ],
  "flows": [
    {
      "title": "After — request handling",
      "nodes": [
        {
          "id": "request",
          "label": "Validate request",
          "status": "modified",
          "evidence": [{"file": "src/service.py", "line": 12, "side": "head"}]
        },
        {
          "id": "caller",
          "label": "Return result",
          "status": "unchanged",
          "evidence": [{"file": "src/caller.py", "line": 20, "side": "head"}]
        }
      ],
      "edges": [
        {
          "from": "request",
          "to": "caller",
          "label": "Valid request",
          "evidence": [{"file": "src/caller.py", "line": 18, "side": "head"}]
        }
      ]
    }
  ]
}
```

Use full recorded SHAs, positive source line numbers, exact repository-relative paths, and `base`/`head` sides. The `base` citation side resolves to `mergeBaseOid`, the ancestor used by GitHub's three-dot PR comparison; `baseRefOid` is retained to detect base-branch movement. `context_files` explicitly identifies inspected unchanged source used for citations. Renamed files may cite `previous_path` at the merge-base SHA. Verify citations against fetched source; structural validation cannot prove the semantic accuracy of claims.

`file_changes` must cover every changed path exactly once. `inspected_files` lists changed paths actually inspected, without duplicates. Uninspected paths appear automatically in the report and forbid `APPROVE`. `limitations` and snapshot `collection_notes` also forbid `APPROVE`. P0/P1 findings require `REQUEST_CHANGES`. All other verdicts depend on evidence and professional judgment.

Supply at least one grounded flow. If insufficient source evidence makes that impossible, document the blocker and obtain the missing context before rendering. Empty findings are valid; do not create cosmetic findings to fill the layout. Summaries, verification, and limitations are plain text, not HTML.
