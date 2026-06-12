"""Workflow resume and reopen helpers (M7)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from workflow_plan import load_workflow, save_workflow, INBOX_GATE_POLL_SECONDS


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
        return (
            "Present brief; await user accept brief or correlated inbox feedback "
            f"(poll inbox every {INBOX_GATE_POLL_SECONDS // 60}m at gate)"
        )
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
            "await user accept plan, plan-feedback.md, or correlated inbox feedback "
            f"(poll inbox every {INBOX_GATE_POLL_SECONDS // 60}m at gate)"
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
            f"Resume autonomous code review loop (iteration {iteration}/{maximum}, "
            f"last {verdict}): specialists → fixer on INCOMPLETE → advance"
        )
    if phase == "pr_creation":
        return (
            "Commit and open draft PR: run conductor pr_creation phase — "
            "git-commit skill, pr-create skill, then advance to ci_observe"
        )
    if phase == "ci_observe":
        ci_loop = loops.get("ci_observe") or {}
        iteration = ci_loop.get("iteration", 0)
        maximum = ci_loop.get("max", 5)
        verdict = ci_loop.get("last_verdict") or "—"
        return (
            f"Resume CI observe loop (iteration {iteration}/{maximum}, "
            f"last {verdict}): poll checks, rebase on conflict, fix on failure, advance to delivery on green"
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
    plan_review_dir = session_dir / "artifacts" / "plan-review"
    if not plan_review_dir.is_dir():
        return None
    highest = 0
    best = None
    for path in plan_review_dir.glob("pr-*.json"):
        match = re.fullmatch(r"pr-(\d+)", path.stem)
        if match and int(match.group(1)) > highest:
            highest = int(match.group(1))
            best = path.stem
    return best


def latest_code_review_id(session_dir: Path) -> str | None:
    reviews_dir = session_dir / "reviews"
    if not reviews_dir.is_dir():
        return None
    highest = 0
    best = None
    for path in reviews_dir.glob("r-*.json"):
        match = re.fullmatch(r"r-(\d+)", path.stem)
        if match and int(match.group(1)) > highest:
            highest = int(match.group(1))
            best = path.stem
    return best


def read_review_summary_json(session_dir: Path, review_id: str) -> dict[str, Any] | None:
    path = session_dir / "reviews" / f"{review_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def read_plan_review_summary(session_dir: Path, review_id: str) -> dict[str, Any] | None:
    path = session_dir / "artifacts" / "plan-review" / f"{review_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())
