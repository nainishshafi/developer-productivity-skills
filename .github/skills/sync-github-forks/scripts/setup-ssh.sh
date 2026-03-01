#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------------------------------------------
# setup-ssh.sh — Generate an SSH key and print instructions to add it to GitHub
# ---------------------------------------------------------------------------

KEY_TYPE="${KEY_TYPE:-ed25519}"
KEY_PATH="${KEY_PATH:-$HOME/.ssh/id_$KEY_TYPE}"
EMAIL="${1:-}"

if [[ -z "$EMAIL" ]]; then
  read -rp "Enter your GitHub email address: " EMAIL
fi

# Check if key already exists
if [[ -f "$KEY_PATH" ]]; then
  echo "SSH key already exists at $KEY_PATH"
  echo "Public key:"
  cat "${KEY_PATH}.pub"
  exit 0
fi

echo "Generating $KEY_TYPE SSH key for $EMAIL ..."
ssh-keygen -t "$KEY_TYPE" -C "$EMAIL" -f "$KEY_PATH" -N ""

echo ""
echo "Key generated at $KEY_PATH"

# Start ssh-agent and add key
eval "$(ssh-agent -s)"
ssh-add "$KEY_PATH"

echo ""
echo "---------------------------------------------------------------------"
echo "Add this public key to GitHub:"
echo "  https://github.com/settings/ssh/new"
echo "---------------------------------------------------------------------"
cat "${KEY_PATH}.pub"
echo "---------------------------------------------------------------------"
echo ""
echo "Then test with: ssh -T git@github.com"
