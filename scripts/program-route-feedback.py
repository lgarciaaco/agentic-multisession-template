#!/usr/bin/env python3
"""Route parent gate feedback to a child session inbox."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from hub_paths import hub_root  # noqa: E402
from program_route_feedback import route_feedback  # noqa: E402
from session_binding import validate_codename  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Route parent feedback to child inbox")
    parser.add_argument("parent", help="Parent session codename")
    parser.add_argument("child", help="Child session codename")
    parser.add_argument("--gate", required=True, choices=("brief_review", "plan_user_review"))
    parser.add_argument("--message", required=True, help="Gate feedback message")
    parser.add_argument("--dry-run", action="store_true", help="Print payload only")
    args = parser.parse_args()

    try:
        route_feedback(
            hub_root(),
            parent=args.parent,
            child=args.child,
            gate=args.gate,
            message=args.message,
            dry_run=args.dry_run,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.dry_run:
        print("dry-run ok")
    else:
        print(f"routed to sessions/_inbox/{validate_codename(args.child)}.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
