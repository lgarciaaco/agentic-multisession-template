#!/usr/bin/env bash
# Accept action plan: sync tasks, set gates, phase → implementation, ensure worktrees.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CODENAME="${1:-}"

if [[ -z "$CODENAME" ]]; then
  echo "Usage: $0 <codename>" >&2
  exit 1
fi

cd "$ROOT"
export WORKSPACE_ROOT="$ROOT"
export WORKSPACE_CODENAME="$CODENAME"

python3 <<'PY'
import json
import os
import sys
from pathlib import Path

root = Path(os.environ["WORKSPACE_ROOT"])
sys.path.insert(0, str(root / "scripts" / "lib"))
from session_binding import validate_codename
from workflow_plan import accept_action_plan

codename = validate_codename(os.environ.get("WORKSPACE_CODENAME", ""))
result = accept_action_plan(root, codename)
print(json.dumps(result, indent=2))
PY

./scripts/ensure-worktrees.sh "$CODENAME"
./scripts/sync-session.sh "$CODENAME"
