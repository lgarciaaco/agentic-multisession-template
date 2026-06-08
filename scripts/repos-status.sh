#!/usr/bin/env bash
# Agent-facing repos + hub bootstrap status (JSON on stdout).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export WORKSPACE_ROOT="$ROOT"
python3 -c "
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path('scripts/lib').resolve()))
from repos import bootstrap_status
print(json.dumps(bootstrap_status(), indent=2))
"
