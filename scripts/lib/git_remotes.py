#!/usr/bin/env python3
"""Configure git remotes: upstream on origin, user fork on fork (GitHub fork workflow)."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

FORK_REMOTE_NAME = "fork"
UPSTREAM_REMOTE_NAME = "origin"
_GIT_TIMEOUT_SEC = 300
_CLONE_URL_RE = re.compile(
    r"^(?:git@[^:]+:[^\s]+|(?:https?|ssh|file)://[^\s]+)$"
)


def validate_clone_url(url: str) -> str:
    """Return a safe git remote/clone URL or raise ValueError."""
    candidate = url.strip()
    if not candidate or "\n" in candidate or "\r" in candidate:
        raise ValueError(f"invalid clone URL: {url!r}")
    if candidate.startswith("-"):
        raise ValueError(f"invalid clone URL: {url!r}")
    if not _CLONE_URL_RE.fullmatch(candidate):
        raise ValueError(f"invalid clone URL: {url!r}")
    return candidate


def fork_clone_url(cfg: dict, default_fork_user: str = "") -> str | None:
    """Return fork remote URL when GitHub fork workflow applies."""
    if cfg.get("remote") != "github":
        return None
    explicit = cfg.get("fork")
    if explicit:
        return validate_clone_url(explicit)
    name = cfg.get("name")
    if not name:
        return None
    user = cfg.get("fork_user") or default_fork_user
    if not user:
        return None
    return validate_clone_url(f"git@github.com:{user}/{name}.git")


def _run(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=check,
        timeout=_GIT_TIMEOUT_SEC,
    )


def _remote_exists(repo: Path, name: str) -> bool:
    return _run(repo, "remote", "get-url", name, check=False).returncode == 0


def configure_repo_remotes(
    repo_dir: Path,
    cfg: dict,
    *,
    default_fork_user: str = "",
) -> None:
    """Set origin=upstream; fork=user fork (push default) when fork URL is configured."""
    if not (repo_dir / ".git").exists():
        raise FileNotFoundError(f"Not a git repo: {repo_dir}")

    upstream = validate_clone_url(cfg["clone"])
    fork_url = fork_clone_url(cfg, default_fork_user)

    if _remote_exists(repo_dir, UPSTREAM_REMOTE_NAME):
        _run(repo_dir, "remote", "set-url", UPSTREAM_REMOTE_NAME, upstream)
    else:
        _run(repo_dir, "remote", "add", UPSTREAM_REMOTE_NAME, upstream)

    if fork_url:
        _run(
            repo_dir,
            "config",
            f"remote.{UPSTREAM_REMOTE_NAME}.pushurl",
            "no_push_to_upstream",
            check=False,
        )
        if _remote_exists(repo_dir, FORK_REMOTE_NAME):
            _run(repo_dir, "remote", "set-url", FORK_REMOTE_NAME, fork_url)
        else:
            _run(repo_dir, "remote", "add", FORK_REMOTE_NAME, fork_url)
        _run(repo_dir, "config", "remote.pushDefault", FORK_REMOTE_NAME)
        return

    _run(repo_dir, "config", "--unset", f"remote.{UPSTREAM_REMOTE_NAME}.pushurl", check=False)
    _run(repo_dir, "config", "--unset", "remote.pushDefault", check=False)
    if _remote_exists(repo_dir, FORK_REMOTE_NAME):
        _run(repo_dir, "remote", "remove", FORK_REMOTE_NAME, check=False)


def default_fork_user_from_yaml(root: Path) -> str:
    from repos import load_hub_config

    try:
        data = load_hub_config(root)
    except FileNotFoundError:
        return ""
    user = data.get("github_fork_user") or data.get("fork_user") or ""
    return user.strip() if isinstance(user, str) else ""


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from repos import load_repos, repo_base, workspace_root

    root = workspace_root()
    repos = load_repos(root)
    fork_user = default_fork_user_from_yaml(root)

    if len(argv) >= 3 and Path(argv[1]).exists():
        alias = argv[2]
        if alias not in repos:
            print(f"Unknown repo: {alias}", file=sys.stderr)
            return 1
        configure_repo_remotes(Path(argv[1]).resolve(), repos[alias], default_fork_user=fork_user)
        print(f"[remotes] {alias} -> {argv[1]}")
        return 0

    aliases = [a for a in argv[1:] if a in repos] if len(argv) > 1 else list(repos.keys())
    for alias in aliases:
        if alias not in repos:
            print(f"Unknown repo: {alias}", file=sys.stderr)
            return 1
        cfg = repos[alias]
        if cfg.get("path") == ".":
            print(f"[skip] {alias}: hub root entry")
            continue
        repo_dir = repo_base(root, cfg)
        if not (repo_dir / ".git").exists():
            print(f"[skip] {alias}: no clone at {repo_dir}")
            continue
        configure_repo_remotes(repo_dir, cfg, default_fork_user=fork_user)
        fork = fork_clone_url(cfg, fork_user) or "(push origin)"
        print(f"[remotes] {alias}: origin=upstream fork={fork}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
