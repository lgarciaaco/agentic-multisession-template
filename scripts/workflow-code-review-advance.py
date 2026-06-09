#!/usr/bin/env python3
"""Advance code review loop after code-reviewer synthesizer (M6)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from session_binding import hub_root, validate_codename  # noqa: E402
from workflow_code_review import (  # noqa: E402
    advance_code_review_loop,
    latest_review_summary,
    read_review_summary,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Advance workflow code review loop")
    parser.add_argument("codename", help="Session codename")
    parser.add_argument(
        "review_id",
        nargs="?",
        default=None,
        help="Review id (r-NNN); default: latest reviews/r-NNN.json",
    )
    parser.add_argument(
        "--verdict",
        default=None,
        help="Override verdict from review summary",
    )
    args = parser.parse_args()

    root = hub_root()
    codename = validate_codename(args.codename)
    session_dir = root / "sessions" / codename

    review_id = args.review_id
    if review_id:
        summary = read_review_summary(session_dir, review_id)
    else:
        latest = latest_review_summary(session_dir)
        if not latest:
            print("No reviews/r-NNN.json found", file=sys.stderr)
            return 1
        review_id, summary = latest

    verdict = str(args.verdict or summary.get("verdict") or "").upper()
    if not verdict:
        print(f"Review {review_id} has no verdict", file=sys.stderr)
        return 1

    workflow = advance_code_review_loop(session_dir, verdict, review_id=review_id)
    code_loop = (workflow.get("loops") or {}).get("code_review") or {}
    print(review_id)
    print(verdict)
    print(workflow.get("phase"))
    print(f"{code_loop.get('iteration', 0)}/{code_loop.get('max', 5)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
