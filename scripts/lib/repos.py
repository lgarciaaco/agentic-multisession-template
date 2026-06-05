#!/usr/bin/env python3
"""Load repos.yaml from hub root."""

from __future__ import annotations

import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore


def workspace_root() -> Path:
    env = __import__("os").environ.get("WORKSPACE_ROOT", "").strip()
    if env:
        return Path(env)
    return Path(__file__).resolve().parent.parent.parent


def repos_yaml_path(root: Path | None = None) -> Path:
    root = root or workspace_root()
    return root / "repos.yaml"


def load_repos(root: Path | None = None) -> dict:
    path = repos_yaml_path(root)
    if not path.exists():
        example = path.parent / "repos.yaml.example"
        hint = f" Copy {example.name} to repos.yaml." if example.exists() else ""
        raise FileNotFoundError(f"Missing {path}.{hint}")
    text = path.read_text()
    if yaml is not None:
        data = yaml.safe_load(text) or {}
        return data.get("repos", {})
    repos: dict = {}
    current: str | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if line.startswith("  ") and not line.startswith("    ") and stripped.endswith(":"):
            current = stripped[:-1]
            repos[current] = {}
        elif current and line.startswith("    ") and ":" in stripped:
            key, _, val = stripped.partition(":")
            repos[current][key.strip()] = val.strip()
    return repos


def repo_base(root: Path, cfg: dict) -> Path:
    path = cfg.get("path", ".")
    return (root / path).resolve() if path != "." else root.resolve()
