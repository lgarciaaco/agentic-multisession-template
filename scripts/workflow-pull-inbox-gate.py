#!/usr/bin/env python3
"""Pull session inbox and apply workflow gate feedback when correlated."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from session_binding import hub_root, validate_codename  # noqa: E402
from workflow_inbox_gate import GATE_PHASES, pull_inbox_gate  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Pull inbox messages correlated with workflow user gates",
    )
    parser.add_argument("codename", help="Session codename")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply the first pending gate action (default: report only)",
    )
    args = parser.parse_args()

    root = hub_root()
    codename = validate_codename(args.codename)
    session_dir = root / "sessions" / codename
    if not (session_dir / "workflow.json").exists():
        print("workflow.json not found", file=sys.stderr)
        return 1

    try:
        result = pull_inbox_gate(root, codename, apply=args.apply)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2))

    if args.apply and result.get("applied"):
        applied = result["applied"][0]
        action = applied.get("action")
        if action == "accept_plan":
            subprocess.run(
                ["./scripts/ensure-worktrees.sh", codename],
                cwd=root,
                check=False,
            )
        subprocess.run(
            ["./scripts/sync-session.sh", codename],
            cwd=root,
            check=False,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
