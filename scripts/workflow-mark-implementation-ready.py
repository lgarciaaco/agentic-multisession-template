#!/usr/bin/env python3
"""Mark an implementation task slice ready — conductor auto-enters code review next."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from session_binding import validate_codename  # noqa: E402
from hub_paths import hub_root  # noqa: E402
from workflow_code_review import (  # noqa: E402
    begin_code_review_loop,
    mark_implementation_ready,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Mark task slice ready and begin code review loop"
    )
    parser.add_argument("codename", help="Session codename")
    parser.add_argument("task_id", help="Task id from action plan (e.g. t1)")
    parser.add_argument(
        "--mark-only",
        action="store_true",
        help="Only set ready_for_review; do not transition phase",
    )
    args = parser.parse_args()

    root = hub_root()
    codename = validate_codename(args.codename)
    session_dir = root / "sessions" / codename
    try:
        mark_implementation_ready(session_dir, args.task_id)
        if args.mark_only:
            print("ready")
            return 0
        workflow = begin_code_review_loop(session_dir, task_id=args.task_id)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(workflow.get("phase"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
