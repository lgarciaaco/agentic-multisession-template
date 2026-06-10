"""Workflow resume and reopen helpers (M7)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from workflow_code_review import read_review_summary
from workflow_plan import latest_sequential_id, load_workflow, save_workflow


def workflow_next_action(workflow: dict[str, Any]) -> str:
    """Return conductor resume hint from workflow.json state."""
    phase = str(workflow.get("phase") or "unknown")
    gates = workflow.get("gates") or {}
    loops = workflow.get("loops") or {}
    plan_loop = loops.get("plan") or {}
    code_loop = loops.get("code_review") or {}

    if phase == "intake":
        return "Continue analyst interview; draft artifacts/problem-brief.md"
    if phase == "brief_review":
        return "Present brief; await user accept brief"
    if phase == "plan_loop":
        iteration = plan_loop.get("iteration", 0)
        maximum = plan_loop.get("max", 5)
        verdict = plan_loop.get("last_verdict") or "—"
        return (
            f"Resume autonomous plan loop (iteration {iteration}/{maximum}, "
            f"last {verdict}): plan-author → plan-reviewer → workflow-plan-synthesize.py"
        )
    if phase == "plan_user_review":
        return (
            "Present action plan, including refused dispositions; "
            "await user accept plan or plan-feedback.md"
        )
    if phase == "implementation":
        return (
            "Continue implementation; when slice done run "
            "workflow-mark-implementation-ready.py <codename> <task-id> — auto code review, no commit gate"
        )
    if phase == "code_review_loop":
        iteration = code_loop.get("iteration", 0)
        maximum = code_loop.get("max", 5)
        verdict = code_loop.get("last_verdict") or "—"
        return (
            f"AUTO — no user turn: resume code review loop (iteration {iteration}/{maximum}, "
            f"last {verdict}): load code-reviewer SKILL → specialists → fixer on INCOMPLETE → advance"
        )
    if phase == "delivery":
        return "Write delivery report: python3 scripts/workflow-write-delivery-report.py <codename>"
    if phase == "completed":
        return "Pipeline complete; optional end session"
    if not gates.get("brief_accepted"):
        return "Set gates.brief_accepted via accept brief before advancing"
    if not gates.get("plan_user_accepted"):
        return "Set gates.plan_user_accepted via accept plan before implementation"
    return f"Resume phase `{phase}` per workflow-orchestrator SKILL.md"


def reopen_brief(session_dir: Path) -> dict[str, Any]:
    """Unfreeze brief: clear gates, phase → intake."""
    workflow = load_workflow(session_dir)
    gates = workflow.setdefault("gates", {})
    gates["brief_accepted"] = False
    gates["plan_user_accepted"] = False
    workflow["phase"] = "intake"
    loops = workflow.setdefault("loops", {})
    plan_loop = loops.setdefault("plan", {"iteration": 0, "max": 5, "last_verdict": None})
    plan_loop["iteration"] = 0
    plan_loop["last_verdict"] = None
    code_loop = loops.setdefault(
        "code_review",
        {"iteration": 0, "max": 5, "last_verdict": None, "task_id": None},
    )
    code_loop["iteration"] = 0
    code_loop["last_verdict"] = None
    code_loop["task_id"] = None
    impl = loops.get("implementation")
    if isinstance(impl, dict):
        impl["active_task"] = None
        impl["ready_for_review"] = False
    save_workflow(session_dir, workflow)
    return workflow


def reopen_plan(session_dir: Path) -> dict[str, Any]:
    """Unfreeze plan: clear plan gate, phase → plan_loop."""
    workflow = load_workflow(session_dir)
    gates = workflow.setdefault("gates", {})
    if not gates.get("brief_accepted"):
        raise ValueError("brief not accepted — use reopen brief or complete intake first")
    gates["plan_user_accepted"] = False
    workflow["phase"] = "plan_loop"
    save_workflow(session_dir, workflow)
    return workflow


def latest_plan_review_id(session_dir: Path) -> str | None:
    return latest_sequential_id(session_dir / "artifacts" / "plan-review", "pr")


def latest_code_review_id(session_dir: Path) -> str | None:
    return latest_sequential_id(session_dir / "reviews", "r")


def read_review_summary_json(session_dir: Path, review_id: str) -> dict[str, Any] | None:
    try:
        return read_review_summary(session_dir, review_id)
    except (FileNotFoundError, ValueError):
        return None


def read_plan_review_summary(session_dir: Path, review_id: str) -> dict[str, Any] | None:
    path = session_dir / "artifacts" / "plan-review" / f"{review_id}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None
