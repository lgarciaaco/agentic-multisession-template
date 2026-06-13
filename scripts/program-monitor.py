#!/usr/bin/env python3
"""Monitor active child sessions for a program orchestrator parent."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from hub_paths import hub_root  # noqa: E402
from program_monitor import gate_column_short, monitor_program  # noqa: E402


def _one_line_next(child: dict) -> str:
    if child.get("error"):
        return f"error: {child['error']}"
    hint = child.get("resume_hint") or "—"
    return str(hint).replace("|", "/").replace("\n", " ").strip()


def format_text(report: dict) -> str:
    lines = [
        f"Program monitor — parent `{report['parent']}`",
        f"Generated: {report['generated_at']}",
        "",
        f"Parent next: {report.get('parent_next_action') or '—'}",
        "",
        "| Child | Phase | Gate | Next |",
        "|-------|-------|------|------|",
    ]
    for child in report.get("children") or []:
        gate = gate_column_short(child.get("pending_gate"))
        phase = child.get("phase") or "—"
        codename = child.get("codename") or "—"
        next_line = _one_line_next(child)
        lines.append(f"| `{codename}` | {phase} | {gate} | {next_line} |")
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
