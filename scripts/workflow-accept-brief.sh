#!/usr/bin/env bash
# Accept problem brief: set gate, phase → plan_loop.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CODENAME="${1:-}"

if [[ -z "$CODENAME" ]]; then
  echo "Usage: $0 <codename>" >&2
  exit 1
fi

cd "$ROOT"
export WORKSPACE_ROOT="$ROOT"

python3 - "$CODENAME" <<'PY'
import json
import os
import sys
from pathlib import Path

root = Path(os.environ["WORKSPACE_ROOT"])
sys.path.insert(0, str(root / "scripts" / "lib"))
from session_binding import validate_codename
from workflow_inbox_gate import accept_brief

codename = validate_codename(sys.argv[1])
result = accept_brief(root, codename, source="user")
print(json.dumps(result, indent=2))
PY

./scripts/sync-session.sh "$CODENAME"
