---
name: sync-github-forks
description: Use when the user asks to "sync github forks", "sync forks", "pull all my forks", or wants to clone and pull all their GitHub forked repositories automatically across Windows, Linux, or macOS.
version: 1.0.0
---

# Sync GitHub Forks

Sync all GitHub forks for the authenticated user by cloning missing repositories and pulling existing ones via the `gh` CLI.

> **IMPORTANT:** Both cross-platform scripts are **already bundled with this skill**. Do NOT create new script files. Detect the OS and run the bundled script:
> - **Windows (PowerShell)** → `.github/skills/sync-github-forks/scripts/sync-forks.ps1`
> - **Linux / macOS (Bash)** → `.github/skills/sync-github-forks/scripts/sync-forks.sh`

## Prerequisites

- [`gh` CLI](https://cli.github.com) installed and authenticated (`gh auth login`)
- `git` on `PATH`
- **Linux / macOS only:** `jq` on `PATH` (Windows PowerShell uses built-in `ConvertFrom-Json`)
- SSH key configured with GitHub (for clone/pull via SSH)

## Usage

**Windows (PowerShell):**
```powershell
# Optional: override clone location (default: ~\git-repos)
$env:BASE_DIR = "$env:USERPROFILE\code"

pwsh .github/skills/sync-github-forks/scripts/sync-forks.ps1
```

**Linux / macOS (Bash):**
```bash
# Optional: override clone location (default: ~/git-repos)
export BASE_DIR=~/code

bash .github/skills/sync-github-forks/scripts/sync-forks.sh
```

## What the Script Does

1. Checks required CLI tools (`gh` and `git`, plus `jq` on Linux/macOS).
2. Derives your GitHub username automatically via `gh api user`.
3. Paginates `GET /user/repos?type=forks&per_page=100&page=N` via `gh api` until all forks are fetched.
4. For each fork:
   - Local directory exists → `git pull origin <current-branch>` (fast-forward).
   - Local directory missing → `git clone <ssh_url> $BASE_DIR/<name>`.
5. Prints a final summary: `Done — cloned N, pulled N, failed N`.

## Key Decisions

- `gh` CLI handles authentication — no `GITHUB_TOKEN` environment variable required.
- Username is derived at runtime from `gh api user` — no hardcoded configuration.
- SSH clone URLs are used so no token is embedded in the remote URL.
- Pagination ensures all forks are fetched beyond the 100-repo API limit.

## Verification

1. Run `gh auth status` — confirm you are logged in.
2. Run the appropriate bundled script for your OS (see Usage above).
3. Confirm repositories are cloned or updated in `BASE_DIR`.

## Additional Resources

- **`references/sync-github-forks-reference.md`** — Pagination mechanics, SSH vs HTTPS troubleshooting, and cron/Task Scheduler automation.
- **`scripts/sync-forks.ps1`** — Windows PowerShell implementation.
- **`scripts/sync-forks.sh`** — Linux / macOS Bash implementation.
