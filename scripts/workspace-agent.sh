#!/usr/bin/env bash
# Start Cursor agent with session picker (use instead of bare `agent` in tmux).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export WORKSPACE_ROOT="$ROOT"

AGENT_ARGS=()
REUSE=0
for arg in "$@"; do
  if [[ "$arg" == "--reuse" ]]; then
    REUSE=1
  else
    AGENT_ARGS+=("$arg")
  fi
done
ENSURE_ARGS=()
[[ "$REUSE" == 1 ]] && ENSURE_ARGS+=(--reuse)

tmp="$(mktemp "${TMPDIR:-/tmp}/workspace-codename.XXXXXX")"
trap 'rm -f "$tmp"' EXIT
if ! "$ROOT/scripts/ensure-session-interactive.sh" "${ENSURE_ARGS[@]}" >"$tmp"; then
  echo "Error: could not select a session." >&2
  exit 1
fi
CODENAME="$(<"$tmp")"
if [[ -z "$CODENAME" ]]; then
  echo "Error: empty session codename." >&2
  exit 1
fi

AGENT_BIN="${WORKSPACE_AGENT_BIN:-agent}"
if ! command -v "$AGENT_BIN" >/dev/null 2>&1; then
  echo "Error: '$AGENT_BIN' not found. Install Cursor agent CLI or set WORKSPACE_AGENT_BIN." >&2
  exit 1
fi

WINDOW_LABEL="$CODENAME"
if [[ -n "${WORKSPACE_TMUX_WINDOW_PREFIX:-}" ]]; then
  WINDOW_LABEL="${WORKSPACE_TMUX_WINDOW_PREFIX}${CODENAME}"
fi
echo "Session: $CODENAME (tmux: $WINDOW_LABEL)" >&2
if [[ -r /dev/tty && -w /dev/tty ]]; then
  exec "$AGENT_BIN" "${AGENT_ARGS[@]}" </dev/tty >/dev/tty 2>&1
fi
exec "$AGENT_BIN" "${AGENT_ARGS[@]}"
