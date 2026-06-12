"""Plan loop helpers for workflow-orchestrator (M4)."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hub_paths import resolve_review_workspace, resolve_session_artifact

SEVERITY_RANK = {"NIT": 0, "SUGGESTION": 1, "REQUIRED": 2, "BLOCKER": 3}
INBOX_GATE_POLL_SECONDS = 120


def make_workflow_id(when: datetime | None = None) -> str:
    """Return wf-YYYYMMDD-HHMMSS workspace id."""
    moment = when or datetime.now(timezone.utc)
    return moment.strftime("wf-%Y%m%d-%H%M%S")


def next_plan_review_id(plan_review_dir: Path) -> str:
    """Allocate next pr-NNN id from artifacts/plan-review/."""
    plan_review_dir.mkdir(parents=True, exist_ok=True)
    highest = 0
    for path in plan_review_dir.glob("pr-*.json"):
        match = re.fullmatch(r"pr-(\d+)", path.stem)
        if match:
            highest = max(highest, int(match.group(1)))
    return f"pr-{highest + 1:03d}"


def dedupe_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep highest severity per issue text."""
    by_issue: dict[str, dict[str, Any]] = {}
    for item in findings:
        issue = str(item.get("issue") or "").strip()
        if not issue:
            continue
        current = by_issue.get(issue)
        if not current:
            by_issue[issue] = item
            continue
        cur_rank = SEVERITY_RANK.get(str(current.get("severity")), 0)
        new_rank = SEVERITY_RANK.get(str(item.get("severity")), 0)
        if new_rank >= cur_rank:
            by_issue[issue] = item
    return list(by_issue.values())


def count_findings_by_severity(findings: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"required": 0, "suggestion": 0, "nit": 0, "blocker": 0}
    for item in findings:
        sev = str(item.get("severity") or "").upper()
        key = sev.lower() if sev in SEVERITY_RANK else None
        if key and key in counts:
            counts[key] += 1
    return counts


def synthesize_plan_verdict(findings_doc: dict[str, Any]) -> str:
    """Compute APPROVE | REVISE | REJECT from plan reviewer output."""
    agent_verdict = str(findings_doc.get("verdict") or "").upper()
    if agent_verdict == "REJECT":
        return "REJECT"

    criteria = findings_doc.get("criteria") or []
    raw_findings = findings_doc.get("findings") or []
    findings = dedupe_findings(raw_findings)

    def severity(item: dict[str, Any]) -> str:
        return str(item.get("severity") or "").upper()

    if any(severity(item) == "REQUIRED" for item in findings):
        return "REVISE"
    if any(not item.get("met", True) for item in criteria):
        return "REVISE"
    # Open SUGGESTION/NIT → author must disposition; reviewer must validate on a later pass.
    open_items = raw_findings + findings
    if any(severity(item) in ("SUGGESTION", "NIT") for item in open_items):
        return "REVISE"
    return "APPROVE"


def write_plan_scope_manifest(
    workspace: Path,
    *,
    codename: str,
    brief_path: str,
    plan_path: str,
    session_mode: str | None = None,
    workflow_id: str,
    prior_findings: str | None = None,
    user_feedback: str | None = None,
) -> Path:
    """Write plan_scope_manifest.json for plan loop Task agents."""
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "findings").mkdir(exist_ok=True)
    manifest = {
        "workflow_id": workflow_id,
        "phase": "plan_review",
        "codename": codename,
        "brief_path": brief_path,
        "plan_path": plan_path,
        "session_mode": session_mode or "product",
    }
    if prior_findings:
        manifest["prior_findings"] = prior_findings
    if user_feedback:
        manifest["user_feedback"] = user_feedback
    out = workspace / "plan_scope_manifest.json"
    out.write_text(json.dumps(manifest, indent=2) + "\n")
    return out


