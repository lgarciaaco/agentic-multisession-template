#!/usr/bin/env bash
# Correlation snapshot: chat bindings, tmux panes, active sessions.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export WORKSPACE_ROOT="$ROOT"
FORMAT="report"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --json) FORMAT="json"; shift ;;
    -h|--help)
      echo "Usage: $0 [--json]"
      echo "  One-screen audit: which chats map to which codenames, tmux panes, sessions."
      exit 0
      ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done
exec python3 "$ROOT/scripts/lib/session_cli.py" audit --format "$FORMAT"
