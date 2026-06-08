#!/usr/bin/env bash
# Create git worktrees for a session from session.json tasks + repos.yaml.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CODENAME="${1:-}"

if [[ -z "$CODENAME" ]]; then
  echo "Usage: $0 <codename>" >&2
  exit 1
fi

cd "$ROOT"
export WORKSPACE_ROOT="$ROOT"
export WORKSPACE_CODENAME="${1:-}"

if [[ ! -f "$ROOT/repos.yaml" ]]; then
  echo "Error: missing repos.yaml — cp repos.yaml.example repos.yaml" >&2
  exit 1
fi

python3 <<'PY'
import json
import os
import subprocess
import sys
from pathlib import Path

root = Path(os.environ["WORKSPACE_ROOT"])
sys.path.insert(0, str(root / "scripts" / "lib"))
from git_remotes import configure_repo_remotes, default_fork_user_from_yaml
from hub_git import resolve_worktree_start_ref
from repos import load_repos, repo_base
from session_binding import validate_codename

try:
    codename = validate_codename(os.environ.get("WORKSPACE_CODENAME", ""))
except ValueError as exc:
    print(f"Error: {exc}", file=sys.stderr)
    sys.exit(1)
session_path = root / "sessions" / codename / "session.json"

if not session_path.exists():
    print(f"Error: missing {session_path}", file=sys.stderr)
    sys.exit(1)

try:
    repos = load_repos(root)
except FileNotFoundError as exc:
    print(f"Error: {exc}", file=sys.stderr)
    sys.exit(1)

session = json.loads(session_path.read_text())
tasks = session.get("tasks", [])
fork_user = default_fork_user_from_yaml(root)

if not tasks:
    print("No tasks in session.json — add tasks first.")
    sys.exit(0)

for task in tasks:
    alias = task.get("repo")
    if not alias:
        print(f"Error: task {task.get('id', '?')} missing 'repo' (repos.yaml key)", file=sys.stderr)
        sys.exit(1)
    if alias not in repos:
        print(f"Error: unknown repo '{alias}' in task {task.get('id')}", file=sys.stderr)
        sys.exit(1)

    cfg = repos[alias]
    base = repo_base(root, cfg)
    if not (base / ".git").exists():
        print(f"Error: reference clone missing: {base}", file=sys.stderr)
        print("Run: ./scripts/clone-repos.sh", file=sys.stderr)
        sys.exit(1)

    wt_dest = root / "sessions" / codename / "worktrees" / alias
    branch = task.get("feature_branch")
    base_branch = task.get("base_branch") or cfg.get("default_branch", "main")

    task["worktree"] = f"sessions/{codename}/worktrees/{alias}"

    if wt_dest.exists():
        print(f"[skip] worktree exists: {wt_dest}")
        configure_repo_remotes(wt_dest, cfg, default_fork_user=fork_user)
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
    configure_repo_remotes(wt_dest, cfg, default_fork_user=fork_user)

session_path.write_text(json.dumps(session, indent=2) + "\n")
print("Done.")
PY
