"""Program orchestrator state for multi-session parent sessions."""

from __future__ import annotations

import functools
import json
from pathlib import Path
from typing import Any

from hub_paths import resolve_session_artifact
from session_binding import validate_codename

PROGRAM_VERSION = 1
PROGRAM_FILENAME = "program.json"

GATE_PHASES = frozenset({"brief_review", "plan_user_review"})


def default_program(parent_codename: str) -> dict[str, Any]:
    """Return a fresh program document for a parent session."""
    name = validate_codename(parent_codename)
    return {
        "version": PROGRAM_VERSION,
        "parent_codename": name,
        "ingest_path": "artifacts/program-ingest.md",
        "plan_path": "artifacts/program-plan.md",
        "status_path": "artifacts/program-status.md",
        "decomposition_approved": False,
        "proposed_children": [],
        "active_children": [],
        "gate_queue": [],
        "merge_hints": {"ordered_children": [], "notes": []},
    }


def _require_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def _require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a list")
    return value


def _validate_artifact_path(session_dir: Path, rel: str, label: str) -> str:
    if not isinstance(rel, str) or not rel.strip():
        raise ValueError(f"{label} must be a non-empty string")
    resolve_session_artifact(session_dir, rel)
    return rel.strip()


def _validate_proposed_child(entry: Any, index: int) -> dict[str, Any]:
    if not isinstance(entry, dict):
        raise ValueError(f"proposed_children[{index}] must be an object")
    child_id = entry.get("id")
    if not isinstance(child_id, str) or not child_id.strip():
        raise ValueError(f"proposed_children[{index}].id must be a non-empty string")
    suggested = entry.get("suggested_codename")
    if suggested is not None:
        validate_codename(str(suggested))
    repo = entry.get("repo")
    if not isinstance(repo, str) or not repo.strip():
        raise ValueError(f"proposed_children[{index}].repo must be a non-empty string")
    depends_on = entry.get("depends_on", [])
    dep_list = _require_list(depends_on, f"proposed_children[{index}].depends_on")
    for dep in dep_list:
        if not isinstance(dep, str) or not dep.strip():
            raise ValueError(
                f"proposed_children[{index}].depends_on entries must be non-empty strings"
            )
    title = entry.get("title", "")
    goal = entry.get("goal", "")
    if not isinstance(title, str):
        raise ValueError(f"proposed_children[{index}].title must be a string")
    if not isinstance(goal, str):
        raise ValueError(f"proposed_children[{index}].goal must be a string")
    return {
        "id": child_id.strip(),
        "suggested_codename": validate_codename(str(suggested)) if suggested else None,
        "title": title,
        "goal": goal,
        "repo": repo.strip(),
        "depends_on": [dep.strip() for dep in dep_list],
    }


def _validate_active_child(entry: Any, index: int) -> dict[str, Any]:
    if not isinstance(entry, dict):
        raise ValueError(f"active_children[{index}] must be an object")
    codename = validate_codename(str(entry.get("codename", "")))
    status = entry.get("status", "pending")
    if not isinstance(status, str) or not status.strip():
        raise ValueError(f"active_children[{index}].status must be a non-empty string")
    started = entry.get("started")
    if started is not None and not isinstance(started, str):
        raise ValueError(f"active_children[{index}].started must be a string when set")
    pane_id = entry.get("pane_id")
    if pane_id is not None:
        if not isinstance(pane_id, str) or not pane_id.strip():
            raise ValueError(f"active_children[{index}].pane_id must be a non-empty string when set")
    window_label = entry.get("window_label")
    if window_label is not None and not isinstance(window_label, str):
        raise ValueError(f"active_children[{index}].window_label must be a string when set")
    last_routed_at = entry.get("last_routed_at")
    if last_routed_at is not None:
        if not isinstance(last_routed_at, str) or not last_routed_at.strip():
            raise ValueError(
                f"active_children[{index}].last_routed_at must be a non-empty string when set"
            )
    last_routed_message = entry.get("last_routed_message")
    if last_routed_message is not None:
        if not isinstance(last_routed_message, str):
            raise ValueError(
                f"active_children[{index}].last_routed_message must be a string when set"
            )
    unknown = set(entry) - {
        "codename",
        "status",
        "started",
        "pane_id",
        "window_label",
        "last_routed_at",
        "last_routed_message",
    }
    if unknown:
        raise ValueError(
            f"active_children[{index}] has unknown keys: {', '.join(sorted(unknown))}"
        )
    out: dict[str, Any] = {
        "codename": codename,
        "status": status.strip(),
    }
    if started is not None:
        out["started"] = started.strip()
    if pane_id is not None and pane_id.strip():
        out["pane_id"] = pane_id.strip()
    if window_label is not None and window_label.strip():
        out["window_label"] = window_label.strip()
    if last_routed_at is not None and last_routed_at.strip():
        out["last_routed_at"] = last_routed_at.strip()
    if last_routed_message is not None:
        out["last_routed_message"] = last_routed_message
    return out


def _validate_gate_entry(
    entry: Any,
    index: int,
    *,
    active_codenames: set[str],
) -> dict[str, Any]:
    if not isinstance(entry, dict):
        raise ValueError(f"gate_queue[{index}] must be an object")
    child = validate_codename(str(entry.get("child_codename", "")))
    if child not in active_codenames:
        raise ValueError(f"gate_queue[{index}] references unknown active child: {child}")
    gate = entry.get("gate")
    if gate not in GATE_PHASES:
        raise ValueError(
            f"gate_queue[{index}].gate must be one of: {', '.join(sorted(GATE_PHASES))}"
        )
    queued_at = entry.get("queued_at")
    if queued_at is not None and not isinstance(queued_at, str):
        raise ValueError(f"gate_queue[{index}].queued_at must be a string when set")
    handled = entry.get("handled", False)
    if not isinstance(handled, bool):
        raise ValueError(f"gate_queue[{index}].handled must be a boolean")
    out: dict[str, Any] = {
        "child_codename": child,
        "gate": gate,
        "handled": handled,
    }
    if queued_at is not None:
        out["queued_at"] = queued_at.strip()
    return out


