#!/usr/bin/env python3
"""Generate delivery-report.md and complete workflow (M7)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from session_binding import validate_codename  # noqa: E402
from hub_paths import hub_root  # noqa: E402
from workflow_delivery import write_delivery_report  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Write workflow delivery report")
    parser.add_argument("codename", help="Session codename")
    parser.add_argument("--title", default=None, help="Override report title")
    args = parser.parse_args()

    root = hub_root()
    codename = validate_codename(args.codename)
    session_dir = root / "sessions" / codename
    if not (session_dir / "workflow.json").exists():
        print("workflow.json not found", file=sys.stderr)
        return 1

    path = write_delivery_report(session_dir, codename=codename, title=args.title)
    print(path)
    print("completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
