#!/usr/bin/env bash
# Regenerate a multi-root .code-workspace file from repos.yaml.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# shellcheck source=lib/hub-env.sh
source "$(dirname "$0")/lib/hub-env.sh"

SLUG="$(hub_slug_from_root "$ROOT")"
export WORKSPACE_ROOT="$ROOT"
DEFAULT_WS="$ROOT/${SLUG}.code-workspace"
export WORKSPACE_FILE="${1:-$DEFAULT_WS}"

python3 <<'PY'
import json
import os
import sys
from pathlib import Path

root = Path(os.environ["WORKSPACE_ROOT"]).resolve()
sys.path.insert(0, str(root / "scripts" / "lib"))
from repos import load_repos

try:
    repos = load_repos(root)
except FileNotFoundError as exc:
    print(f"Error: {exc}", file=sys.stderr)
    sys.exit(1)

out = Path(os.environ["WORKSPACE_FILE"]).resolve()
if ".." in Path(os.environ["WORKSPACE_FILE"]).parts:
    print("Error: workspace path must not contain ..", file=sys.stderr)
    sys.exit(1)
if out != root and root not in out.parents:
    print(f"Error: workspace file must be under hub root ({root})", file=sys.stderr)
    sys.exit(1)

folders = [{"name": "hub", "path": "."}]
for alias, cfg in sorted(repos.items()):
    rel = cfg.get("path", ".")
    if rel == ".":
        continue
    folders.append({"name": f"repo-{alias}", "path": rel})

workspace = {
    "folders": folders,
    "settings": {"files.exclude": {"**/.git": True}},
}

out.write_text(json.dumps(workspace, indent=2) + "\n")
print(f"Wrote {out} ({len(folders)} folders)")
PY
