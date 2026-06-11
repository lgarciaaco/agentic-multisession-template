"""PR creation phase helpers for workflow-orchestrator."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from workflow_code_review import active_code_review_task_id
from workflow_plan import load_workflow, save_workflow


PR_CREATION_SUCCESS = frozenset({"SUCCESS"})
PR_CREATION_RETRY = frozenset({"RETRY"})
PR_CREATION_FAIL = frozenset({"FAIL"})


def begin_pr_creation(session_dir: Path) -> dict[str, Any]:
    """Transition code_review PASS → pr_creation phase."""
    workflow = load_workflow(session_dir)
    phase = str(workflow.get("phase") or "")
    if phase != "pr_creation":
        raise ValueError(f"cannot begin pr_creation from phase '{phase}'")
    loops = workflow.setdefault("loops", {})
    pr_loop = loops.setdefault("pr_creation", {"iteration": 0, "max": 5, "last_verdict": None})
    pr_loop["iteration"] = 0
    pr_loop["last_verdict"] = None
    save_workflow(session_dir, workflow)
    return workflow


def advance_pr_creation(
    session_dir: Path,
    verdict: str,
    *,
    pr_url: str | None = None,
) -> dict[str, Any]:
    """
    Advance pr_creation loop after commit + PR attempt.
    SUCCESS → ci_observe; RETRY → stay; FAIL → escalate.
    """
    workflow = load_workflow(session_dir)
    loops = workflow.setdefault("loops", {})
    pr_loop = loops.setdefault("pr_creation", {"iteration": 0, "max": 5, "last_verdict": None})

    normalized = str(verdict).upper()
    _VALID_VERDICTS = PR_CREATION_SUCCESS | PR_CREATION_RETRY | PR_CREATION_FAIL
    if normalized not in _VALID_VERDICTS:
        raise ValueError(f"unknown pr_creation verdict: {verdict!r}")

    iteration = int(pr_loop.get("iteration", 0)) + 1
    maximum = int(pr_loop.get("max", 5))
    pr_loop["iteration"] = iteration
    pr_loop["last_verdict"] = normalized

    if normalized in PR_CREATION_SUCCESS:
        if not pr_url:
            raise ValueError("pr_url required when verdict is SUCCESS")
        _record_pr_url(session_dir, workflow, pr_url)
        ci_loop = loops.setdefault("ci_observe", {"iteration": 0, "max": 5, "last_verdict": None})
        ci_loop["iteration"] = 0
        ci_loop["last_verdict"] = None
        workflow["phase"] = "ci_observe"
    elif normalized in PR_CREATION_FAIL or iteration >= maximum:
        workflow["phase"] = "pr_creation"
    else:
        workflow["phase"] = "pr_creation"

    save_workflow(session_dir, workflow)
    return workflow


def _record_pr_url(session_dir: Path, workflow: dict[str, Any], pr_url: str) -> None:
    """Store PR URL on the active task in session.json."""
    session_path = session_dir / "session.json"
    if not session_path.exists():
        return
    task_id = active_code_review_task_id(session_dir)
    if not task_id:
        return
    session = json.loads(session_path.read_text())
    for task in session.get("tasks") or []:
        if str(task.get("id")) == task_id:
            task["pr"] = pr_url
            break
    session_path.write_text(json.dumps(session, indent=2) + "\n")


def pr_creation_escalate(verdict: str, iteration: int, maximum: int) -> bool:
    normalized = str(verdict).upper()
    if normalized in PR_CREATION_FAIL:
        return True
    return normalized in PR_CREATION_RETRY and iteration >= maximum
