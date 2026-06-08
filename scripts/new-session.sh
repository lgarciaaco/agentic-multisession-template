#!/usr/bin/env bash
# Create a new codename session: sessions/<codename>/
# Optional: ./scripts/new-session.sh [codename] [title]
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export WORKSPACE_ROOT="${WORKSPACE_ROOT:-$ROOT}"
if [[ -n "${1:-}" ]]; then
  export WORKSPACE_NEW_SESSION_NAME="$1"
fi
if [[ -n "${2:-}" ]]; then
  export WORKSPACE_NEW_SESSION_TITLE="$2"
fi

python3 <<'PY'
import os
import sys
from pathlib import Path

root = Path(os.environ["WORKSPACE_ROOT"])
sys.path.insert(0, str(root / "scripts" / "lib"))
from session_binding import CodenameAllocationError, create_new_session

name = os.environ.get("WORKSPACE_NEW_SESSION_NAME", "").strip() or None
title = os.environ.get("WORKSPACE_NEW_SESSION_TITLE", "").strip() or None
try:
    codename = create_new_session(root, name, title)
except CodenameAllocationError as exc:
    print(f"Error: {exc}", file=sys.stderr)
    sys.exit(1)
except SystemExit as exc:
    raise SystemExit(exc.code if exc.code is not None else 1) from exc

print(codename)
PY
