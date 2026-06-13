"""Code review loop helpers for workflow-orchestrator (M6)."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hub_paths import resolve_review_workspace, resolve_session_artifact
from workflow_plan import (
    dedupe_findings,
    load_workflow,
    parse_action_plan_tasks,
    save_workflow,
)

CODE_REVIEW_COMPLETE = frozenset({"PASS", "PASS_WITH_NITS"})
CODE_REVIEW_ESCALATE_VERDICTS = frozenset({"FAIL"})


def synthesize_code_review_verdict(
    findings_docs: list[dict[str, Any]],
) -> str:
    """Compute PASS | INCOMPLETE | FAIL from merged specialist findings.

    Any BLOCKER severity maps to FAIL regardless of agent token (including leaks, security, infra-yaml).
    """
    raw_findings: list[dict[str, Any]] = []
    for doc in findings_docs:
        raw_findings.extend(doc.get("findings") or [])
        if str(doc.get("agent") or "") == "intent":
            continue
        for item in doc.get("criteria") or []:
            if not item.get("met", True):
                raw_findings.append(
                    {
                        "severity": "REQUIRED",
                        "issue": f"intent criterion not met: {item.get('id', '')}",
                    }
                )
    merged = dedupe_findings(raw_findings)

    def severity(item: dict[str, Any]) -> str:
        return str(item.get("severity") or "").upper()

    if any(severity(item) == "BLOCKER" for item in merged):
        return "FAIL"
    if any(severity(item) == "REQUIRED" for item in merged):
        return "INCOMPLETE"
    open_items = raw_findings + merged
    if any(severity(item) in ("SUGGESTION", "NIT") for item in open_items):
        return "INCOMPLETE"
    return "PASS"


def _load_session_tasks(session_dir: Path) -> list[dict[str, Any]]:
    session_path = session_dir / "session.json"
    if not session_path.exists():
        return []
    return json.loads(session_path.read_text()).get("tasks") or []


def active_code_review_task_id(session_dir: Path) -> str | None:
    """Task id under review for the current slice (multi-PR plans)."""
    workflow = load_workflow(session_dir)
    code_loop = (workflow.get("loops") or {}).get("code_review") or {}
    task_id = str(code_loop.get("task_id") or "").strip()
    if task_id:
        return task_id
    impl = (workflow.get("loops") or {}).get("implementation") or {}
    active = str(impl.get("active_task") or "").strip()
    return active or None


def implementation_ready_for_review(session_dir: Path) -> tuple[bool, str | None]:
    """
    True when a task slice is ready for autonomous code review.
    Does not require every plan task to be done (supports sequential PR tasks).
    """
    tasks = _load_session_tasks(session_dir)
    if not tasks:
        return False, None

    workflow = load_workflow(session_dir)
    impl = (workflow.get("loops") or {}).get("implementation") or {}
    if impl.get("ready_for_review"):
        active = str(impl.get("active_task") or "").strip()
        if active:
            return True, active

    for task in tasks:
        task_id = str(task.get("id") or "").strip()
        if not task_id:
            continue
        status = str(task.get("status") or "").lower()
        if status == "done" and not task.get("code_review_passed"):
            return True, task_id

    if implementation_tasks_complete(session_dir):
        last = str(tasks[-1].get("id") or "").strip()
        return True, last or None

    return False, None


def mark_implementation_ready(session_dir: Path, task_id: str) -> dict[str, Any]:
    """Conductor calls when coding slice is complete — auto-enters code review next."""
    task_id = str(task_id).strip()
    if not task_id:
        raise ValueError("task_id required")
    tasks = _load_session_tasks(session_dir)
    if not any(str(t.get("id")) == task_id for t in tasks):
        raise ValueError(f"unknown task id: {task_id}")

    workflow = load_workflow(session_dir)
    phase = str(workflow.get("phase") or "")
    if phase not in ("implementation", "code_review_loop"):
        raise ValueError(f"cannot mark implementation ready in phase '{phase}'")

    loops = workflow.setdefault("loops", {})
    impl = loops.setdefault("implementation", {})
    impl["active_task"] = task_id
    impl["ready_for_review"] = True
    workflow["loops"] = loops
    save_workflow(session_dir, workflow)
    return workflow


def code_review_loop_complete(verdict: str) -> bool:
    return str(verdict).upper() in CODE_REVIEW_COMPLETE


def code_review_loop_escalate(verdict: str, iteration: int, maximum: int) -> bool:
    normalized = str(verdict).upper()
    if normalized in CODE_REVIEW_ESCALATE_VERDICTS:
        return True
    return normalized == "INCOMPLETE" and iteration >= maximum


def update_code_review_loop_state(
    workflow: dict[str, Any],
    *,
    iteration: int,
    verdict: str,
) -> dict[str, Any]:
    loops = workflow.setdefault("loops", {})
    code_loop = loops.setdefault(
        "code_review",
        {"iteration": 0, "max": 5, "last_verdict": None},
    )
    code_loop["iteration"] = iteration
    code_loop["last_verdict"] = verdict
    workflow["loops"] = loops
    return workflow


def next_code_review_id(reviews_dir: Path) -> str:
    """Allocate next r-NNN id from sessions/<codename>/reviews/."""
    reviews_dir.mkdir(parents=True, exist_ok=True)
    highest = 0
    for path in reviews_dir.glob("r-*.json"):
        match = re.fullmatch(r"r-(\d+)", path.stem)
        if match:
            highest = max(highest, int(match.group(1)))
    return f"r-{highest + 1:03d}"


def read_review_summary(session_dir: Path, review_id: str) -> dict[str, Any]:
    path = session_dir / "reviews" / f"{review_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Review summary not found: {path}")
    return json.loads(path.read_text())


def latest_review_summary(session_dir: Path) -> tuple[str, dict[str, Any]] | None:
    reviews_dir = session_dir / "reviews"
    if not reviews_dir.is_dir():
        return None
    best_id = ""
    best_num = -1
    for path in reviews_dir.glob("r-*.json"):
        match = re.fullmatch(r"r-(\d+)", path.stem)
        if match and int(match.group(1)) > best_num:
            best_num = int(match.group(1))
            best_id = path.stem
    if not best_id:
        return None
    return best_id, read_review_summary(session_dir, best_id)


def workflow_acceptance_criteria(session_dir: Path) -> list[dict[str, Any]]:
    """Build acceptance criteria from action-plan.md and session.json tasks."""
    workflow_path = session_dir / "workflow.json"
    if not workflow_path.exists():
        return []

    workflow = json.loads(workflow_path.read_text())
    artifacts = workflow.get("artifacts") or {}
    plan_rel = artifacts.get("plan", "artifacts/action-plan.md")
    try:
        plan_path = resolve_session_artifact(session_dir, plan_rel)
    except ValueError:
        plan_path = session_dir / "artifacts" / "action-plan.md"

    by_id: dict[str, dict[str, Any]] = {}
    if plan_path.exists():
        for task in parse_action_plan_tasks(plan_path.read_text()):
            task_id = str(task.get("id") or "").strip()
            if not task_id:
                continue
            by_id[task_id] = {
                "id": task_id,
                "source": "action-plan",
                "acceptance": str(task.get("acceptance") or "").strip(),
                "title": str(task.get("title") or "").strip(),
                "repo": str(task.get("repo") or "").strip(),
            }

    session_path = session_dir / "session.json"
    if session_path.exists():
        session = json.loads(session_path.read_text())
        for task in session.get("tasks") or []:
            task_id = str(task.get("id") or "").strip()
            acceptance = str(task.get("acceptance") or "").strip()
            if not task_id or not acceptance:
                continue
            entry = by_id.setdefault(
                task_id,
                {
                    "id": task_id,
                    "source": "session.json",
                    "acceptance": acceptance,
                    "title": str(task.get("title") or "").strip(),
                    "repo": str(task.get("repo") or "").strip(),
                },
            )
            if entry.get("source") != "action-plan":
                entry["acceptance"] = acceptance
                entry["source"] = "session.json"

    return list(by_id.values())


def enrich_scope_manifest(
    manifest_path: Path,
    session_dir: Path,
    *,
    codename: str,
) -> Path:
    """Add workflow acceptance block to scope_manifest.json for intent reviewer."""
    manifest = json.loads(manifest_path.read_text())
    criteria = workflow_acceptance_criteria(session_dir)
    if not criteria:
        return manifest_path

    workflow = load_workflow(session_dir)
    artifacts = workflow.get("artifacts") or {}
    plan_rel = artifacts.get("plan", "artifacts/action-plan.md")
    task_id = active_code_review_task_id(session_dir)
    if task_id:
        criteria = [item for item in criteria if item.get("id") == task_id] or criteria
    manifest["workflow"] = {
        "codename": codename,
        "action_plan_path": f"sessions/{codename}/{plan_rel}",
        "acceptance_criteria": criteria,
        "active_task": task_id,
        "include_working_tree": True,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest_path


def resolve_code_review_workspace(root: Path, codename: str, workspace_arg: str) -> Path:
    """Resolve workspace path; must stay under sessions/<codename>/reviews/workspace/."""
    return resolve_review_workspace(root, codename, workspace_arg)


def implementation_tasks_complete(session_dir: Path) -> bool:
    session_path = session_dir / "session.json"
    if not session_path.exists():
        return False
    session = json.loads(session_path.read_text())
    tasks = session.get("tasks") or []
    if not tasks:
        return False
    return all(str(task.get("status") or "").lower() == "done" for task in tasks)


def begin_code_review_loop(session_dir: Path, *, task_id: str | None = None) -> dict[str, Any]:
    """Transition implementation → code_review_loop when a task slice is ready."""
    ready, inferred = implementation_ready_for_review(session_dir)
    active = task_id or inferred
    if not ready or not active:
        if implementation_tasks_complete(session_dir):
            tasks = _load_session_tasks(session_dir)
            active = active or (str(tasks[-1].get("id") or "").strip() if tasks else None)
            ready = bool(active)
        if not ready or not active:
            raise ValueError(
                "implementation slice not ready for code review — "
                "run workflow-mark-implementation-ready.py <codename> <task-id> after coding"
            )

    workflow = load_workflow(session_dir)
    loops = workflow.setdefault("loops", {})
    code_loop = loops.setdefault(
        "code_review",
        {"iteration": 0, "max": 5, "last_verdict": None},
    )
    code_loop["task_id"] = active
    impl = loops.setdefault("implementation", {})
    impl["ready_for_review"] = False
    workflow["loops"] = loops
    workflow["phase"] = "code_review_loop"
    save_workflow(session_dir, workflow)
    return workflow


def update_progress_last_review(
    session_dir: Path,
    *,
    review_id: str,
    summary: dict[str, Any],
    when: datetime | None = None,
) -> None:
    progress_path = session_dir / "progress.json"
    progress: dict[str, Any] = {}
    if progress_path.exists():
        progress = json.loads(progress_path.read_text())
    moment = when or datetime.now(timezone.utc)
    progress["last_review"] = {
        "id": review_id,
        "verdict": summary.get("verdict"),
        "at": summary.get("at") or moment.isoformat(),
        "workspace": summary.get("workspace"),
        "scope": summary.get("scope"),
    }
    progress["updated"] = moment.date().isoformat()
    progress_path.write_text(json.dumps(progress, indent=2) + "\n")


def advance_code_review_loop(
    session_dir: Path,
    verdict: str,
    *,
    review_id: str | None = None,
) -> dict[str, Any]:
    """
    Update workflow loops.code_review after code-reviewer synthesizer persists r-NNN.
    Returns updated workflow dict.
    """
    workflow = load_workflow(session_dir)
    code_loop = (workflow.get("loops") or {}).get("code_review") or {}
    iteration = int(code_loop.get("iteration", 0)) + 1
    maximum = int(code_loop.get("max", 5))
    normalized = str(verdict).upper()
    workflow = update_code_review_loop_state(workflow, iteration=iteration, verdict=normalized)

    if code_review_loop_complete(normalized):
        workflow["phase"] = "pr_creation"
        task_id = active_code_review_task_id(session_dir)
        if task_id:
            session_path = session_dir / "session.json"
            if session_path.exists():
                session = json.loads(session_path.read_text())
                for task in session.get("tasks") or []:
                    if str(task.get("id")) == task_id:
                        task["code_review_passed"] = True
                session_path.write_text(json.dumps(session, indent=2) + "\n")
    elif code_review_loop_escalate(normalized, iteration, maximum):
        workflow["phase"] = "code_review_loop"
    else:
        workflow["phase"] = "code_review_loop"

    save_workflow(session_dir, workflow)

    if review_id:
        try:
            summary = read_review_summary(session_dir, review_id)
            update_progress_last_review(session_dir, review_id=review_id, summary=summary)
        except FileNotFoundError:
            pass
    elif latest_review_summary(session_dir):
        rid, summary = latest_review_summary(session_dir)  # type: ignore[misc]
        update_progress_last_review(session_dir, review_id=rid, summary=summary)

    return workflow


def persist_review_summary_for_test(
    session_dir: Path,
    *,
    verdict: str,
    workspace_rel: str,
    review_id: str | None = None,
    when: datetime | None = None,
) -> str:
    """Write reviews/r-NNN.json for tests (simulates code-reviewer synthesizer)."""
    reviews_dir = session_dir / "reviews"
    rid = review_id or next_code_review_id(reviews_dir)
    moment = when or datetime.now(timezone.utc)
    summary = {
        "id": rid,
        "at": moment.isoformat(),
        "review_id": workspace_rel.rsplit("/", 1)[-1],
        "workspace": workspace_rel,
        "scope": "changeset",
        "target": str(session_dir),
        "verdict": str(verdict).upper(),
        "agents": ["intent"],
        "findings_count": {"blocker": 0, "required": 0, "suggestion": 0, "nit": 0},
    }
    (reviews_dir / f"{rid}.json").write_text(json.dumps(summary, indent=2) + "\n")
    update_progress_last_review(session_dir, review_id=rid, summary=summary)
    return rid


def run_code_review_loop(
    root: Path,
    codename: str,
    verdict_sequence: list[str],
    *,
    workspace_id: str = "review-20260609-120000",
) -> dict[str, Any]:
    """
    Drive code review loop for tests. Each verdict simulates one code-reviewer run.
    """
    session_dir = root / "sessions" / codename
    begin_code_review_loop(session_dir)
    review_ids: list[str] = []
    workspace_rel = f"sessions/{codename}/reviews/workspace/{workspace_id}"

    for index, verdict in enumerate(verdict_sequence, start=1):
        rid = persist_review_summary_for_test(
            session_dir,
            verdict=verdict,
            workspace_rel=f"{workspace_rel}-iter{index}",
        )
        review_ids.append(rid)
        workflow = advance_code_review_loop(session_dir, verdict, review_id=rid)
        if code_review_loop_complete(str(verdict).upper()):
            break
        maximum = int((workflow.get("loops") or {}).get("code_review", {}).get("max", 5))
        if code_review_loop_escalate(str(verdict).upper(), index, maximum):
            break

    progress_path = session_dir / "progress.json"
    progress = json.loads(progress_path.read_text()) if progress_path.exists() else {}
    return {
        "verdicts": [str(v).upper() for v in verdict_sequence[: len(review_ids)]],
        "review_ids": review_ids,
        "workflow": workflow,
        "progress": progress,
    }
