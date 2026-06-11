#!/usr/bin/env python3
"""Advance CI observe loop after polling/fix attempt.

Usage: python3 scripts/workflow-ci-observe-advance.py <codename> <verdict>

Verdicts: GREEN | CONFLICT | TEST_FAILURE | TIMEOUT | FAIL
Prints: iteration, verdict, new phase (one per line).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))

from hub_paths import hub_root  # noqa: E402
from workflow_ci_observe import advance_ci_observe  # noqa: E402


def main() -> None:
    if len(sys.argv) < 3:
        print("usage: workflow-ci-observe-advance.py <codename> <verdict>", file=sys.stderr)
        sys.exit(1)

    codename = sys.argv[1]
    verdict = sys.argv[2]

    root = hub_root()
    session_dir = root / "sessions" / codename

    workflow = advance_ci_observe(session_dir, verdict)
    ci_loop = (workflow.get("loops") or {}).get("ci_observe") or {}
    print(ci_loop.get("iteration", 0))
    print(ci_loop.get("last_verdict", ""))
    print(workflow.get("phase", ""))


if __name__ == "__main__":
    main()
