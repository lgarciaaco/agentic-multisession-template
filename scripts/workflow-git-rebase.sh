#!/usr/bin/env bash
# Rebase onto origin/<target> with non-interactive editor env (headless CI observe).
set -euo pipefail

export GIT_EDITOR=true
export EDITOR=true

usage() {
  echo "Usage: $(basename "$0") [repo_dir] [target_branch]" >&2
  echo "  repo_dir defaults to current directory; target_branch defaults to main." >&2
  exit 1
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
fi

if [[ $# -ge 1 && -d "$1" ]]; then
  REPO_DIR="$(cd "$1" && pwd)"
  TARGET="${2:-main}"
else
  REPO_DIR="$(pwd)"
  TARGET="${1:-main}"
fi

cd "$REPO_DIR"
git fetch origin "$TARGET"
git rebase "origin/$TARGET"
