#!/usr/bin/env python3
"""Enrich code-reviewer scope_manifest with workflow acceptance criteria (M6)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from session_binding import validate_codename  # noqa: E402
from hub_paths import hub_root  # noqa: E402
from workflow_code_review import enrich_scope_manifest, resolve_code_review_workspace  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Add workflow acceptance criteria to scope_manifest.json"
    )
    parser.add_argument("codename", help="Session codename")
    parser.add_argument(
        "workspace",
        help="Workspace path relative to hub root (sessions/<codename>/reviews/workspace/...)",
    )
    args = parser.parse_args()

    root = hub_root()
    codename = validate_codename(args.codename)
    session_dir = root / "sessions" / codename
    try:
        workspace = resolve_code_review_workspace(root, codename, args.workspace)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    manifest_path = workspace / "scope_manifest.json"
    if not manifest_path.exists():
        print(f"Missing {manifest_path}", file=sys.stderr)
        return 1

    enrich_scope_manifest(manifest_path, session_dir, codename=codename)
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
