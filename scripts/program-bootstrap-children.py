#!/usr/bin/env python3
"""Bootstrap program child sessions and open tmux tabs when available."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from hub_paths import hub_root  # noqa: E402
from program_bootstrap import bootstrap_children  # noqa: E402
from program_child_tabs import DEFAULT_WORKFLOW_PROMPT  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bootstrap program child sessions after decomposition approval"
    )
    parser.add_argument("parent", help="Parent session codename")
    parser.add_argument(
        "--approve",
        action="store_true",
        help="Mark decomposition approved and bootstrap proposed_children",
    )
    parser.add_argument(
        "--workflow-prompt",
        default=DEFAULT_WORKFLOW_PROMPT,
        help="Initial agent prompt for child tabs (default: /workflow-orchestrator)",
    )
    args = parser.parse_args()

    root = hub_root()
    try:
        result = bootstrap_children(
            root,
            args.parent,
            approve=args.approve,
            workflow_prompt=args.workflow_prompt,
        )
    except (ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
