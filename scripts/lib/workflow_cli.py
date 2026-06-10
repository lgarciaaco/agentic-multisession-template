"""Shared CLI bootstrap for workflow-*.py entry scripts."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable

from session_binding import hub_root, validate_codename


def workflow_session_dir(codename: str) -> tuple[Path, Path]:
    """Return (hub_root, sessions/<codename>) after validating codename."""
    root = hub_root()
    name = validate_codename(codename)
    session_dir = root / "sessions" / name
    return root, session_dir


def run_workflow_main(handler: Callable[[Path, Path], int], codename: str) -> int:
    """Validate codename, ensure workflow.json exists, invoke handler(root, session_dir)."""
    try:
        root, session_dir = workflow_session_dir(codename)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    workflow_path = session_dir / "workflow.json"
    if not workflow_path.exists():
        print(f"Error: missing {workflow_path} — start /workflow first", file=sys.stderr)
        return 1
    return handler(root, session_dir)
