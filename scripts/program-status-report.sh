#!/usr/bin/env bash
# Write artifacts/program-status.md for a program orchestrator parent session.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export WORKSPACE_ROOT="${WORKSPACE_ROOT:-$ROOT}"

CODENAME="${1:?usage: program-status-report.sh <parent-codename> [--reviews-json path]}"
REVIEWS_JSON=""

shift || true
while [[ $# -gt 0 ]]; do
  case "$1" in
    --reviews-json)
      REVIEWS_JSON="${2:?--reviews-json requires a path}"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

python3 - "$CODENAME" "$REVIEWS_JSON" <<'PY'
import json
import sys
from pathlib import Path
import os

root = Path(os.environ["WORKSPACE_ROOT"])
sys.path.insert(0, str(root / "scripts" / "lib"))

from hub_paths import resolve_session_artifact
from program_monitor import monitor_program, render_program_status_markdown
from program_state import load_program
from session_binding import validate_codename

codename = validate_codename(sys.argv[1])
reviews_path = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] else ""
session_dir = root / "sessions" / codename
report = monitor_program(root, codename)
program = load_program(session_dir)
status_path = resolve_session_artifact(session_dir, program.get("status_path") or "artifacts/program-status.md")

child_reviews = None
if reviews_path:
    payload_path = Path(reviews_path)
    if payload_path.is_file():
        child_reviews = json.loads(payload_path.read_text(encoding="utf-8"))

body = render_program_status_markdown(report, child_reviews=child_reviews)
status_path.parent.mkdir(parents=True, exist_ok=True)
status_path.write_text(body, encoding="utf-8")
print(status_path)
PY
