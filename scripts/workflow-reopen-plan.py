#!/usr/bin/env python3
"""Reopen action plan gate (M7)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from session_binding import validate_codename  # noqa: E402
from hub_paths import hub_root  # noqa: E402
from workflow_resume import reopen_plan, workflow_next_action  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Reopen workflow plan gate")
    parser.add_argument("codename", help="Session codename")
    args = parser.parse_args()

    root = hub_root()
    codename = validate_codename(args.codename)
    session_dir = root / "sessions" / codename
    if not (session_dir / "workflow.json").exists():
        print("workflow.json not found", file=sys.stderr)
        return 1

    try:
        workflow = reopen_plan(session_dir)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(workflow.get("phase"))
    print(workflow_next_action(workflow))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
