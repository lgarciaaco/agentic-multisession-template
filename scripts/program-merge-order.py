#!/usr/bin/env python3
"""Suggest child PR merge order for a program orchestrator parent."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from hub_paths import hub_root  # noqa: E402
from program_merge_order import merge_order  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Compute child PR merge order")
    parser.add_argument("codename", help="Parent session codename")
    parser.add_argument("--format", choices=("json", "text"), default="json")
    args = parser.parse_args()
    try:
        report = merge_order(hub_root(), args.codename)
    except (ValueError, FileNotFoundError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if args.format == "text":
        print(f"Merge order for `{report['parent']}`:")
        for idx, name in enumerate(report["merge_sequence"], start=1):
            print(f"{idx}. {name}")
        for note in report.get("notes") or []:
            print(f"note: {note}")
    else:
        print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
