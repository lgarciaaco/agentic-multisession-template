#!/usr/bin/env bash
# Clone or update reference repos under repos/ from repos.yaml.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f "$ROOT/repos.yaml" ]]; then
  echo "Error: missing repos.yaml — cp repos.yaml.example repos.yaml and set clone URLs." >&2
  exit 1
fi

python3 <<'PY'
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path("scripts/lib").resolve()))
from git_remotes import configure_repo_remotes, default_fork_user_from_yaml, validate_clone_url
from hub_git import sync_local_branch_to_upstream
from repos import load_repos, repo_base, workspace_root

root = workspace_root()

try:
    repos = load_repos(root)
except FileNotFoundError as exc:
    print(f"Error: {exc}", file=sys.stderr)
    sys.exit(1)

if not repos:
    print("No repos in repos.yaml.")
    sys.exit(0)

fork_user = default_fork_user_from_yaml(root)

for alias, cfg in repos.items():
    dest = repo_base(root, cfg)
    clone_raw = cfg.get("clone")
    branch = cfg.get("default_branch", "main")
    rel = cfg.get("path", ".")

    if rel == ".":
        if not (dest / ".git").exists():
            print(f"Error: hub repo entry '{alias}' (path: .) is not a git repo.", file=sys.stderr)
            sys.exit(1)
        print(f"[fetch] {alias} (hub root)")
        try:
            sha = sync_local_branch_to_upstream(dest, branch)
            print(f"  [sync] {branch} @ {sha}")
        except RuntimeError as exc:
            print(f"  WARNING: {exc}", file=sys.stderr)
        continue

    if not clone_raw:
        print(f"Error: repo '{alias}' needs clone URL in repos.yaml", file=sys.stderr)
        sys.exit(1)

    try:
        clone = validate_clone_url(clone_raw)
    except ValueError as exc:
        print(f"Error: repo '{alias}': {exc}", file=sys.stderr)
        sys.exit(1)

    if (dest / ".git").exists():
        print(f"[fetch] {alias} -> {dest}")
        try:
            sha = sync_local_branch_to_upstream(dest, branch)
            print(f"  [sync] {branch} @ {sha}")
        except RuntimeError as exc:
            print(f"  WARNING: {exc}", file=sys.stderr)
            subprocess.run(["git", "-C", str(dest), "fetch", "origin", "--prune"], check=False)
        current = subprocess.run(
            ["git", "-C", str(dest), "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
        )
        if current.returncode == 0 and current.stdout.strip() != clone:
            subprocess.run(
                ["git", "-C", str(dest), "remote", "set-url", "origin", clone],
                check=True,
            )
        subprocess.run(["git", "-C", str(dest), "checkout", branch], check=False)
        configure_repo_remotes(dest, cfg, default_fork_user=fork_user)
        continue

    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"[clone] {alias} <- {clone}")
    r = subprocess.run(
        ["git", "clone", "--branch", branch, "--", clone, str(dest)],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        print(f"  FAILED: {r.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    configure_repo_remotes(dest, cfg, default_fork_user=fork_user)

print("Done.")
PY
