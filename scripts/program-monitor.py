#!/usr/bin/env python3
"""Monitor active child sessions for a program orchestrator parent."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from hub_paths import hub_root  # noqa: E402
from program_monitor import monitor_program  # noqa: E402


def format_text(report: dict) -> str:
    lines = [
        f"Program monitor — parent `{report['parent']}`",
        f"Generated: {report['generated_at']}",
        "",
        f"Parent next: {report.get('parent_next_action') or '—'}",
        "",
    ]
    for child in report.get("children") or []:
        gate = child.get("pending_gate") or "—"
        lines.append(
            f"- `{child['codename']}` phase={child.get('phase')} pending_gate={gate}"
        )
        if child.get("error"):
            lines.append(f"  error: {child['error']}")
        review = child.get("gate_review")
        if review:
            present = "present" if review.get("artifact_present") else "missing"
            lines.append(f"  review: {review.get('artifact_path')} ({present})")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Monitor program child sessions")
    parser.add_argument("codename", help="Parent session codename")
    parser.add_argument("--format", choices=("json", "text"), default="json")
    args = parser.parse_args()
    try:
        report = monitor_program(hub_root(), args.codename)
    except (ValueError, FileNotFoundError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if args.format == "text":
        print(format_text(report), end="")
    else:
        print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
