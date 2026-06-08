#!/usr/bin/env python3
"""Load repos.yaml from hub root."""

from __future__ import annotations

from pathlib import Path

import yaml


def workspace_root() -> Path:
    env = __import__("os").environ.get("WORKSPACE_ROOT", "").strip()
    if env:
        return Path(env)
    return Path(__file__).resolve().parent.parent.parent


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

    return {
        "state": "ready",
        "repos": list(repos.keys()),
        "hub_launcher_installed": launcher.exists(),
        "agent_action": (
            "Repos cloned. Bind or create a session; add tasks with tasks[].repo matching "
            "repos.yaml keys; ./scripts/ensure-worktrees.sh <codename> before product edits."
        ),
        "hub_setup_remaining": hub_steps,
    }
