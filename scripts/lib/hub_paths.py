"""Shared hub path resolution and session artifact containment."""

from __future__ import annotations

import os
from pathlib import Path


def hub_root() -> Path:
    env = os.environ.get("WORKSPACE_ROOT", "").strip()
    if env:
        return Path(env)
    return Path(__file__).resolve().parent.parent.parent


def resolve_session_artifact(session_dir: Path, rel: str) -> Path:
    """Resolve a workflow artifact path; must stay under session_dir."""
    rel_clean = rel.strip().lstrip("/")
    if not rel_clean or ".." in Path(rel_clean).parts:
        raise ValueError(f"invalid artifact path: {rel!r}")
    resolved = (session_dir / rel_clean).resolve()
    session_resolved = session_dir.resolve()
    try:
        resolved.relative_to(session_resolved)
    except ValueError as exc:
        raise ValueError(
            f"artifact path must stay under {session_dir}: {rel!r}"
        ) from exc
    return resolved


def resolve_review_workspace(root: Path, codename: str, workspace_arg: str) -> Path:
    """Resolve workspace path; must stay under sessions/<codename>/reviews/workspace/."""
    rel = workspace_arg.strip().lstrip("/")
    parts = Path(rel).parts
    expected = ("sessions", codename, "reviews", "workspace")
    if len(parts) < len(expected) or parts[: len(expected)] != expected:
        raise ValueError(
            f"workspace must be under sessions/{codename}/reviews/workspace/: {workspace_arg}"
        )
    if ".." in parts:
        raise ValueError(f"workspace path must not contain ..: {workspace_arg}")
    resolved = (root / rel).resolve()
    allowed = (root / "sessions" / codename / "reviews" / "workspace").resolve()
    try:
        resolved.relative_to(allowed)
    except ValueError as exc:
        raise ValueError(
            f"workspace must resolve under sessions/{codename}/reviews/workspace/"
        ) from exc
    return resolved
