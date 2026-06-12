#!/usr/bin/env python3
"""Begin code review loop when implementation tasks are done (M6)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from session_binding import validate_codename  # noqa: E402
from hub_paths import hub_root  # noqa: E402
from workflow_code_review import begin_code_review_loop  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Begin workflow code review loop")
    parser.add_argument("codename", help="Session codename")
    args = parser.parse_args()

    root = hub_root()
    codename = validate_codename(args.codename)
    session_dir = root / "sessions" / codename
    try:
        workflow = begin_code_review_loop(session_dir)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(workflow.get("phase"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
