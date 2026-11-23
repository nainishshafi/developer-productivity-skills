# Git Committer Reference

This reference provides detailed guidance for using the `git-committer` skill.

## Conventional Commit Types

| Type | Description |
| :--- | :--- |
| `feat` | A new feature |
| `fix` | A bug fix |
| `docs` | Documentation only changes |
| `style` | Changes that do not affect the meaning of the code |
| `refactor` | A code change that neither fixes a bug nor adds a feature |
| `perf` | A code change that improves performance |
| `test` | Adding missing tests or correcting existing tests |
| `chore` | Changes to the build process or auxiliary tools and libraries |

## Commit Message Template

```text
<type>(<scope>): <short summary>

- <detailed bullet point 1>
- <detailed bullet point 2>
```

## Shell-Safe Multi-Line Commit Commands

For Bash-compatible shells:

```bash
git commit -F - <<'EOF'
feat(scope): short summary

- detail 1
- detail 2
EOF
```

For Windows PowerShell:

```powershell
$msg = @'
feat(scope): short summary

- detail 1
- detail 2
'@
git commit -m $msg
```

Do not use Bash heredoc syntax such as `$(cat <<'EOF' ...)` in PowerShell, because it is not valid there.

## Troubleshooting Identity Issues

If you see:
`fatal: unable to auto-detect email address`

Confirm the failure with `git var GIT_AUTHOR_IDENT`. Report the missing identity and stop without editing Git configuration.

## Troubleshooting Pre-Commit Checks

- **Timeout or interruption:** Check whether the commit process is still active. Once it exits, compare HEAD with the pre-attempt commit and inspect `git status --short`. Do not retry if the intended commit already exists. Do not delete Git lock files as part of a routine retry.
- **Scanner fallback:** A Semgrep timeout is not a clean Semgrep result. If the hook runs built-in rules in its place, report those results and mention the reduced coverage.
- **Blocking finding or scanner failure:** Keep the hook enabled. Fix the finding or diagnose the missing or broken scanner. For hooks managed by `github-security-scanner-hook`, the updated installer can refresh its marked block without replacing surrounding hook logic; run it only when authorized to change the hook.
- **Missing error output:** Confirm HEAD first, then run `git hook run pre-commit` or the repository scanner directly using the local venv. If diagnostics remain unavailable, isolate scanner components and inspect flagged locations without printing secret values. Do not repeat the same failed commit blindly or invent a root cause.
- **Recycle Bin reports:** Inspect only live Git state; never search or restore recycled metadata. An intact live index and a verified new HEAD can coexist with a report. Distinguish commit outcome from scanner coverage, and obey explicit tool restrictions.
