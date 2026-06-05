#!/usr/bin/env bash
# Create git worktrees for a session from session.json tasks (monorepo hub).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CODENAME="${1:-}"

if [[ -z "$CODENAME" ]]; then
  echo "Usage: $0 <codename>" >&2
  exit 1
fi

cd "$ROOT"

if [[ ! -d "$ROOT/.git" ]]; then
  echo "Error: hub root is not a git repo — init git before ensure-worktrees." >&2
  exit 1
fi

python3 <<PY
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path("scripts/lib").resolve()))
from hub_git import resolve_worktree_start_ref

root = Path("$ROOT").resolve()
codename = "$CODENAME"
session_path = root / "sessions" / codename / "session.json"

if not session_path.exists():
    print(f"Error: missing {session_path}", file=sys.stderr)
    sys.exit(1)

session = json.loads(session_path.read_text())
tasks = session.get("tasks", [])

if not tasks:
    print("No tasks in session.json — add tasks first.")
    sys.exit(0)

base = root
if not (base / ".git").exists():
    print(f"Error: not a git repo: {base}", file=sys.stderr)
    sys.exit(1)

for task in tasks:
    alias = (task.get("id") or "project").strip()
    if not alias:
        continue

    wt_dest = root / "sessions" / codename / "worktrees" / alias
    branch = task.get("feature_branch")
    base_branch = task.get("base_branch") or "main"

    task["worktree"] = f"sessions/{codename}/worktrees/{alias}"

    if wt_dest.exists():
        print(f"[skip] worktree exists: {wt_dest}")
        continue

    wt_dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        start_ref, base_sha = resolve_worktree_start_ref(base, base_branch)
    except (RuntimeError, FileNotFoundError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    cmd = ["git", "-C", str(base), "worktree", "add", str(wt_dest)]
    if branch:
        cmd.extend(["-b", branch, start_ref])
    else:
        cmd.append(start_ref)

    label = branch or base_branch
    print(f"[add] {alias} -> {wt_dest} (branch: {label}, base: {start_ref} @ {base_sha})")
    subprocess.run(cmd, check=True)

session_path.write_text(json.dumps(session, indent=2) + "\n")
print("Done.")
PY
