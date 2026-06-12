#!/usr/bin/env python3
"""Minimal git helpers for hub session worktrees (fetch + worktree base ref)."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

_BRANCH_RE = re.compile(r"^[a-zA-Z0-9._/-]+$")
_GIT_TIMEOUT_SEC = 300


def _validate_branch(branch: str) -> str:
    name = branch.strip()
    if not name or ".." in name or name.startswith("-") or not _BRANCH_RE.fullmatch(name):
        raise ValueError(f"invalid git branch name: {branch!r}")
    return name


def _run(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=check,
        timeout=_GIT_TIMEOUT_SEC,
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
    branch = _validate_branch(branch)
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


def sync_local_branch_to_upstream(repo_dir: Path, branch: str) -> str:
    """Fetch origin and fast-forward checked-out branch to origin/<branch>. Returns short SHA."""
    branch = _validate_branch(branch)
    fetch_upstream(repo_dir)
    ref = upstream_ref(repo_dir, branch)
    current = _run(repo_dir, "branch", "--show-current", check=False).stdout.strip()
    if current != branch:
        checkout = _run(repo_dir, "checkout", branch, check=False)
        if checkout.returncode != 0:
            msg = checkout.stderr.strip() or checkout.stdout.strip() or "checkout failed"
            raise RuntimeError(f"could not checkout {branch} in {repo_dir}: {msg}")
    result = _run(repo_dir, "merge", "--ff-only", ref, check=False)
    if result.returncode != 0:
        msg = result.stderr.strip() or result.stdout.strip() or "merge --ff-only failed"
        raise RuntimeError(f"could not fast-forward {branch} in {repo_dir}: {msg}")
    return _run(repo_dir, "rev-parse", "--short", branch).stdout.strip()