def render_plan_report(
    findings_doc: dict[str, Any],
    *,
    verdict: str,
    workflow_id: str,
    codename: str,
) -> str:
    """Markdown report for plan synthesizer."""
    criteria = findings_doc.get("criteria") or []
    findings = dedupe_findings(findings_doc.get("findings") or [])
    counts = count_findings_by_severity(findings)

    lines = [
        f"# Plan review — {codename}",
        "",
        f"**Workflow:** `{workflow_id}`",
        f"**Verdict:** {verdict}",
        "",
        "## Criteria",
        "",
        "| ID | Met | Evidence |",
        "|----|-----|----------|",
    ]
    for item in criteria:
        cid = item.get("id", "")
        met = "yes" if item.get("met") else "no"
        evidence = str(item.get("evidence") or "—")
        lines.append(f"| {cid} | {met} | {evidence} |")

    lines.extend(["", "## Findings", ""])
    if not findings:
        lines.append("None.")
    else:
        for item in findings:
            sev = item.get("severity", "")
            issue = item.get("issue", "")
            fix = item.get("fix", "")
            fix_line = f" — fix: {fix}" if fix else ""
            lines.append(f"- **{sev}:** {issue}{fix_line}")

    lines.extend(
        [
            "",
            "## Counts",
            "",
            f"required: {counts['required']}, suggestion: {counts['suggestion']}, nit: {counts['nit']}",
        ]
    )
    return "\n".join(lines) + "\n"


def persist_plan_review(
    session_dir: Path,
    workspace: Path,
    findings_doc: dict[str, Any],
    *,
    workflow_id: str,
    when: datetime | None = None,
) -> tuple[str, str, str]:
    """
    Synthesize verdict, write workspace report, persist pr-NNN artifacts.
    Returns (review_id, verdict, report_path).
    """
    verdict = synthesize_plan_verdict(findings_doc)
    findings = dedupe_findings(findings_doc.get("findings") or [])
    counts = count_findings_by_severity(findings)

    report = render_plan_report(
        findings_doc,
        verdict=verdict,
        workflow_id=workflow_id,
        codename=session_dir.name,
    )
    report_path = workspace / "report.md"
    report_path.write_text(report)

    plan_review_dir = session_dir / "artifacts" / "plan-review"
    review_id = next_plan_review_id(plan_review_dir)
    moment = when or datetime.now(timezone.utc)

    try:
        workspace_rel = workspace.relative_to(session_dir.parent.parent)
    except ValueError:
        workspace_rel = workspace
    summary = {
        "id": review_id,
        "at": moment.isoformat(),
        "workflow_id": workflow_id,
        "workspace": str(workspace_rel),
        "verdict": verdict,
        "findings_count": {
            "required": counts["required"],
            "suggestion": counts["suggestion"],
            "nit": counts["nit"],
        },
    }
    (plan_review_dir / f"{review_id}.json").write_text(json.dumps(summary, indent=2) + "\n")
    (plan_review_dir / f"{review_id}-report.md").write_text(report)

    return review_id, verdict, str(report_path)


def load_workflow(session_dir: Path) -> dict[str, Any]:
    path = session_dir / "workflow.json"
    if not path.exists():
        raise FileNotFoundError(f"missing workflow: {path}")
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path}") from exc


def save_workflow(session_dir: Path, workflow: dict[str, Any]) -> None:
    path = session_dir / "workflow.json"
    path.write_text(json.dumps(workflow, indent=2) + "\n")


def update_plan_loop_state(
    workflow: dict[str, Any],
    *,
    iteration: int,
    verdict: str,
) -> dict[str, Any]:
    loops = workflow.setdefault("loops", {})
    plan_loop = loops.setdefault("plan", {"iteration": 0, "max": 5, "last_verdict": None})
    plan_loop["iteration"] = iteration
    plan_loop["last_verdict"] = verdict
    workflow["loops"] = loops
    return workflow


def resolve_plan_workspace(root: Path, codename: str, workspace_arg: str) -> Path:
    """Resolve workspace path; must stay under sessions/<codename>/reviews/workspace/."""
    return resolve_review_workspace(root, codename, workspace_arg)


def plan_loop_complete(verdict: str) -> bool:
    return verdict == "APPROVE"


def plan_loop_escalate(verdict: str, iteration: int, maximum: int) -> bool:
    return verdict == "REJECT" or (verdict == "REVISE" and iteration >= maximum)


