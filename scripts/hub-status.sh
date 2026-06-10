#!/usr/bin/env bash
# Agent-facing hub template version check (JSON on stdout).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export WORKSPACE_ROOT="$ROOT"

FETCH=1
while [[ $# -gt 0 ]]; do
  case "$1" in
    --cached-only) FETCH=0 ;;
    -h|--help)
      cat <<'EOF'
Usage: ./scripts/hub-status.sh [--cached-only]

Compare installed `.hub-version` to upstream template releases (JSON on stdout).
Default: fetch upstream into .hub-upstream-cache/
--cached-only: use cache only (no network)

When installed version is 1.0.0-rc.1, treat it as the first stable candidate line.
EOF
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
  esac
  shift
done

export HUB_STATUS_FETCH="$FETCH"
python3 -c "
import json
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path('scripts/lib').resolve()))
from hub_upgrade import hub_status
fetch = os.environ.get('HUB_STATUS_FETCH', '1') != '0'
print(json.dumps(hub_status(fetch=fetch), indent=2))
"
