#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------------------------------------------
# sync-forks.sh — Clone or pull all GitHub forks for a user
# Requires: gh CLI (authenticated), jq, git
# ---------------------------------------------------------------------------

# Check dependencies
for cmd in gh jq git; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "Error: '$cmd' is required but not found on PATH. Install it and retry." >&2
    exit 1
  fi
done

# Derive username from gh CLI
GITHUB_USERNAME=$(gh api user --jq '.login')

BASE_DIR="${BASE_DIR:-$HOME/git-repos}"
mkdir -p "$BASE_DIR"

cloned=0
pulled=0
failed=0
page=1

echo "Fetching forks for $GITHUB_USERNAME ..."

while true; do
  repos=$(gh api "user/repos?type=forks&per_page=100&page=$page")

  count=$(echo "$repos" | jq 'length')
  [[ "$count" -eq 0 ]] && break

  while IFS= read -r repo; do
    name=$(echo "$repo" | jq -r '.name')
    ssh_url=$(echo "$repo" | jq -r '.ssh_url')
    local_dir="$BASE_DIR/$name"

    if [[ -d "$local_dir" ]]; then
      branch=$(git -C "$local_dir" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")
      if git -C "$local_dir" pull origin "$branch" --ff-only 2>&1; then
        echo "  [pulled]  $name"
        ((pulled++)) || true
      else
        echo "  [failed]  $name (pull error)" >&2
        ((failed++)) || true
      fi
    else
      if git clone "$ssh_url" "$local_dir" 2>&1; then
        echo "  [cloned]  $name"
        ((cloned++)) || true
      else
        echo "  [failed]  $name (clone error)" >&2
        ((failed++)) || true
      fi
    fi
  done < <(echo "$repos" | jq -c '.[]')

  ((page++)) || true
done

echo ""
echo "Done — cloned $cloned, pulled $pulled, failed $failed"