def validate_program(
    program: dict[str, Any],
    *,
    session_dir: Path,
    expected_codename: str | None = None,
) -> dict[str, Any]:
    """Validate and normalize a program document."""
    doc = _require_mapping(program, "program")
    version = doc.get("version")
    if version != PROGRAM_VERSION:
        raise ValueError(f"unsupported program version: {version!r}")

    parent = validate_codename(str(doc.get("parent_codename", "")))
    if expected_codename is not None and parent != validate_codename(expected_codename):
        raise ValueError(
            f"parent_codename {parent!r} does not match session {expected_codename!r}"
        )

    ingest_path = _validate_artifact_path(session_dir, doc.get("ingest_path", ""), "ingest_path")
    plan_path = _validate_artifact_path(session_dir, doc.get("plan_path", ""), "plan_path")
    status_path = _validate_artifact_path(session_dir, doc.get("status_path", ""), "status_path")

    decomposition_approved = doc.get("decomposition_approved", False)
    if not isinstance(decomposition_approved, bool):
        raise ValueError("decomposition_approved must be a boolean")

    proposed_raw = _require_list(doc.get("proposed_children", []), "proposed_children")
    proposed_children = [
        _validate_proposed_child(entry, idx) for idx, entry in enumerate(proposed_raw)
    ]

    active_raw = _require_list(doc.get("active_children", []), "active_children")
    active_children = [
        _validate_active_child(entry, idx) for idx, entry in enumerate(active_raw)
    ]
    active_codenames = {entry["codename"] for entry in active_children}

    gate_raw = _require_list(doc.get("gate_queue", []), "gate_queue")
    gate_queue = [
        _validate_gate_entry(entry, idx, active_codenames=active_codenames)
        for idx, entry in enumerate(gate_raw)
    ]

    merge_hints_raw = _require_mapping(doc.get("merge_hints", {}), "merge_hints")
    ordered_raw = _require_list(
        merge_hints_raw.get("ordered_children", []),
        "merge_hints.ordered_children",
    )
    ordered_children: list[str] = []
    for idx, name in enumerate(ordered_raw):
        codename = validate_codename(str(name))
        if codename not in active_codenames:
            raise ValueError(
                f"merge_hints.ordered_children[{idx}] references unknown active child: {codename}"
            )
        ordered_children.append(codename)
    notes_raw = _require_list(merge_hints_raw.get("notes", []), "merge_hints.notes")
    notes: list[str] = []
    for idx, note in enumerate(notes_raw):
        if not isinstance(note, str):
            raise ValueError(f"merge_hints.notes[{idx}] must be a string")
        notes.append(note)

    return {
        "version": PROGRAM_VERSION,
        "parent_codename": parent,
        "ingest_path": ingest_path,
        "plan_path": plan_path,
        "status_path": status_path,
        "decomposition_approved": decomposition_approved,
        "proposed_children": proposed_children,
        "active_children": active_children,
        "gate_queue": gate_queue,
        "merge_hints": {"ordered_children": ordered_children, "notes": notes},
    }


def program_path(session_dir: Path) -> Path:
    return session_dir / PROGRAM_FILENAME


def load_program(session_dir: Path, *, codename: str | None = None) -> dict[str, Any]:
    """Load and validate program.json from a parent session directory."""
    path = program_path(session_dir)
    if not path.exists():
        raise FileNotFoundError(f"missing program state: {path}")
    try:
        raw = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path}") from exc
    expected = codename or session_dir.name
    return validate_program(raw, session_dir=session_dir, expected_codename=expected)


def save_program(session_dir: Path, program: dict[str, Any], *, codename: str | None = None) -> None:
    """Validate and persist program.json under a parent session directory."""
    expected = codename or session_dir.name
    normalized = validate_program(program, session_dir=session_dir, expected_codename=expected)
    program_path(session_dir).write_text(json.dumps(normalized, indent=2) + "\n")


def find_program_parent(root: Path, child: str) -> str | None:
    """Return parent codename when child is registered in a program's active_children.

    Results are cached per process for repeated (root, child) lookups. Cache is not
    invalidated when program.json changes — safe for CLI one-shot use; long-lived
    callers should restart or accept stale reads until process exit.

    Raises:
        ValueError: when child is not a valid codename.
    """
    child_name = validate_codename(child)
    return _find_program_parent_cached(str(root.resolve()), child_name)


@functools.lru_cache(maxsize=256)
def _find_program_parent_cached(root_str: str, child: str) -> str | None:
    root = Path(root_str)
    sessions_dir = root / "sessions"
    if not sessions_dir.is_dir():
        return None
    for session_dir in sorted(sessions_dir.iterdir()):
        if not session_dir.is_dir() or session_dir.name.startswith("_"):
            continue
        prog_file = program_path(session_dir)
        if not prog_file.exists():
            continue
        try:
            program = load_program(session_dir, codename=session_dir.name)
        except (ValueError, FileNotFoundError, OSError):
            continue
        active = {entry["codename"] for entry in program["active_children"]}
        if child in active:
            return program["parent_codename"]
    return None
