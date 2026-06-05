#!/usr/bin/env bash
set -euo pipefail
input=$(cat)
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
export WORKSPACE_ROOT="$ROOT" HOOK_INPUT="$input"
exec python3 "$ROOT/scripts/lib/session_cli.py" hook-session-end
