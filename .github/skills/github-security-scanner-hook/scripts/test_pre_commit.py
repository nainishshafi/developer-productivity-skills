import contextlib
import io
import json
import os
import runpy
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parent
INSTALLER = runpy.run_path(str(SCRIPTS / "install-hook.py"))
SCANNER = runpy.run_path(str(SCRIPTS / "scan-staged.py"))


class HookInstallerTests(unittest.TestCase):
    def test_upgrade_preserves_unmanaged_lines_and_is_idempotent(self):
        prefix = "#!/usr/bin/env bash\nset -e\n"
        suffix = "echo after\n"
        old = f"{prefix}{INSTALLER['HOOK_START']}\nold\n{INSTALLER['HOOK_END']}\n{suffix}"
        stanza = INSTALLER["build_hook_stanza"]("/scanner.py", "/python")
        refresh = INSTALLER["refresh_hook_stanza"]
        expected = prefix + stanza.lstrip("\n") + suffix
        self.assertEqual(refresh(old, stanza), expected)
        self.assertEqual(refresh(expected, stanza), expected)
        self.assertIsNone(refresh("# mentions github-security-scanner-hook\n", stanza))
        for invalid in (INSTALLER["HOOK_START"] + "\n", old + old, INSTALLER["HOOK_END"] + "\n"):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                refresh(invalid, stanza)

    def test_generated_hook_with_git(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True, capture_output=True)
            script = repo / "scanner's $test.py"
            hook = repo / ".git" / "hooks" / "pre-commit"
            stanza = INSTALLER["build_hook_stanza"](str(script), sys.executable)
            INSTALLER["write_hook"](hook, "#!/usr/bin/env bash\nset -e\n" + stanza + "echo after\n")
            command = ["git", "-c", "core.hooksPath=.git/hooks", "hook", "run", "pre-commit"]
            cases = (
                (None, 1, "script not found"),
                (0, 0, "after"),
                (1, 1, "HIGH severity"),
                (2, 0, "MEDIUM/LOW"),
                (3, 1, "scanner failed (exit 3)"),
            )
            for scanner_exit, expected, message in cases:
                with self.subTest(scanner_exit=scanner_exit):
                    if scanner_exit is not None:
                        script.write_text(f"raise SystemExit({scanner_exit})\n", encoding="utf-8")
                    result = subprocess.run(
                        command, cwd=repo, stdin=subprocess.DEVNULL,
                        capture_output=True, text=True, timeout=10,
                    )
                    output = result.stdout + result.stderr
                    self.assertEqual(result.returncode, expected, output)
                    self.assertIn(message, output)
                    self.assertEqual("after" in output, expected == 0)


class ScannerTimeoutTests(unittest.TestCase):
    def test_scanner_discovery_prefers_shared_installation(self):
        resolve = SCANNER["resolve_tool"]
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            shared = home / ".gemini" / "agent-venv" / ("Scripts" if os.name == "nt" else "bin")
            shared.mkdir(parents=True)
            for name in ("detect-secrets", "semgrep"):
                executable = shared / (f"{name}.exe" if os.name == "nt" else name)
                executable.touch(0o755)
                with self.subTest(name=name), patch.object(Path, "home", return_value=home):
                    self.assertEqual(resolve(name), executable.resolve())

    def test_detect_secrets_keeps_baseline_unchanged_and_reports_new_findings(self):
        scan = SCANNER["run_detect_secrets"]
        with tempfile.TemporaryDirectory() as tmp:
            baseline = Path(tmp) / ".secrets.baseline"
            known = {"type": "TestDetector", "hashed_secret": "known", "line_number": 1}
            new = {**known, "hashed_secret": "new", "line_number": 2}
            original = json.dumps({"results": {"example.py": [known]}})
            baseline.write_text(original, encoding="utf-8")

            def run(cmd):
                copy = Path(cmd[cmd.index("--baseline") + 1])
                self.assertNotEqual(copy, baseline)
                copy.write_text(json.dumps({"results": {"example.py": [known, new]}}), encoding="utf-8")
                return subprocess.CompletedProcess(cmd, 0, "", "")

            original_path = Path
            with patch.dict(scan.__globals__, {
                "Path": lambda name: baseline if name == ".secrets.baseline" else original_path(name),
                "run": run,
            }):
                findings = scan(Path("detect-secrets"), ["example.py"])
            self.assertEqual([finding["line"] for finding in findings], [2])
            self.assertEqual(baseline.read_text(encoding="utf-8"), original)

    def test_timeout_does_not_wait_for_grandchild_output(self):
        command = [
            sys.executable, "-c",
            "import subprocess, sys, time; "
            "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(4)']); "
            "time.sleep(5)",
        ]
        started = time.monotonic()
        result = SCANNER["run"](command, timeout=1)
        self.assertEqual(result.returncode, 124)
        self.assertLess(time.monotonic() - started, 3)

    def test_semgrep_timeout_runs_builtin_rules(self):
        main = SCANNER["main"]
        completed = subprocess.CompletedProcess(["semgrep"], 124, "", "timed out")
        with patch.object(sys, "argv", ["scan-staged.py"]), patch.dict(main.__globals__, {
            "ensure_in_git_repo": lambda: None,
            "get_git_files": lambda _: [__file__],
            "run_detect_secrets": lambda *_: [],
            "resolve_tool": Path,
            "run": lambda _: completed,
        }), patch.dict(main.__globals__, {
            "run_builtin_fallback": unittest.mock.Mock(return_value=[]),
        }), contextlib.redirect_stderr(io.StringIO()) as stderr, contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as exit_status:
                main()
            self.assertEqual(exit_status.exception.code, 0)
            main.__globals__["run_builtin_fallback"].assert_called_once_with(
                [__file__], SCANNER["BUILTIN_PROMPT_RULES"] + SCANNER["BUILTIN_CODE_RULES"],
            )
            self.assertIn("timed out", stderr.getvalue())
            self.assertIn("using built-in", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