def set_action_plan_reviewer_approved(session_dir: Path, plan_rel: str) -> None:
    """Update only Status header in action-plan.md."""
    plan_path = resolve_session_artifact(session_dir, plan_rel)
    if not plan_path.exists():
        raise FileNotFoundError(f"action plan not found: {plan_rel}")
    text = plan_path.read_text()
    text = re.sub(
        r"^\*\*Status:\*\*.*$",
        "**Status:** reviewer_approved",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    plan_path.write_text(text)


def run_plan_loop(
    root: Path,
    codename: str,
    findings_sequence: list[dict[str, Any]],
    *,
    workflow_id: str = "wf-20260609-120000",
) -> dict[str, Any]:
    """
    Drive plan loop for tests or dry-run. Each findings_sequence entry is plan.json
    content for one iteration (after plan-author would have run).
    """
    session_dir = root / "sessions" / codename
    workflow = load_workflow(session_dir)
    workflow["phase"] = "plan_loop"
    artifacts = workflow.get("artifacts") or {}
    brief_rel = artifacts.get("brief", "artifacts/problem-brief.md")
    plan_rel = artifacts.get("plan", "artifacts/action-plan.md")
    brief_path = f"sessions/{codename}/{brief_rel}"
    plan_path = f"sessions/{codename}/{plan_rel}"
    session = json.loads((session_dir / "session.json").read_text())
    session_mode = session.get("mode") or "product"

    verdicts: list[str] = []
    review_id = ""
    max_iter = int((workflow.get("loops") or {}).get("plan", {}).get("max", 5))

    for index, findings_doc in enumerate(findings_sequence, start=1):
        workspace = session_dir / "reviews" / "workspace" / f"{workflow_id}-iter{index}"
        write_plan_scope_manifest(
            workspace,
            codename=codename,
            brief_path=brief_path,
            plan_path=plan_path,
            session_mode=session_mode,
            workflow_id=workflow_id,
            prior_findings="findings/plan.json" if index > 1 else None,
        )
        (workspace / "findings").mkdir(exist_ok=True)
        (workspace / "findings" / "plan.json").write_text(
            json.dumps(findings_doc, indent=2) + "\n"
        )

        review_id, verdict, _ = persist_plan_review(
            session_dir,
            workspace,
            findings_doc,
            workflow_id=workflow_id,
        )
        verdicts.append(verdict)
        workflow = update_plan_loop_state(workflow, iteration=index, verdict=verdict)
        save_workflow(session_dir, workflow)

        if plan_loop_complete(verdict):
            set_action_plan_reviewer_approved(session_dir, plan_rel)
            workflow["phase"] = "plan_user_review"
            save_workflow(session_dir, workflow)
            break
        if plan_loop_escalate(verdict, index, max_iter):
            break

    return {"verdicts": verdicts, "workflow": workflow, "last_review": review_id}


_SECTION_TASKS = re.compile(r"^##\s+Tasks\s*$", re.IGNORECASE)


def parse_action_plan_tasks(plan_text: str) -> list[dict[str, Any]]:
    """Parse ## Tasks markdown table from action-plan.md."""
    lines = plan_text.splitlines()
    start = None
    for index, line in enumerate(lines):
        if _SECTION_TASKS.match(line.strip()):
            start = index + 1
            break
    if start is None:
        raise ValueError("action-plan.md has no ## Tasks section")

    table_rows: list[str] = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        if line.strip().startswith("|"):
            table_rows.append(line.strip())

    if len(table_rows) < 2:
        raise ValueError("action-plan.md Tasks table is empty")

    tasks: list[dict[str, Any]] = []
    for row in table_rows[2:]:
        cells = [cell.strip() for cell in row.strip("|").split("|")]
        if len(cells) < 4:
            continue
        task_id, repo, summary = cells[0], cells[1], cells[2]
        depends = cells[-1].strip() if len(cells) > 4 else ""
        acceptance = cells[3] if len(cells) == 4 else "|".join(cells[3:-1]).strip()
        if not task_id or task_id.lower() == "id":
            continue
        if depends in ("—", "-", ""):
            depends = ""
        entry: dict[str, Any] = {
            "id": task_id,
            "title": summary,
            "repo": repo,
            "status": "pending",
            "acceptance": acceptance,
        }
        if depends:
            entry["depends"] = depends
        tasks.append(entry)

    if not tasks:
        raise ValueError("action-plan.md Tasks table has no data rows")
    return tasks


def _tasks_table_markdown(tasks: list[dict[str, Any]]) -> list[str]:
    rows = [
        "| ID | Status | Notes |",
        "|----|--------|-------|",
    ]
    for task in tasks:
        note_parts: list[str] = []
        if task.get("repo"):
            note_parts.append(f"repo: {task['repo']}")
        if task.get("acceptance"):
            note_parts.append(str(task["acceptance"]))
        if task.get("depends"):
            note_parts.append(f"depends: {task['depends']}")
        if task.get("title") and not note_parts:
            note_parts.append(str(task["title"]))
        note = " — ".join(note_parts)
        rows.append(f"| {task['id']} | {task.get('status', 'pending')} | {note} |")
    return rows


def set_tasks_table_section(session_dir: Path, tasks: list[dict[str, Any]]) -> None:
    """Replace ## Tasks table body in TASKS.md; preserve Goal and Notes."""
    path = session_dir / "TASKS.md"
    if not path.exists():
        raise FileNotFoundError(f"{path} not found")
    lines = path.read_text().splitlines()
    new_lines: list[str] = []
    index = 0
    found = False
    while index < len(lines):
        if _SECTION_TASKS.match(lines[index].strip()):
            found = True
            new_lines.append(lines[index])
            index += 1
            while index < len(lines) and not lines[index].startswith("## "):
                index += 1
            new_lines.append("")
            new_lines.extend(_tasks_table_markdown(tasks))
            continue
        new_lines.append(lines[index])
        index += 1
    if not found:
        raise ValueError("TASKS.md has no ## Tasks section")
    path.write_text("\n".join(new_lines).rstrip() + "\n")


def set_action_plan_user_approved(session_dir: Path, plan_rel: str) -> None:
    plan_path = resolve_session_artifact(session_dir, plan_rel)
    if not plan_path.exists():
        return
    text = plan_path.read_text()
    text = re.sub(
        r"^\*\*Status:\*\*.*$",
        "**Status:** user_approved",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    plan_path.write_text(text)


def sync_action_plan_tasks(root: Path, codename: str) -> list[dict[str, Any]]:
    """Parse action-plan.md and write tasks to session.json + TASKS.md."""
    from repos import load_repos

    session_dir = root / "sessions" / codename
    workflow = load_workflow(session_dir)
    artifacts = workflow.get("artifacts") or {}
    plan_rel = artifacts.get("plan", "artifacts/action-plan.md")
    plan_path = resolve_session_artifact(session_dir, plan_rel)
    if not plan_path.exists():
        raise FileNotFoundError(f"missing {plan_path}")

    parsed = parse_action_plan_tasks(plan_path.read_text())
    repos = load_repos(root)
    for task in parsed:
        alias = task.get("repo", "")
        if not alias:
            raise ValueError(f"task {task['id']} missing repo")
        if repos and alias not in repos:
            raise ValueError(f"task {task['id']} repo '{alias}' not in repos.yaml")

    session_path = session_dir / "session.json"
    session = json.loads(session_path.read_text())
    session["tasks"] = parsed
    session_path.write_text(json.dumps(session, indent=2) + "\n")
    set_tasks_table_section(session_dir, parsed)
    return parsed


def accept_action_plan(root: Path, codename: str) -> dict[str, Any]:
    """
    User gate: accept plan → sync tasks, set gates, phase implementation.
    Caller should run ensure-worktrees.sh and sync-session.sh after.
    """
    session_dir = root / "sessions" / codename
    workflow_path = session_dir / "workflow.json"
    if not workflow_path.exists():
        raise ValueError(f"missing {workflow_path} — start /workflow-orchestrator first")

    workflow = load_workflow(session_dir)
    gates = workflow.setdefault("gates", {})
    if not gates.get("brief_accepted"):
        raise ValueError("brief not accepted — accept brief first")
    if gates.get("plan_user_accepted"):
        raise ValueError("plan already accepted")

    phase = workflow.get("phase", "")
    if phase not in ("plan_user_review", "plan_loop"):
        raise ValueError(f"cannot accept plan in phase '{phase}'")

    tasks = sync_action_plan_tasks(root, codename)
    plan_rel = (workflow.get("artifacts") or {}).get("plan", "artifacts/action-plan.md")
    set_action_plan_user_approved(session_dir, plan_rel)

    gates["plan_user_accepted"] = True
    workflow["gates"] = gates
    workflow["phase"] = "implementation"
    save_workflow(session_dir, workflow)

    return {"codename": codename, "tasks": tasks, "phase": "implementation"}
