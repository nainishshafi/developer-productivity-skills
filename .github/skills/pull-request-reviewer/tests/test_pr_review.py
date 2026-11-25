"""Verify PR snapshot consistency, HTML safety, and evidence/approval guardrails."""

import argparse
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import tempfile
import sys
import unittest
from unittest.mock import patch


SKILL = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("pr_review", SKILL / "scripts" / "pr-review.py")
MODULE = importlib.util.module_from_spec(SPEC)
sys.dont_write_bytecode = True
SPEC.loader.exec_module(MODULE)


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = json.loads((SKILL / "assets" / "sample-snapshot.json").read_text())
        self.review = json.loads((SKILL / "assets" / "sample-review.json").read_text())

    def test_review_revision_and_merge_base_binding(self):
        for key in ("head_sha", "base_sha", "merge_base_sha"):
            review = deepcopy(self.review)
            review[key] = "a" * 40
            with self.subTest(key=key), self.assertRaises(ValueError):
                MODULE.validate(self.snapshot, review)

    def test_approval_requires_nonblocking_complete_review(self):
        self.review["verdict"] = "APPROVE"
        with self.assertRaises(ValueError):
            MODULE.validate(self.snapshot, self.review)
        self.review["findings"] = []
        self.review["limitations"] = []
        MODULE.validate(self.snapshot, self.review)
        self.review["inspected_files"].pop()
        with self.assertRaises(ValueError):
            MODULE.validate(self.snapshot, self.review)

    def test_incomplete_patch_evidence_prevents_approval(self):
        self.review.update(verdict="APPROVE", findings=[], limitations=[])
        self.snapshot["collection_notes"] = ["Binary contents unavailable"]
        with self.assertRaises(ValueError):
            MODULE.validate(self.snapshot, self.review)

    def test_edges_and_citations_require_grounded_references(self):
        for mutate in (
            lambda r: r["flows"][0]["edges"][0].update(to="invented"),
            lambda r: r["flows"][0]["nodes"][0].update(evidence=[]),
            lambda r: r["findings"][0].update(file="../outside.py"),
            lambda r: r["findings"][0].update(line=0),
        ):
            review = deepcopy(self.review)
            mutate(review)
            with self.assertRaises(ValueError):
                MODULE.validate(self.snapshot, review)

    def test_render_escapes_source_and_preserves_template_like_text(self):
        self.snapshot["title"] = '<script>alert(1)</script> {{SUMMARY}}'
        self.snapshot["diff"] += '\n+<img src=x onerror=alert(1)>\n'
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "snapshot.json").write_text(json.dumps(self.snapshot), encoding="utf-8")
            (root / "review.json").write_text(json.dumps(self.review), encoding="utf-8")
            MODULE.render(argparse.Namespace(
                snapshot=root / "snapshot.json", review=root / "review.json",
                output=root / "report.html",
            ))
            html = (root / "report.html").read_text(encoding="utf-8")
        self.assertNotIn("<script>", html)
        self.assertNotIn("<img src=x", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("{{SUMMARY}}", html)
        self.assertIn("Content-Security-Policy", html)
        self.assertIn("<svg", html)
        self.assertIn("Zero quantity still reaches persistence", html)

    def collection_responses(self, changed=False):
        before = {**self.snapshot, "changedFiles": 2}
        pages = [
            [{"filename": "src/new.py", "previous_filename": "src/old.py", "status": "renamed",
              "additions": 1, "deletions": 1, "patch": "@@ -1 +1 @@\n-old\n+new"}],
            [{"filename": "assets/data.bin", "status": "added", "additions": 0, "deletions": 0}],
        ]
        after = {key: before[key] for key in ("baseRefOid", "headRefOid", "changedFiles")}
        if changed:
            after["headRefOid"] = "a" * 40
        return [
            json.dumps(before), before["mergeBaseOid"], json.dumps(pages),
            "diff --git a/src/old.py b/src/new.py\n-old\n+new\n", json.dumps(after),
        ]

    def test_collect_paginated_renames_and_binary_metadata(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(
            MODULE, "gh", side_effect=self.collection_responses(),
        ) as mocked:
            output = Path(folder) / "snapshot.json"
            MODULE.collect(argparse.Namespace(pr="42", repo="example/order-service", output=output))
            snapshot = json.loads(output.read_text())
            self.assertEqual(snapshot["files"][0]["previous_path"], "src/old.py")
            self.assertIn("assets/data.bin", snapshot["collection_notes"][0])
            self.assertEqual(output.with_suffix(".diff").read_text(), snapshot["diff"])
            self.assertIn("--paginate", mocked.call_args_list[2].args)

    def test_collect_rejects_revision_drift_without_writing_snapshot(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(
            MODULE, "gh", side_effect=self.collection_responses(changed=True),
        ):
            output = Path(folder) / "snapshot.json"
            with self.assertRaisesRegex(ValueError, "changed during collection"):
                MODULE.collect(argparse.Namespace(pr="42", repo="example/order-service", output=output))
            self.assertFalse(output.exists())

    def test_collect_rejects_incomplete_file_manifest(self):
        responses = self.collection_responses()
        metadata = json.loads(responses[0])
        metadata["changedFiles"] = 3
        responses[0] = json.dumps(metadata)
        with tempfile.TemporaryDirectory() as folder, patch.object(MODULE, "gh", side_effect=responses):
            with self.assertRaisesRegex(ValueError, "Incomplete PR file list"):
                MODULE.collect(argparse.Namespace(
                    pr="42", repo="example/order-service", output=Path(folder) / "snapshot.json",
                ))

    def test_missing_github_cli_has_actionable_error(self):
        with patch.object(MODULE.subprocess, "run", side_effect=FileNotFoundError):
            with self.assertRaisesRegex(ValueError, "GitHub CLI"):
                MODULE.gh("pr", "view", "42")

    def test_base_source_links_use_merge_base_not_branch_tip(self):
        self.snapshot["baseRefOid"] = "a" * 40
        link = MODULE.source_link(self.snapshot, {"file": "src/orders.py", "line": 2, "side": "base"})
        self.assertIn(self.snapshot["mergeBaseOid"], link)
        self.assertNotIn(self.snapshot["baseRefOid"], link)


if __name__ == "__main__":
    unittest.main()
