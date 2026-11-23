import contextlib
import io
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
            "check_tool": lambda *_: True,
            "run_detect_secrets": lambda *_: [],
            "resolve_semgrep": lambda _: Path("semgrep"),
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
