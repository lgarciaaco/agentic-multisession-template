#!/usr/bin/env bash
# Bootstrap program child sessions after decomposition approval.
# Usage: ./scripts/program-bootstrap-children.sh <parent> [--approve]
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export WORKSPACE_ROOT="$ROOT"
exec python3 "$ROOT/scripts/program-bootstrap-children.py" "$@"
