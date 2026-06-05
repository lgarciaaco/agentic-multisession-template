#!/usr/bin/env python3
"""Minimal git helpers for monorepo session worktrees (no forks / multi-repo)."""

from __future__ import annotations

import subprocess
from pathlib import Path


def _run(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=check,
    )


def fetch_upstream(repo_dir: Path) -> None:
    """Fetch all refs from origin."""
    if not (repo_dir / ".git").exists():
        raise FileNotFoundError(f"Not a git repo: {repo_dir}")
    result = _run(repo_dir, "fetch", "origin", "--prune", check=False)
    if result.returncode != 0:
        raise RuntimeError(
            f"git fetch failed in {repo_dir}: {result.stderr.strip() or result.stdout.strip()}"
        )


def upstream_ref(repo_dir: Path, branch: str) -> str:
    """Return origin/<branch> when present after fetch."""
    ref = f"origin/{branch}"
    if _run(repo_dir, "rev-parse", "--verify", ref, check=False).returncode != 0:
        raise RuntimeError(
            f"{ref} not found in {repo_dir}. Check base_branch or add a remote."
        )
    return ref


def resolve_worktree_start_ref(repo_dir: Path, base_branch: str) -> tuple[str, str]:
    """Fetch upstream and return (start_ref, short_sha) for git worktree add."""
    fetch_upstream(repo_dir)
    ref = upstream_ref(repo_dir, base_branch)
    sha = _run(repo_dir, "rev-parse", "--short", ref).stdout.strip()
    return ref, sha
