#!/usr/bin/env python3
"""Route parent feedback to a child session tmux pane."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from hub_paths import hub_root  # noqa: E402
from program_route_feedback import route_correction, route_feedback  # noqa: E402
from gate_command_registry import allowed_route_messages, normalize_route_message  # noqa: E402
from program_state import GATE_PHASES  # noqa: E402
from session_binding import validate_codename  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Route parent feedback to child tmux pane via send-keys"
    )
    parser.add_argument("parent", help="Parent session codename")
    parser.add_argument("child", help="Child session codename")
    parser.add_argument(
        "--gate",
        choices=tuple(sorted(GATE_PHASES)),
        help="Gate phase for accept/reopen commands",
    )
    parser.add_argument("--message", required=True, help="Gate command or free-text correction")
    parser.add_argument(
        "--correction",
        action="store_true",
        help="Send free-text brief/plan correction (omit --gate)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print message only")
    args = parser.parse_args()

    if args.gate and args.correction:
        print("use either --gate or --correction, not both", file=sys.stderr)
        return 1

    try:
        if args.gate:
            payload = route_feedback(
                hub_root(),
                parent=args.parent,
                child=args.child,
                gate=args.gate,
                message=args.message,
                dry_run=args.dry_run,
            )
        else:
            normalized = normalize_route_message(args.message)
            for gate in sorted(GATE_PHASES):
                if normalized in allowed_route_messages(gate):
                    print(
                        f"gate command {args.message!r} requires --gate {gate}",
                        file=sys.stderr,
                    )
                    return 1
            payload = route_correction(
                hub_root(),
                parent=args.parent,
                child=args.child,
                message=args.message,
                dry_run=args.dry_run,
            )
    except (ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    child = validate_codename(args.child)
    if args.dry_run:
        print(payload)
        print("dry-run ok")
    else:
        print(f"sent to tmux pane for {child}: {payload}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
