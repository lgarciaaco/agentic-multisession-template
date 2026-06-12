#!/usr/bin/env python3
"""Synthesize plan review from workspace findings/plan.json (M4)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from session_binding import validate_codename  # noqa: E402
from hub_paths import hub_root  # noqa: E402
from workflow_plan import (  # noqa: E402
    load_workflow,
    persist_plan_review,
    plan_loop_complete,
    plan_loop_escalate,
    resolve_plan_workspace,
    save_workflow,
    set_action_plan_reviewer_approved,
    update_plan_loop_state,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Synthesize plan loop iteration")
    parser.add_argument("codename", help="Session codename")
    parser.add_argument(
        "workspace",
        help="Workspace path relative to hub root (e.g. sessions/alpha/reviews/workspace/wf-...)",
    )
    args = parser.parse_args()

    root = hub_root()
    codename = validate_codename(args.codename)
    session_dir = root / "sessions" / codename
    try:
        workspace = resolve_plan_workspace(root, codename, args.workspace)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    findings_path = workspace / "findings" / "plan.json"

    if not findings_path.exists():
        print(f"Missing {findings_path}", file=sys.stderr)
        return 1

    findings_doc = json.loads(findings_path.read_text())
    manifest_path = workspace / "plan_scope_manifest.json"
    if not manifest_path.exists():
        print(f"Missing {manifest_path}", file=sys.stderr)
        return 1
    try:
        manifest = json.loads(manifest_path.read_text())
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON in {manifest_path}: {exc}", file=sys.stderr)
        return 1
    workflow_id = manifest.get("workflow_id", workspace.name)
    if not workflow_id:
        workflow_id = workspace.name

    review_id, verdict, report_path = persist_plan_review(
        session_dir,
        workspace,
        findings_doc,
        workflow_id=str(workflow_id),
    )

    workflow = load_workflow(session_dir)
    plan_loop = (workflow.get("loops") or {}).get("plan") or {}
    iteration = int(plan_loop.get("iteration", 0)) + 1
    maximum = int(plan_loop.get("max", 5))
    workflow = update_plan_loop_state(workflow, iteration=iteration, verdict=verdict)

    if plan_loop_complete(verdict):
        plan_rel = (workflow.get("artifacts") or {}).get("plan", "artifacts/action-plan.md")
        try:
            set_action_plan_reviewer_approved(session_dir, plan_rel)
        except FileNotFoundError as exc:
            print(str(exc), file=sys.stderr)
            save_workflow(session_dir, workflow)
            return 1
        workflow["phase"] = "plan_user_review"
    elif plan_loop_escalate(verdict, iteration, maximum):
        pass  # conductor escalates to user; phase unchanged

    save_workflow(session_dir, workflow)

    print(review_id)
    print(verdict)
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
