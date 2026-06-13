"""Inbox feedback correlated with workflow user gates."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from gate_command_registry import (
    ACCEPT_BRIEF,
    ACCEPT_PLAN,
    REOPEN_BRIEF,
    REOPEN_PLAN,
    classify_gate_command,
    is_gate_command_action,
)
from gate_metadata_registry import gate_artifact_path, gate_feedback_kind, gate_feedback_kinds
from hub_paths import resolve_session_artifact
from program_state import GATE_PHASES, find_program_parent
from inbox_provenance import inbox_block_marker
from session_binding import read_inbox, sanitize_goal_text, validate_codename
from workflow_plan import (
    INBOX_GATE_POLL_SECONDS,
    accept_action_plan,
    load_workflow,
    save_workflow,
)
from workflow_resume import reopen_brief, reopen_plan

INBOX_POLL_SECONDS = INBOX_GATE_POLL_SECONDS

_INBOX_BLOCK_RE = re.compile(
    r"^\*\*From `(?P<from>[^`]+)`\*\* \((?P<date>[^)]+)\)\s*\n+(?P<body>.*?)(?=^\*\*From `|\Z)",
    re.MULTILINE | re.DOTALL,
)

def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def inbox_gate_state(workflow: dict[str, Any]) -> dict[str, Any]:
    gates = workflow.setdefault("gates", {})
    inbox = gates.setdefault("inbox", {})
    inbox.setdefault("processed_markers", [])
    inbox.setdefault("last_pull_at", None)
    return inbox


def block_marker(from_session: str, date: str, body: str) -> str:
    return inbox_block_marker(from_session, date, body)


def parse_inbox_blocks(content: str) -> list[dict[str, str]]:
    blocks: list[dict[str, str]] = []
    for match in _INBOX_BLOCK_RE.finditer(content):
        body = match.group("body").strip()
        if not body:
            continue
        from_session = match.group("from").strip()
        date = match.group("date").strip()
        blocks.append(
            {
                "from": from_session,
                "date": date,
                "body": body,
                "marker": block_marker(from_session, date, body),
            }
        )
    return blocks


def classify_gate_message(phase: str, body: str) -> str | None:
    if phase not in GATE_PHASES:
        return None
    text = body.strip()
    if not text:
        return None

    first_line = text.splitlines()[0].strip()
    action = classify_gate_command(phase, first_line)
    if action is not None:
        return action
    return gate_feedback_kind(phase)


def gate_command_sender_authorized(
    root: Path,
    target_codename: str,
    from_session: str,
    body: str,
    *,
    marker: str | None = None,
) -> bool:
    """Return True when from_session may apply inbox gate commands to target.

    Program parent gate routing uses tmux send-keys — inbox gate auto-apply is
    disabled for gate commands. Chat gate commands and workflow-accept-*.sh remain
    authorized user paths.
    """
    _ = (root, target_codename, from_session, body, marker)
    return False


def feedback_sender_authorized(
    root: Path,
    target_codename: str,
    from_session: str,
) -> bool:
    """Return True when from_session may auto-apply brief_correction or plan_feedback.

    Program parent→child corrections use tmux send-keys — registered program children
    never auto-apply parent inbox feedback. No other senders are authorized today.
    """
    try:
        target = validate_codename(target_codename)
        sender = validate_codename(from_session)
    except ValueError:
        return False
    if sender == target:
        return False
    if find_program_parent(root, target) is not None:
        return False
    return False


def unprocessed_inbox_blocks(
    root: Path,
    codename: str,
    workflow: dict[str, Any],
) -> list[dict[str, str]]:
    content = read_inbox(root, codename)
    if not content:
        return []
    inbox = inbox_gate_state(workflow)
    processed = set(inbox.get("processed_markers") or [])
    return [block for block in parse_inbox_blocks(content) if block["marker"] not in processed]


def set_problem_brief_accepted(session_dir: Path, brief_rel: str) -> None:
    brief_path = resolve_session_artifact(session_dir, brief_rel)
    if not brief_path.exists():
        raise ValueError(f"missing brief artifact: {brief_rel}")
    accepted = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    text = brief_path.read_text()
    text = re.sub(
        r"^\*\*Status:\*\*.*$",
        "**Status:** accepted",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    text = re.sub(
        r"^\*\*Accepted:\*\*.*$",
        f"**Accepted:** {accepted}",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    text = re.sub(
        r"(?ms)^## Open questions\s*\n(?:- .*\n)*",
        "## Open questions\n\n(none)\n",
        text,
        count=1,
    )
    brief_path.write_text(text)


def accept_brief(root: Path, codename: str, *, source: str = "user") -> dict[str, Any]:
    """User or inbox gate: accept brief → plan loop."""
    session_dir = root / "sessions" / codename
    workflow = load_workflow(session_dir)
    phase = str(workflow.get("phase") or "")
    if phase != "brief_review":
        raise ValueError(f"cannot accept brief in phase '{phase}'")

    gates = workflow.setdefault("gates", {})
    if gates.get("brief_accepted"):
        raise ValueError("brief already accepted")

    artifacts = workflow.get("artifacts") or {}
    brief_rel = artifacts.get("brief", gate_artifact_path("brief_review"))
    set_problem_brief_accepted(session_dir, brief_rel)

    gates["brief_accepted"] = True
    workflow["phase"] = "plan_loop"
    save_workflow(session_dir, workflow)
    return {"codename": codename, "phase": "plan_loop", "source": source}


def apply_brief_correction(
    root: Path,
    codename: str,
    message: str,
    *,
    from_session: str,
) -> dict[str, Any]:
    from_session = validate_codename(from_session)
    session_dir = root / "sessions" / codename
    workflow = load_workflow(session_dir)
    phase = str(workflow.get("phase") or "")
    if phase != "brief_review":
        raise ValueError(f"cannot apply brief correction in phase '{phase}'")

    artifacts = workflow.get("artifacts") or {}
    brief_rel = artifacts.get("brief", gate_artifact_path("brief_review"))
    brief_path = resolve_session_artifact(session_dir, brief_rel)
    brief_path.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    safe_body = sanitize_goal_text(message.strip())
    block = f"\n\n## Inbox correction from `{from_session}` ({stamp})\n\n{safe_body}\n"
    if brief_path.exists():
        brief_path.write_text(brief_path.read_text().rstrip() + block + "\n")
    else:
        brief_path.write_text(f"# Problem brief\n{block}\n")
    return {"codename": codename, "phase": "brief_review", "artifact": str(brief_rel)}


def apply_plan_feedback(
    root: Path,
    codename: str,
    message: str,
    *,
    from_session: str,
) -> dict[str, Any]:
    from_session = validate_codename(from_session)
    session_dir = root / "sessions" / codename
    workflow = load_workflow(session_dir)
    phase = str(workflow.get("phase") or "")
    if phase != "plan_user_review":
        raise ValueError(f"cannot apply plan feedback in phase '{phase}'")

    artifacts = workflow.get("artifacts") or {}
    feedback_rel = artifacts.get("plan_feedback", "artifacts/plan-feedback.md")
    feedback_path = resolve_session_artifact(session_dir, feedback_rel)
    feedback_path.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    safe_body = sanitize_goal_text(message.strip())
    block = f"\n\n## Inbox feedback from `{from_session}` ({stamp})\n\n{safe_body}\n"
    if feedback_path.exists():
        feedback_path.write_text(feedback_path.read_text().rstrip() + block + "\n")
    else:
        feedback_path.write_text(f"# Plan feedback\n{block}\n")

    workflow["phase"] = "plan_loop"
    save_workflow(session_dir, workflow)
    return {"codename": codename, "phase": "plan_loop", "artifact": str(feedback_rel)}


def mark_inbox_processed(workflow: dict[str, Any], markers: list[str]) -> None:
    inbox = inbox_gate_state(workflow)
    processed = list(inbox.get("processed_markers") or [])
    for marker in markers:
        if marker not in processed:
            processed.append(marker)
    inbox["processed_markers"] = processed
    inbox["last_pull_at"] = _utc_now_iso()


def pull_inbox_gate(
    root: Path,
    codename: str,
    *,
    apply: bool = False,
) -> dict[str, Any]:
    session_dir = root / "sessions" / codename
    workflow_path = session_dir / "workflow.json"
    if not workflow_path.exists():
        raise ValueError(f"missing {workflow_path} — start /workflow-orchestrator first")

    workflow = load_workflow(session_dir)
    phase = str(workflow.get("phase") or "")
    inbox = inbox_gate_state(workflow)
    blocks = unprocessed_inbox_blocks(root, codename, workflow)

    pending: list[dict[str, Any]] = []
    for block in blocks:
        action = classify_gate_message(phase, block["body"])
        if not action:
            continue
        pending.append(
            {
                "action": action,
                "from": block["from"],
                "date": block["date"],
                "marker": block["marker"],
                "body": block["body"],
            }
        )

    result: dict[str, Any] = {
        "codename": codename,
        "phase": phase,
        "gate_phase": phase in GATE_PHASES,
        "poll_seconds": INBOX_POLL_SECONDS,
        "last_pull_at": inbox.get("last_pull_at"),
        "pending": pending,
        "applied": [],
        "rejected": [],
    }

    if not apply or not pending:
        if phase in GATE_PHASES:
            inbox["last_pull_at"] = _utc_now_iso()
            save_workflow(session_dir, workflow)
        return result

    applied_markers: list[str] = []
    rejected: list[dict[str, Any]] = []
    for item in pending:
        action = item["action"]
        from_session = item["from"]
        body = item["body"]
        marker = item["marker"]

        if is_gate_command_action(action) and not gate_command_sender_authorized(
            root, codename, from_session, body, marker=marker
        ):
            applied_markers.append(marker)
            rejected.append(
                {
                    "action": action,
                    "from": from_session,
                    "marker": marker,
                    "reason": "unauthorized_gate_sender",
                }
            )
            continue

        if action in gate_feedback_kinds() and not feedback_sender_authorized(
            root, codename, from_session
        ):
            applied_markers.append(marker)
            rejected.append(
                {
                    "action": action,
                    "from": from_session,
                    "marker": marker,
                    "reason": "unauthorized_feedback_sender",
                }
            )
            continue

        if action == ACCEPT_BRIEF:
            accept_brief(root, codename, source=f"inbox:{from_session}")
            workflow = load_workflow(session_dir)
            phase = str(workflow.get("phase") or "")
            result["phase"] = phase
            applied_markers.append(marker)
            result["applied"].append({"action": action, "from": from_session, "marker": marker})
            break

        if action == ACCEPT_PLAN:
            accept_action_plan(root, codename)
            workflow = load_workflow(session_dir)
            phase = str(workflow.get("phase") or "")
            result["phase"] = phase
            applied_markers.append(marker)
            result["applied"].append({"action": action, "from": from_session, "marker": marker})
            break

        if action == REOPEN_BRIEF:
            workflow = reopen_brief(session_dir)
            phase = str(workflow.get("phase") or "")
            result["phase"] = phase
            applied_markers.append(marker)
            result["applied"].append({"action": action, "from": from_session, "marker": marker})
            break

        if action == REOPEN_PLAN:
            workflow = reopen_plan(session_dir)
            phase = str(workflow.get("phase") or "")
            result["phase"] = phase
            applied_markers.append(marker)
            result["applied"].append({"action": action, "from": from_session, "marker": marker})
            break

        if action == "plan_feedback":
            apply_plan_feedback(root, codename, body, from_session=from_session)
            workflow = load_workflow(session_dir)
            phase = str(workflow.get("phase") or "")
            result["phase"] = phase
            applied_markers.append(marker)
            result["applied"].append({"action": action, "from": from_session, "marker": marker})
            break

        if action == "brief_correction":
            apply_brief_correction(root, codename, body, from_session=from_session)
            workflow = load_workflow(session_dir)
            phase = str(workflow.get("phase") or "")
            result["phase"] = phase
            applied_markers.append(marker)
            result["applied"].append({"action": action, "from": from_session, "marker": marker})
            break

    workflow = load_workflow(session_dir)
    mark_inbox_processed(workflow, applied_markers)
    save_workflow(session_dir, workflow)
    result["last_pull_at"] = inbox_gate_state(workflow).get("last_pull_at")
    result["rejected"] = rejected
    return result


def pull_inbox_gate_json(root: Path, codename: str, *, apply: bool = False) -> str:
    return json.dumps(pull_inbox_gate(root, codename, apply=apply), indent=2) + "\n"
