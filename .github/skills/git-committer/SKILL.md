---
name: git-committer
description: Creates conventional Git commits, handles pre-commit outcomes, and assists with safe branching, rebasing, recovery, and PR workflows. Use when asked to git commit, commit changes, push to github, create branch, rebase, merge, stash, cherry-pick, resolve merge conflict, check git history, create pull request, or update the git-committer skill.
version: 1.2.6
---

# Git Committer

## Core Directives

1. **Verify Identity**: Check the effective identity without changing Git configuration. Report missing or unexpected identity before committing.
2. **Conventional Commits**: Use `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, or `chore:` prefixes.
3. **Atomic Commits**: Stage related changes together; avoid giant "everything" commits.
4. **Summary and Body**: Include a concise summary line and a bulleted body for complex changes.
5. **Keep Hooks Enabled**: Do not bypass hooks or signing to get past a failure or timeout.

## Workflow

### 0. Check for a Recycle Bin report
Use `git --no-optional-locks status --short` for status checks so inspection does not refresh the index on disk.

If a Recycle Bin report names Git metadata, pause writes and let any running Git command finish. Verify live HEAD, staged changes, and working-tree status against the expected state. Resolve the live index with `git rev-parse --path-format=absolute --git-path index`; the index must exist and its sibling `<index>.lock` must be absent. If the intended commit exists, report it without retrying. A report alone establishes neither corruption nor the cause of a failed command.

Stop writes if live metadata is missing, a lock remains, checks fail or show unexpected changes, or the tool prohibits further writes. Otherwise, continue within the user's authorization after diagnosing any failed command and fixing its confirmed cause. Never access or restore recycled items, delete Git metadata, or switch tools to bypass a restriction.

### 1. Check Staged Files
Review status, staged and unstaged diffs, and recent commit messages. Stage only the intended paths, verify the staged diff, and leave unrelated edits and generated files alone.
The hook checks selected staged paths, not all pending edits or repository history. When asked to commit everything, verify the complete pending scope before scanning; do not report repository-wide coverage from a staged scan.

### 2. Check Identity and Record HEAD
Verify the effective identity with `git var GIT_AUTHOR_IDENT` and note the current commit before attempting a commit. An unborn branch has no current commit.

### 3. Check the Pre-Commit Hook
From the repository root, resolve the active hook with `git rev-parse --path-format=absolute --git-path hooks/pre-commit`. Check the resolved file, not `pre-commit.sample` or a tracked installer.

When the repository provides a [security hook installer](../github-security-scanner-hook/SKILL.md) and the active hook is absent, run `scripts/install-hook.py` from that skill directory using the repository's Python environment with the working directory set to the repository root. Install automatically only if the installer can write to the resolved active path; the bundled installer targets `.git/hooks/pre-commit`. Recheck the active hook after installation.

Verify that the active hook invokes the expected scanner, directly or through a hook manager. If an existing hook cannot be verified or installation fails or is unsupported, pause before `git commit` and offer to run the scanner directly on the final staged changes. Do not modify existing hooks without approval or commit if the direct scan fails or reports blocking findings.

Keep the hook's Python in the repository venv. The scanner locates `detect-secrets` and Semgrep in the shared agent venv first; check that environment before installing duplicate tools in the repository venv.

### 4. Stage and Commit
Use a shell-appropriate multi-line commit message pattern.

```bash
git add <paths>
git commit -m "<type>(<scope>): <subject>

- <body>"
```

On Windows PowerShell, prefer a here-string for multi-line commit messages:

```powershell
git add <paths>
$msg = @'
<type>(<scope>): <subject>

- <body>
'@
git commit -m $msg
```

Avoid Bash heredoc patterns like `$(cat <<'EOF' ...)` in PowerShell sessions because they fail to parse.

### 5. Verify the Outcome
Check `git log -1` and `git status --short` after the attempt. If the command times out, is interrupted, or returns an ambiguous error, verify HEAD and the index before retrying. Do not start a second commit while the first is still running. If the intended commit exists, report its hash and any remaining changes.

Report whether the commit output confirmed a hook scan or a direct staged scan ran. Do not infer that the hook ran from commit success alone.

If no commit was created, distinguish a blocking finding from a hook or scanner failure. Fix the reported cause before retrying. When the hook reports built-in fallback after a Semgrep timeout, report the fallback result, not a Semgrep pass. See the reference for recovery details.
If error output is unavailable, isolate the hook and scanner components before another commit attempt. Report a direct component result only for that component; a detect-secrets pass does not establish Semgrep or full-hook completion.

## Resources

- [Conventional Commits](https://www.conventionalcommits.org/)
- [Git Committer Reference](references/git-committer-reference.md)
