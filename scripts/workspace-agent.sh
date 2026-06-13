#!/usr/bin/env bash
# Start Cursor agent with session picker (use instead of bare `agent` in tmux).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export WORKSPACE_ROOT="$ROOT"
# shellcheck disable=SC1091
source "$ROOT/scripts/lib/hub-env.sh"
ensure_tmux_window_prefix "$(hub_slug_from_root "$ROOT")"

AGENT_ARGS=()
REUSE=0
for arg in "$@"; do
  if [[ "$arg" == "--reuse" ]]; then
    REUSE=1
  elif [[ "$arg" == "--workflow" ]]; then
    AGENT_ARGS+=("/workflow-orchestrator")
  else
    AGENT_ARGS+=("$arg")
  fi
done
ENSURE_ARGS=()
[[ "$REUSE" == 1 ]] && ENSURE_ARGS+=(--reuse)

tmp="$(mktemp "${TMPDIR:-/tmp}/workspace-codename.XXXXXX")"
trap 'rm -f "$tmp"' EXIT
if ! "$ROOT/scripts/ensure-session-interactive.sh" "${ENSURE_ARGS[@]}" >"$tmp"; then
  code=$?
  if [[ "$code" == 130 ]]; then
    exit 130
  fi
  echo "Error: could not select a session." >&2
  exit "$code"
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

export WORKSPACE_CODENAME="$CODENAME"
REPOS_STATE="$(python3 <<'PY' 2>/dev/null || echo "unknown"
import os
import sys
from pathlib import Path
root = Path(os.environ["WORKSPACE_ROOT"])
sys.path.insert(0, str(root / "scripts" / "lib"))
from repos import bootstrap_status
print(bootstrap_status(root)["state"])
PY
)"

case "$REPOS_STATE" in
  needs_clone|ready)
    if ! "$ROOT/scripts/clone-repos.sh"; then
      echo "Warning: clone-repos failed — fix repos.yaml / network." >&2
    elif [[ -f "$ROOT/sessions/$CODENAME/session.json" ]]; then
      if ! "$ROOT/scripts/ensure-worktrees.sh" "$CODENAME"; then
        echo "Warning: ensure-worktrees failed — check tasks[].repo in session.json." >&2
      fi
    fi
    ;;
  no_repos_yaml|empty_registry)
    echo "Note: repos not configured ($REPOS_STATE) — agent should ask before product work." >&2
    ;;
esac

WINDOW_LABEL="${WORKSPACE_TMUX_WINDOW_PREFIX}${CODENAME}"
WT="$(python3 <<'PY' 2>/dev/null || true
import os
import sys
from pathlib import Path
root = Path(os.environ["WORKSPACE_ROOT"])
sys.path.insert(0, str(root / "scripts" / "lib"))
from session_binding import primary_worktree
wt = primary_worktree(root, os.environ.get("WORKSPACE_CODENAME", ""))
print(wt if wt else "")
PY
)"
if [[ -n "$WT" ]]; then
  echo "Session: $CODENAME | worktree: $WT (tmux: $WINDOW_LABEL)" >&2
else
  echo "Session: $CODENAME (tmux: $WINDOW_LABEL)" >&2
fi
export GIT_EDITOR=true
export EDITOR=true
if [[ -z "${WORKSPACE_AGENT_NO_TTY:-}" && -r /dev/tty && -w /dev/tty ]]; then
  exec "$AGENT_BIN" "${AGENT_ARGS[@]}" </dev/tty >/dev/tty 2>&1
fi
exec "$AGENT_BIN" "${AGENT_ARGS[@]}"
