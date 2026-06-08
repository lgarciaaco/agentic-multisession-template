#!/usr/bin/env bash
# Configure origin (upstream) + fork remotes per repos.yaml.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

exec python3 scripts/lib/git_remotes.py "$@"
