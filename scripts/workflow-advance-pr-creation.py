#!/usr/bin/env python3
"""Advance PR creation phase after commit + draft PR attempt.

Usage: python3 scripts/workflow-advance-pr-creation.py <codename> <verdict> [pr_url]

Verdicts: SUCCESS | RETRY | FAIL
Prints: iteration, verdict, new phase (one per line).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))

from hub_paths import hub_root  # noqa: E402
from workflow_pr_creation import advance_pr_creation  # noqa: E402


def main() -> None:
    if len(sys.argv) < 3:
        print("usage: workflow-advance-pr-creation.py <codename> <verdict> [pr_url]", file=sys.stderr)
        sys.exit(1)

    codename = sys.argv[1]
    verdict = sys.argv[2]
    pr_url = sys.argv[3] if len(sys.argv) > 3 else None

    root = hub_root()
    session_dir = root / "sessions" / codename

    workflow = advance_pr_creation(session_dir, verdict, pr_url=pr_url)
    pr_loop = (workflow.get("loops") or {}).get("pr_creation") or {}
    print(pr_loop.get("iteration", 0))
    print(pr_loop.get("last_verdict", ""))
    print(workflow.get("phase", ""))


if __name__ == "__main__":
    main()
