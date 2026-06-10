#!/usr/bin/env python3
"""Load repos.yaml from hub root."""

from __future__ import annotations

import functools
import re
import subprocess
from pathlib import Path

import yaml

from hub_paths import hub_root

_GIT_TIMEOUT_SEC = 300


def workspace_root() -> Path:
    """Alias for hub_root — single canonical resolver."""
    return hub_root()


def repos_yaml_path(root: Path | None = None) -> Path:
    root = root or workspace_root()
    return root / "repos.yaml"


def load_hub_config(root: Path | None = None) -> dict:
    path = repos_yaml_path(root)
    if not path.exists():
        example = path.parent / "repos.yaml.example"
        hint = f" Copy {example.name} to repos.yaml." if example.exists() else ""
        raise FileNotFoundError(f"Missing {path}.{hint}")
    data = yaml.safe_load(path.read_text()) or {}
    return data if isinstance(data, dict) else {}


def load_repos(root: Path | None = None) -> dict:
    data = load_hub_config(root)
    repos = data.get("repos")
    return repos if isinstance(repos, dict) else {}


def load_guidelines(root: Path | None = None) -> dict:
    """Optional guidelines pointers from repos.yaml (project doc, worktree CONTRIBUTING)."""
    try:
        data = load_hub_config(root)
    except FileNotFoundError:
        return {}
    guidelines = data.get("guidelines")
    return guidelines if isinstance(guidelines, dict) else {}


def _path_under_root(root: Path, rel: str) -> Path | None:
    """Resolve rel under hub root; None if it escapes."""
    if not rel or not isinstance(rel, str):
        return None
    candidate = (root / rel).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate


def project_guideline_rel(guidelines: dict) -> str:
    """Hub-relative project guidelines path from repos.yaml (project canonical; doc alias)."""
    for key in ("project", "doc"):
        val = guidelines.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return "docs/PROJECT.md"


def normalize_git_url(url: str) -> str:
    """Canonical host/path for comparing clone URLs (ssh, https, scp, .git suffix)."""
    raw = url.strip().rstrip("/")
    if raw.endswith(".git"):
        raw = raw[:-4]
    scp = re.match(r"git@([^:]+):(.+)", raw)
    if scp:
        return f"{scp.group(1).lower()}/{scp.group(2).lower()}"
    http = re.match(r"https?://([^/]+)/(.+)", raw)
    if http:
        return f"{http.group(1).lower()}/{http.group(2).lower()}"
    ssh_url = re.match(r"ssh://(?:git@)?([^/]+)/(.+)", raw)
    if ssh_url:
        return f"{ssh_url.group(1).lower()}/{ssh_url.group(2).lower()}"
    return raw.lower()


@functools.lru_cache(maxsize=8)
def _hub_origin_url_cached(root_str: str) -> str:
    root = Path(root_str)
    if not (root / ".git").exists():
        return ""
    result = subprocess.run(
        ["git", "-C", str(root), "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
        check=False,
        timeout=_GIT_TIMEOUT_SEC,
    )
    if result.returncode != 0:
        return ""
    return normalize_git_url(result.stdout.strip())


def hub_origin_url(root: Path | None = None) -> str:
    """Normalized origin URL for the hub root git repo, or empty if unavailable."""
    root = (root or workspace_root()).resolve()
    return _hub_origin_url_cached(str(root))


@functools.lru_cache(maxsize=8)
def _self_hosted_aliases_cached(root_str: str) -> tuple[str, ...]:
    root = Path(root_str)
    origin = _hub_origin_url_cached(root_str)
    if not origin:
        return ()
    aliases: list[str] = []
    try:
        repos = load_repos(root)
    except FileNotFoundError:
        return ()
    for alias, cfg in repos.items():
        clone = cfg.get("clone")
        if isinstance(clone, str) and normalize_git_url(clone) == origin:
            aliases.append(alias)
    return tuple(aliases)


def self_hosted_aliases(root: Path | None = None) -> list[str]:
    """Registry aliases whose clone URL matches the hub origin (hub is the product)."""
    root = (root or workspace_root()).resolve()
    return list(_self_hosted_aliases_cached(str(root)))


def repo_base(root: Path, cfg: dict) -> Path:
    path = cfg.get("path", ".")
    root = root.resolve()
    if path == ".":
        return root
    base = (root / path).resolve()
    try:
        base.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"repo path must stay under hub root: {path!r}") from exc
    return base


def bootstrap_status(root: Path | None = None) -> dict:
    """Agent-facing hub + repos readiness (run via ./scripts/repos-status.sh)."""
    root = root or workspace_root()
    path = repos_yaml_path(root)
    launcher = root / ".hub-launcher"

    if not path.exists():
        return {
            "state": "no_repos_yaml",
            "repos": [],
            "agent_action": (
                "Ask the user which product repos to register (alias, git clone URL, "
                "default_branch). Then create repos.yaml from repos.yaml.example and fill entries."
            ),
            "user_prompt_hint": "Which repos should this hub track? Give alias + git URL per repo.",
        }

    repos = load_repos(root)
    if not repos:
        return {
            "state": "empty_registry",
            "repos": [],
            "agent_action": (
                "repos.yaml exists but repos: {} is empty. Ask the user for repos to add "
                "(alias, clone URL, default_branch). Edit repos.yaml, then ./scripts/clone-repos.sh."
            ),
            "user_prompt_hint": "repos.yaml is empty — which repos should I add?",
        }

    missing_clone: list[str] = []
    ready: list[str] = []
    for alias, cfg in repos.items():
        base = repo_base(root, cfg)
        if (base / ".git").exists():
            ready.append(alias)
        else:
            missing_clone.append(alias)

    if missing_clone:
        return {
            "state": "needs_clone",
            "repos": list(repos.keys()),
            "ready": ready,
            "missing_clone": missing_clone,
            "agent_action": "Run ./scripts/clone-repos.sh (needs network and valid clone URLs).",
        }

    hub_steps: list[str] = []
    if not launcher.exists():
        hub_steps.append("pip install -r scripts/requirements.txt")
        hub_steps.append("./scripts/install-workspace-agent.sh")

    self_hosted = self_hosted_aliases(root)
    if self_hosted:
        agent_action = (
            f"Self-hosted hub ({', '.join(self_hosted)}). Add tasks[].repo, "
            f"./scripts/ensure-worktrees.sh <codename>, edit worktrees/ — not hub root product paths. "
            f"Hub layer refresh: ./scripts/hub-upgrade.sh only."
        )
    else:
        agent_action = (
            "Repos cloned. Bind or create a session; add tasks with tasks[].repo matching "
            "repos.yaml keys; ./scripts/ensure-worktrees.sh <codename> before product edits."
        )

    payload: dict = {
        "state": "ready",
        "repos": list(repos.keys()),
        "hub_launcher_installed": launcher.exists(),
        "agent_action": agent_action,
        "hub_setup_remaining": hub_steps,
    }
    if self_hosted:
        payload["self_hosted"] = True
        payload["self_hosted_aliases"] = self_hosted
    return payload
