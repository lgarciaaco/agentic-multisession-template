#!/usr/bin/env bash
# Write artifacts/program-status.md for a program orchestrator parent session.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export WORKSPACE_ROOT="${WORKSPACE_ROOT:-$ROOT}"

CODENAME="${1:?usage: program-status-report.sh <parent-codename>}"

python3 - "$CODENAME" <<'PY'
import sys
from pathlib import Path
import os

root = Path(os.environ["WORKSPACE_ROOT"])
sys.path.insert(0, str(root / "scripts" / "lib"))

from hub_paths import resolve_session_artifact
from program_monitor import monitor_program
from program_state import load_program
from session_binding import validate_codename

codename = validate_codename(sys.argv[1])
session_dir = root / "sessions" / codename
report = monitor_program(root, codename)
program = load_program(session_dir)
status_path = resolve_session_artifact(session_dir, program.get("status_path") or "artifacts/program-status.md")

lines = [
    f"# Program status — {codename}",
    "",
    f"Generated: {report['generated_at']}",
    f"Decomposition approved: {report.get('decomposition_approved')}",
    "",
    "## Children",
    "",
    "| Child | Phase | Pending gate | Updated | Resume |",
    "|-------|-------|--------------|---------|--------|",
]

for child in report.get("children") or []:
    gate = child.get("pending_gate") or "—"
    phase = child.get("phase") or "—"
    updated = child.get("last_updated") or "—"
    hint = (child.get("resume_hint") or "—").replace("|", "/")
    if child.get("error"):
        hint = f"error: {child['error']}"
    lines.append(f"| `{child['codename']}` | {phase} | {gate} | {updated} | {hint} |")

lines.extend(["", "## Gate queue", ""])
queue = report.get("gate_queue") or []
if not queue:
    lines.append("_No queued gate events._")
else:
    for item in queue:
        lines.append(
            f"- `{item.get('child_codename')}` @ `{item.get('gate')}` handled={item.get('handled')}"
        )

status_path.parent.mkdir(parents=True, exist_ok=True)
status_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
print(status_path)
PY
