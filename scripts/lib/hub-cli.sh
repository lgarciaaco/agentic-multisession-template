#!/usr/bin/env bash
# Shared setup for workspace hub CLI wrappers.
set -euo pipefail

_hub_cli_setup() {
  ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
  cd "$ROOT"
  export WORKSPACE_ROOT="$ROOT"
  CLI="$ROOT/scripts/lib/session_cli.py"
}

hub_cli() {
  _hub_cli_setup
  python3 "$CLI" "$@"
}
