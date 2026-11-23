---
name: git-committer
description: Creates conventional Git commits and handles pre-commit outcomes. Use when asked to git commit, commit changes, or update the git-committer skill.
version: 1.2.0
---

# Git Committer

## Core Directives

1. **Verify Identity**: Check the effective identity without changing Git configuration. Report missing or unexpected identity before committing.
2. **Conventional Commits**: Use `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, or `chore:` prefixes.
3. **Atomic Commits**: Stage related changes together; avoid giant "everything" commits.
4. **Summary and Body**: Include a concise summary line and a bulleted body for complex changes.
5. **Keep Hooks Enabled**: Do not bypass hooks or signing to get past a failure or timeout.

## Workflow

### 1. Check Staged Files
Review status, staged and unstaged diffs, and recent commit messages. Stage only the intended paths, verify the staged diff, and leave unrelated edits and generated files alone.

### 2. Check Identity and Record HEAD
Verify the effective identity with `git var GIT_AUTHOR_IDENT` and note the current commit before attempting a commit. An unborn branch has no current commit.

### 3. Stage and Commit
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

### 4. Verify the Outcome
Check `git log -1` and `git status --short` after the attempt. If the command times out, is interrupted, or returns an ambiguous error, verify HEAD and the index before retrying. Do not start a second commit while the first is still running. If the intended commit exists, report its hash and any remaining changes.

If no commit was created, distinguish a blocking finding from a hook or scanner failure. Fix the reported cause before retrying. When the hook reports built-in fallback after a Semgrep timeout, report the fallback result, not a Semgrep pass. See the reference for recovery details.

## Resources

- [Conventional Commits](https://www.conventionalcommits.org/)
- [Git Committer Reference](references/git-committer-reference.md)
