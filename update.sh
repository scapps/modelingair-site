#!/usr/bin/env bash
# Rebuild the site from the vault and push it to GitHub Pages.
# Usage: ./update.sh            (or double-click after `chmod +x update.sh`)
set -euo pipefail
cd "$(dirname "$0")"
python3 build.py
git add -A
if git diff --cached --quiet; then
  echo "Site already up to date; nothing to push."
else
  git commit -q -m "Update site from vault $(date +%Y-%m-%d)"
  git push
  echo "Pushed. GitHub Pages will refresh in about a minute."
fi
