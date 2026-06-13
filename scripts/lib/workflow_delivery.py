"""Delivery report generator for workflow-orchestrator (M7)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hub_paths import resolve_session_artifact
from workflow_plan import artifact_rel, load_workflow, resolve_artifact, save_workflow
from workflow_resume import (
    latest_code_review_id,
    latest_plan_review_id,
    read_plan_review_summary,
    read_review_summary_json,
)


def render_delivery_report(
    session_dir: Path,
    *,
    codename: str,
    title: str | None = None,
) -> str:
    """Build delivery-report.md content from session artifacts."""
    session_path = session_dir / "session.json"
    session = json.loads(session_path.read_text()) if session_path.exists() else {}
    report_title = title or session.get("title") or codename
    workflow = load_workflow(session_dir)
    loops = workflow.get("loops") or {}

    tasks = session.get("tasks") or []
    done_tasks = [t for t in tasks if str(t.get("status") or "").lower() == "done"]
    pending_tasks = [t for t in tasks if str(t.get("status") or "").lower() != "done"]

    plan_id = latest_plan_review_id(session_dir)
    code_id = latest_code_review_id(session_dir)
    plan_summary = read_plan_review_summary(session_dir, plan_id) if plan_id else None
    code_summary = read_review_summary_json(session_dir, code_id) if code_id else None

    plan_verdict = (loops.get("plan") or {}).get("last_verdict")
    code_verdict = (loops.get("code_review") or {}).get("last_verdict")
    if code_summary and code_summary.get("verdict"):
        code_verdict = code_summary.get("verdict")

    delivered_lines: list[str] = []
    if done_tasks:
        for task in done_tasks:
            note = task.get("note") or task.get("title") or ""
            pr = task.get("pr")
            pr_bit = f" — PR: {pr}" if pr else ""
            delivered_lines.append(f"- **{task.get('id')}:** {note}{pr_bit}")
    else:
        delivered_lines.append("- No session.json tasks marked done.")

    verification_lines = [
        f"- Plan loop: {plan_verdict or '—'}"
        + (f" (`{plan_id}`)" if plan_id else ""),
        f"- Code review: {code_verdict or '—'}"
        + (f" (`{code_id}`)" if code_id else ""),
    ]
    if code_summary and code_summary.get("findings_count"):
        counts = code_summary["findings_count"]
        verification_lines.append(
            "- Findings: "
            f"required={counts.get('required', 0)}, "
            f"suggestion={counts.get('suggestion', 0)}, "
            f"nit={counts.get('nit', 0)}"
        )

    deferred_lines: list[str] = []
    if code_summary and code_summary.get("findings_count"):
        counts = code_summary["findings_count"]
        if counts.get("suggestion") or counts.get("nit"):
            deferred_lines.append(
                f"- Code review nits/suggestions: "
                f"{counts.get('suggestion', 0)} suggestion, {counts.get('nit', 0)} nit"
            )
    if pending_tasks:
        for task in pending_tasks:
            deferred_lines.append(f"- Task `{task.get('id')}` still {task.get('status', 'pending')}")
    if not deferred_lines:
        deferred_lines.append("- None.")

    brief_rel = artifact_rel(workflow, "brief")
    plan_rel = artifact_rel(workflow, "plan")
    artifact_lines = [
        f"- `{brief_rel}`",
        f"- `{plan_rel}`",
    ]
    if plan_id:
        artifact_lines.append(f"- plan-review `{plan_id}`")
    if code_id:
        artifact_lines.append(f"- code review `{code_id}`")

    resume_hint = session.get("next") or "—"

    lines = [
        f"# Delivery report — {report_title}",
        "",
        f"**Session:** `{codename}`",
        f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "## Delivered",
        "",
        *delivered_lines,
        "",
        "## Verification",
        "",
        *verification_lines,
        "",
        "## Deferred",
        "",
        *deferred_lines,
        "",
        "## Artifacts",
        "",
        *artifact_lines,
        "",
        "## Resume",
        "",
        str(resume_hint),
        "",
    ]
    return "\n".join(lines)


def write_delivery_report(
    session_dir: Path,
    *,
    codename: str,
    title: str | None = None,
) -> Path:
    """Write artifacts/delivery-report.md and set phase completed."""
    workflow = load_workflow(session_dir)
    delivery_path = resolve_artifact(session_dir, workflow, "delivery")
    delivery_path.parent.mkdir(parents=True, exist_ok=True)
    delivery_path.write_text(render_delivery_report(session_dir, codename=codename, title=title))
    workflow["phase"] = "completed"
    save_workflow(session_dir, workflow)
    return delivery_path
