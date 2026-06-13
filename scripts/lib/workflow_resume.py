"""Workflow resume and reopen helpers (M7)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from workflow_io import read_summary_json
from workflow_ids import latest_review_id
from workflow_plan import (
    INBOX_GATE_POLL_SECONDS,
    load_workflow,
    save_workflow,
)

PhaseHintBuilder = Callable[[dict[str, Any]], str]


def _hint_intake(_workflow: dict[str, Any]) -> str:
    return "Continue analyst interview; draft artifacts/problem-brief.md"


def _hint_brief_review(_workflow: dict[str, Any]) -> str:
    return (
        "Present brief for gate 1: accept via chat (accept brief / accept), "
        "./scripts/workflow-accept-brief.sh, or program-route-feedback.py for program children; "
        f"optional classify-only poll every {INBOX_GATE_POLL_SECONDS // 60}m: "
        "workflow-pull-inbox-gate.py --apply"
    )


def _hint_plan_loop(workflow: dict[str, Any]) -> str:
    plan_loop = (workflow.get("loops") or {}).get("plan") or {}
    iteration = plan_loop.get("iteration", 0)
    maximum = plan_loop.get("max", 5)
    verdict = plan_loop.get("last_verdict") or "—"
    return (
        f"Resume autonomous plan loop (iteration {iteration}/{maximum}, "
        f"last {verdict}): plan-author → plan-reviewer → workflow-plan-synthesize.py"
    )


def _hint_plan_user_review(_workflow: dict[str, Any]) -> str:
    return (
        "Present plan for gate 2: accept via chat (accept plan), "
        "./scripts/workflow-accept-plan.sh, or program-route-feedback.py for program children; "
        f"optional classify-only poll every {INBOX_GATE_POLL_SECONDS // 60}m: "
        "workflow-pull-inbox-gate.py --apply"
    )


def _hint_implementation(_workflow: dict[str, Any]) -> str:
    return (
        "Continue implementation; when slice done run "
        "workflow-mark-implementation-ready.py <codename> <task-id> — auto code review, no commit gate"
    )


def _hint_code_review_loop(workflow: dict[str, Any]) -> str:
    code_loop = (workflow.get("loops") or {}).get("code_review") or {}
    iteration = code_loop.get("iteration", 0)
    maximum = code_loop.get("max", 5)
    verdict = code_loop.get("last_verdict") or "—"
    return (
        f"Resume autonomous code review loop (iteration {iteration}/{maximum}, "
        f"last {verdict}): specialists → fixer on INCOMPLETE → advance"
    )


def _hint_pr_creation(_workflow: dict[str, Any]) -> str:
    return (
        "Commit and open draft PR: run conductor pr_creation phase — "
        "git-commit skill, pr-create skill, then advance to ci_observe"
    )


def _hint_ci_observe(workflow: dict[str, Any]) -> str:
    ci_loop = (workflow.get("loops") or {}).get("ci_observe") or {}
    iteration = ci_loop.get("iteration", 0)
    maximum = ci_loop.get("max", 5)
    verdict = ci_loop.get("last_verdict") or "—"
    return (
        f"Resume CI observe loop (iteration {iteration}/{maximum}, "
        f"last {verdict}): poll checks, rebase on conflict, fix on failure, advance to delivery on green"
    )


def _hint_delivery(_workflow: dict[str, Any]) -> str:
    return "Write delivery report: python3 scripts/workflow-write-delivery-report.py <codename>"


def _hint_completed(_workflow: dict[str, Any]) -> str:
    return "Pipeline complete; optional end session"


WORKFLOW_PHASES: tuple[str, ...] = (
    "intake",
    "brief_review",
    "plan_loop",
    "plan_user_review",
    "implementation",
    "code_review_loop",
    "pr_creation",
    "ci_observe",
    "delivery",
    "completed",
)

PHASE_HINT_BUILDERS: dict[str, PhaseHintBuilder] = {
    "intake": _hint_intake,
    "brief_review": _hint_brief_review,
    "plan_loop": _hint_plan_loop,
    "plan_user_review": _hint_plan_user_review,
    "implementation": _hint_implementation,
    "code_review_loop": _hint_code_review_loop,
    "pr_creation": _hint_pr_creation,
    "ci_observe": _hint_ci_observe,
    "delivery": _hint_delivery,
    "completed": _hint_completed,
}


def workflow_next_action(workflow: dict[str, Any]) -> str:
    """Return conductor resume hint from workflow.json state."""
    phase = str(workflow.get("phase") or "unknown")
    builder = PHASE_HINT_BUILDERS.get(phase)
    if builder:
        return builder(workflow)

    gates = workflow.get("gates") or {}
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
    return latest_review_id(session_dir / "artifacts" / "plan-review", "pr")


def latest_code_review_id(session_dir: Path) -> str | None:
    return latest_review_id(session_dir / "reviews", "r")


def read_review_summary_json(session_dir: Path, review_id: str) -> dict[str, Any] | None:
    path = session_dir / "reviews" / f"{review_id}.json"
    return read_summary_json(path, missing="none")


def read_plan_review_summary(session_dir: Path, review_id: str) -> dict[str, Any] | None:
    path = session_dir / "artifacts" / "plan-review" / f"{review_id}.json"
    return read_summary_json(path, missing="none")
