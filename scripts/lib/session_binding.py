#!/usr/bin/env python3
"""Workspace session bindings: Cursor chat, tmux pane, and session lifecycle."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

CLOSED_STATUSES = frozenset({"completed", "closed", "cancelled"})
RESERVED_SESSION_DIRS = frozenset({"bindings", "context", "_inbox"})
CODENAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
RESOLVE_SOURCE_LABELS = {
    "binding": "this chat",
    "tmux-pane": "tmux tab",
    "tmux-session": "tmux session (sibling tab)",
    "tmux": "tmux window name",
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def validate_codename(codename: str) -> str:
    """Return a safe session codename or raise ValueError."""
    name = codename.strip()
    if not name:
        raise ValueError("codename must not be empty")
    if name.startswith("_") or name in RESERVED_SESSION_DIRS:
        raise ValueError(f"invalid session codename: {name}")
    if not CODENAME_RE.fullmatch(name):
        raise ValueError(
            f"invalid session codename: {name!r} "
            "(use lowercase letters, digits, hyphens; no slashes or ..)"
        )
    return name


NATO_CODENAMES: tuple[str, ...] = (
    "alpha",
    "bravo",
    "charlie",
    "delta",
    "echo",
    "foxtrot",
    "golf",
    "hotel",
    "india",
    "juliet",
    "kilo",
    "lima",
    "mike",
    "november",
    "oscar",
    "papa",
    "quebec",
    "romeo",
    "sierra",
    "tango",
    "uniform",
    "victor",
    "whiskey",
    "xray",
    "yankee",
    "zulu",
)
DEFAULT_CODENAME_POOL: tuple[str, ...] = NATO_CODENAMES[:8]


class CodenameAllocationError(Exception):
    """Failed to pick or create a session codename."""


def _require_yaml():
    try:
        import yaml
    except ImportError as exc:
        raise SystemExit("PyYAML required: pip install pyyaml") from exc
    return yaml


def _codenames_path(root: Path) -> Path:
    return root / "sessions" / "_codenames.yaml"


def _codenames_example_path(root: Path) -> Path:
    return root / "sessions" / "_codenames.example.yaml"


def _default_codenames_data() -> dict:
    return {
        "active_pool": "default",
        "pools": {"default": list(DEFAULT_CODENAME_POOL)},
        "used": [],
    }


def load_codenames(root: Path | None = None) -> dict:
    root = root or hub_root()
    yaml = _require_yaml()
    codenames_path = _codenames_path(root)
    example_path = _codenames_example_path(root)
    if not codenames_path.exists():
        if example_path.exists():
            codenames_path.write_text(example_path.read_text())
        else:
            codenames_path.parent.mkdir(parents=True, exist_ok=True)
            codenames_path.write_text(
                yaml.dump(_default_codenames_data(), default_flow_style=False, sort_keys=False)
            )
    data = yaml.safe_load(codenames_path.read_text()) or {}
    if not isinstance(data.get("pools"), dict):
        data["pools"] = {"default": list(DEFAULT_CODENAME_POOL)}
    used = data.get("used")
    if not isinstance(used, list):
        data["used"] = []
    return data


def save_codenames(root: Path, data: dict) -> None:
    yaml = _require_yaml()
    _codenames_path(root).write_text(
        yaml.dump(data, default_flow_style=False, sort_keys=False)
    )


def active_pool_name(data: dict) -> str:
    return (data.get("active_pool") or "default").strip() or "default"


def active_pool_list(data: dict) -> list[str]:
    pool_name = active_pool_name(data)
    pools = data.get("pools") or {}

    def _pool_list(name: str) -> list[str] | None:
        raw = pools.get(name)
        if isinstance(raw, list):
            return list(raw)
        return None

    pool = _pool_list(pool_name) or _pool_list("default")
    if pool is None:
        return list(DEFAULT_CODENAME_POOL)
    return pool


def used_codenames(data: dict) -> set[str]:
    used = data.get("used")
    if not isinstance(used, list):
        return set()
    return set(used)


def codename_available(root: Path, name: str, used: set[str]) -> bool:
    if name in used:
        return False
    return not (root / "sessions" / name).exists()


def first_available_in_pool(root: Path, pool: list[str], used: set[str]) -> str | None:
    for candidate in pool:
        try:
            name = validate_codename(candidate)
        except ValueError:
            continue
        if codename_available(root, name, used):
            return name
    return None


def _nato_start_index(pool: list[str]) -> int:
    """Index in NATO_CODENAMES to start overflow after the last pool member."""
    if not pool:
        return len(DEFAULT_CODENAME_POOL)
    nato_index = {name: idx for idx, name in enumerate(NATO_CODENAMES)}
    max_idx = -1
    for name in pool:
        idx = nato_index.get(name)
        if idx is not None:
            max_idx = max(max_idx, idx)
    if max_idx >= 0:
        return max_idx + 1
    return len(DEFAULT_CODENAME_POOL)


def expand_active_pool(root: Path, data: dict, *, min_add: int = 8) -> dict:
    pool_name = active_pool_name(data)
    pools = data.setdefault("pools", {})
    pool = list(active_pool_list(data))
    existing = set(pool)
    start = _nato_start_index(pool)
    added = 0
    idx = start
    while added < min_add and idx < len(NATO_CODENAMES):
        candidate = NATO_CODENAMES[idx]
        if candidate not in existing:
            pool.append(candidate)
            existing.add(candidate)
            added += 1
        idx += 1
    pools[pool_name] = pool
    save_codenames(root, data)
    return data


def allocate_codename(root: Path | None = None, explicit: str | None = None) -> str:
    root = root or hub_root()
    data = load_codenames(root)
    used = used_codenames(data)

    if explicit and explicit.strip():
        try:
            codename = validate_codename(explicit.strip())
        except ValueError as exc:
            raise CodenameAllocationError(str(exc)) from exc
        if codename in used:
            raise CodenameAllocationError(f"codename '{codename}' already used.")
        if (root / "sessions" / codename).exists():
            raise CodenameAllocationError(f"sessions/{codename}/ already exists.")
        return codename

    pool = active_pool_list(data)
    codename = first_available_in_pool(root, pool, used)
    if not codename:
        expand_active_pool(root, data, min_add=8)
        data = load_codenames(root)
        used = used_codenames(data)
        pool = active_pool_list(data)
        codename = first_available_in_pool(root, pool, used)
    if not codename:
        raise CodenameAllocationError("no codenames left in pool.")
    return codename


def mark_codename_used(root: Path, data: dict, codename: str) -> None:
    used = used_codenames(data)
    if codename not in used:
        used.add(codename)
        data["used"] = sorted(used)
        save_codenames(root, data)


def create_session_tree(root: Path, codename: str, title: str | None = None) -> None:
    name = validate_codename(codename)
    session_dir = root / "sessions" / name
    if session_dir.exists():
        raise CodenameAllocationError(f"sessions/{name}/ already exists.")

    template = root / "sessions" / "_template"
    for item in ("session.json", "BOUNDARIES.md", "TASKS.md", "progress.json"):
        src = template / item
        if not src.exists():
            raise CodenameAllocationError(f"missing template {src}")

    session_dir.mkdir(parents=True)
    (session_dir / "worktrees").mkdir(parents=True)
    today = date.today().isoformat()
    session_title = sanitize_context_text((title or name).strip() or name, max_len=200) or name

    for item in ("session.json", "BOUNDARIES.md", "TASKS.md", "progress.json"):
        text = (template / item).read_text()
        text = text.replace("CODENAME", name).replace("YYYY-MM-DD", today)
        (session_dir / item).write_text(text)

    session_path = session_dir / "session.json"
    session = json.loads(session_path.read_text())
    session["title"] = session_title
    session_path.write_text(json.dumps(session, indent=2) + "\n")

    index_path = root / "sessions" / "index.json"
    if not index_path.exists():
        example_index = root / "sessions" / "index.example.json"
        if example_index.exists():
            index_path.write_text(example_index.read_text())
        else:
            index_path.write_text('{"sessions": {}}\n')

    index = json.loads(index_path.read_text())
    index.setdefault("sessions", {})[name] = {
        "title": session_title,
        "status": "draft",
        "created": today,
    }
    index_path.write_text(json.dumps(index, indent=2) + "\n")

    data = load_codenames(root)
    mark_codename_used(root, data, name)


def set_session_title(root: Path, codename: str, title: str) -> None:
    name = validate_codename(codename)
    session_title = sanitize_context_text(title, max_len=200)
    if not session_title:
        raise ValueError("session title must not be empty")
    session = _load_session_json(root, name)
    if not session:
        raise FileNotFoundError(f"sessions/{name}/session.json not found")
    session["title"] = session_title
    _write_session_json(root, name, session)
    sync_index_from_session(root, name, session)


def _goal_text_from_tasks(session_dir: Path) -> str:
    """Non-empty body under ## Goal in TASKS.md (excludes the header)."""
    tasks_path = session_dir / "TASKS.md"
    if not tasks_path.exists():
        return ""
    lines = tasks_path.read_text().splitlines()
    goal_lines: list[str] = []
    in_goal = False
    for line in lines:
        if _is_goal_heading(line):
            in_goal = True
            continue
        if in_goal:
            if line.startswith("## "):
                break
            if line.strip():
                goal_lines.append(line)
    return sanitize_goal_text("\n".join(goal_lines).strip(), max_len=2000)


def set_tasks_goal(session_dir: Path, goal: str) -> None:
    """Replace the ## Goal section body in TASKS.md; preserve other sections."""
    path = session_dir / "TASKS.md"
    if not path.exists():
        raise FileNotFoundError(f"{path} not found")
    goal = goal.strip()
    if not goal:
        raise ValueError("goal must not be empty")
    goal = sanitize_goal_text(goal)
    if not goal:
        raise ValueError("goal must not be empty after sanitization")
    lines = path.read_text().splitlines()
    new_lines: list[str] = []
    i = 0
    found_goal = False
    while i < len(lines):
        if _is_goal_heading(lines[i]):
            found_goal = True
            new_lines.append(lines[i])
            i += 1
            while i < len(lines) and not lines[i].startswith("## "):
                i += 1
            new_lines.append("")
            new_lines.extend(goal.splitlines())
            continue
        new_lines.append(lines[i])
        i += 1
    if not found_goal:
        raise ValueError("TASKS.md has no ## Goal section")
    path.write_text("\n".join(new_lines).rstrip() + "\n")


def _task_has_scope(task: dict) -> bool:
    repo = (task.get("repo") or "").strip()
    if repo:
        return True
    task_id = (task.get("id") or "").strip()
    if task_id:
        return True
    status = (task.get("status") or "").strip().lower()
    return bool(status and status not in ("pending", "draft"))


def _tasks_have_scope(tasks: list) -> bool:
    return any(_task_has_scope(t) for t in tasks if isinstance(t, dict))


def session_scope_is_thin(root: Path, codename: str) -> bool:
    """True when session lacks meaningful title, goal, next, and tasks."""
    name = validate_codename(codename)
    session = _load_session_json(root, name) or {}
    title = (session.get("title") or "").strip()
    if title and title != name:
        return False
    if (session.get("next") or "").strip():
        return False
    session_dir = root / "sessions" / name
    if _goal_text_from_tasks(session_dir):
        return False
    if _tasks_have_scope(session.get("tasks") or []):
        return False
    return True


def format_session_scope_nudge(codename: str) -> str:
    return (
        f"Session scope not recorded yet for `{codename}`. Before product edits, run "
        f'`./scripts/set-session-scope.sh {codename} --title "…" --goal "…"`.'
    )


def self_hosted_worktree_missing(root: Path, codename: str) -> bool:
    """True when hub registers itself but the bound session has no ready worktree."""
    from repos import self_hosted_aliases

    if not self_hosted_aliases(root):
        return False
    return primary_worktree(root, codename) is None


def format_session_worktree_nudge(root: Path, codename: str) -> str:
    from repos import self_hosted_aliases

    aliases = self_hosted_aliases(root)
    alias = aliases[0] if aliases else "template"
    return (
        f"Self-hosted hub: add `tasks[].repo` `{alias}` and run "
        f"`./scripts/ensure-worktrees.sh {codename}` — product edits belong in the worktree, "
        f"not hub root."
    )


def set_session_scope(
    root: Path,
    codename: str,
    *,
    title: str | None = None,
    next_step: str | None = None,
    goal: str | None = None,
    conversation_id: str | None = None,
) -> None:
    """Update session title, next hint, and/or TASKS.md goal; refresh index and chat context."""
    name = validate_codename(codename)
    session_dir = root / "sessions" / name
    if not session_dir.is_dir():
        raise FileNotFoundError(f"sessions/{name}/ does not exist")

    if title is not None:
        set_session_title(root, name, title)

    session = _load_session_json(root, name) or {}
    if next_step is not None:
        cleaned = sanitize_context_text(next_step, max_len=500) if str(next_step).strip() else ""
        if cleaned:
            session["next"] = cleaned
        else:
            session.pop("next", None)
        _write_session_json(root, name, session)

    if goal is not None:
        set_tasks_goal(session_dir, goal)

    session = _load_session_json(root, name) or {}
    sync_index_from_session(root, name, session)
    refresh_binding_contexts(root, name, conversation_id=conversation_id)


def prompt_new_session_title(root: Path, codename: str) -> None:
    """Ask on /dev/tty for a display title; Enter keeps the codename default."""
    name = validate_codename(codename)
    default = name
    session = _load_session_json(root, name) or {}
    current = (session.get("title") or default).strip() or default
    try:
        entered = _read_tty_line(f"Session title [{current}]> ")
    except SystemExit:
        return
    if entered.strip() and entered.strip() != current:
        set_session_title(root, name, entered.strip())


def create_new_session(
    root: Path | None = None,
    explicit: str | None = None,
    title: str | None = None,
) -> str:
    root = root or hub_root()
    codename = allocate_codename(root, explicit)
    create_session_tree(root, codename, title)
    return codename


def sanitize_context_text(value: str, *, max_len: int = 500) -> str:
    """Single-line safe text for injected session context (no newlines or markdown breaks)."""
    if value is None:
        return ""
    text = str(value).replace("\r", " ").replace("\n", " ").strip()
    text = " ".join(text.split())
    if len(text) > max_len:
        return text[: max_len - 1] + "…"
    return text


def sanitize_goal_text(value: str, *, max_len: int = 2000) -> str:
    """Multi-line goal safe for TASKS.md and injected session context."""
    if value is None:
        return ""
    lines: list[str] = []
    for raw in str(value).replace("\r", "").split("\n"):
        line = " ".join(raw.strip().split())
        if not line:
            if lines and lines[-1]:
                lines.append("")
            continue
        if re.match(r"^#+\s", line):
            continue
        if re.match(r"^-\s+\*\*", line):
            continue
        if len(line) > 500:
            line = line[:499] + "…"
        lines.append(line)
    text = "\n".join(lines).strip()
    if len(text) > max_len:
        return text[: max_len - 1] + "…"
    return text


def _is_goal_heading(line: str) -> bool:
    return line.strip() == "## Goal"


def hub_root() -> Path:
    from hub_paths import hub_root as _hub_root

    return _hub_root()


def tmux_pane_option() -> str:
    return os.environ.get("WORKSPACE_TMUX_PANE_OPTION", "workspace-codename").strip() or "workspace-codename"


def hub_slug() -> str:
    env = os.environ.get("WORKSPACE_HUB_SLUG", "").strip()
    if env:
        return env
    meta = hub_root() / ".hub-slug"
    if meta.exists():
        slug = meta.read_text().strip()
        if slug:
            return slug
    return hub_root().name


def default_tmux_window_prefix(slug: str) -> str:
    """Derive window prefix from hub slug (e.g. my-app → my-)."""
    name = slug.strip()
    if not name:
        return ""
    if name.endswith("-agent"):
        name = name[: -len("-agent")]
    stem = name.split("-", 1)[0] if "-" in name else name
    return f"{stem}-"


def tmux_window_prefix() -> str:
    """Hub-scoped window prefix; empty env disables rename. Ignores stale foreign values."""
    if os.environ.get("WORKSPACE_TMUX_WINDOW_PREFIX", None) == "":
        return ""
    return default_tmux_window_prefix(hub_slug())


def agent_launcher_name() -> str:
    env = os.environ.get("WORKSPACE_AGENT_LAUNCHER", "").strip()
    if env:
        return env
    meta = hub_root() / ".hub-launcher"
    if meta.exists():
        name = meta.read_text().strip()
        if name:
            return name
    return "workspace-agent"


def conversation_id() -> str | None:
    cid = os.environ.get("WORKSPACE_CONVERSATION_ID", "").strip()
    return cid or None


def _run_tmux(*args: str) -> subprocess.CompletedProcess[str] | None:
    if not os.environ.get("TMUX"):
        return None
    try:
        return subprocess.run(
            ["tmux", *args],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def get_tmux_window_name() -> str | None:
    result = _run_tmux("display-message", "-p", "#W")
    if not result:
        return None
    name = result.stdout.strip()
    return name or None


def get_tmux_pane_codename() -> str | None:
    result = _run_tmux("display-message", "-p", f"#{{@{tmux_pane_option()}}}")
    if not result:
        return None
    name = result.stdout.strip()
    return name or None


def set_tmux_pane_codename(codename: str) -> bool:
    try:
        name = validate_codename(codename)
    except ValueError:
        return False
    return _run_tmux("set-option", "-p", f"@{tmux_pane_option()}", name) is not None


def clear_tmux_pane_codename() -> bool:
    return _run_tmux("delete-option", "-p", f"@{tmux_pane_option()}") is not None


def tmux_window_label(codename: str) -> str:
    base = codename.strip()
    if not base:
        return ""
    prefix = tmux_window_prefix()
    if prefix and base.startswith(prefix):
        return base
    return f"{prefix}{base}" if prefix else base


def rename_tmux_for_codename(codename: str) -> bool:
    """Rename tmux window to session label and set terminal title via OSC."""
    name = tmux_window_label(codename)
    if not name:
        return False

    renamed = _run_tmux("rename-window", name) is not None
    try:
        sys.stderr.write(f"\033]0;{name}\007\033]2;{name}\007")
        sys.stderr.flush()
    except OSError:
        pass
    return renamed


def _load_json_file(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def _index_sessions(root: Path) -> dict:
    index_path = root / "sessions" / "index.json"
    sessions = _load_json_file(index_path).get("sessions")
    return sessions if isinstance(sessions, dict) else {}


def _load_session_json(root: Path, codename: str) -> dict | None:
    path = root / "sessions" / codename / "session.json"
    if not path.exists():
        return None
    data = _load_json_file(path)
    return data if data else None


def _write_session_json(root: Path, codename: str, session: dict) -> None:
    path = root / "sessions" / codename / "session.json"
    path.write_text(json.dumps(session, indent=2) + "\n")


def _tasks_goal_line(session_dir: Path) -> str:
    tasks_path = session_dir / "TASKS.md"
    if not tasks_path.exists():
        return ""
    body = _goal_text_from_tasks(session_dir)
    if not body:
        return ""
    return "## Goal\n\n" + body


def sync_index_from_session(root: Path, codename: str, session: dict | None = None) -> None:
    """Copy canonical fields from session.json into sessions/index.json."""
    session = session or _load_session_json(root, codename) or {}
    index_path = root / "sessions" / "index.json"
    index = _load_json_file(index_path)
    if not isinstance(index.get("sessions"), dict):
        index["sessions"] = {}
    entry = index["sessions"].get(codename, {})
    entry.update(
        {
            "title": session.get("title") or entry.get("title", ""),
            "status": session.get("status") or entry.get("status", "draft"),
            "created": session.get("created") or entry.get("created", date.today().isoformat()),
        }
    )
    next_step = (session.get("next") or "").strip()
    if next_step:
        entry["next"] = next_step
    else:
        entry.pop("next", None)
    for key in ("ended", "paused_at"):
        entry.pop(key, None)
    index["sessions"][codename] = entry
    index_path.write_text(json.dumps(index, indent=2) + "\n")


def resume_session_on_bind(root: Path, codename: str) -> None:
    """Mark session active and sync index/progress when a tab or chat binds to it."""
    session = _load_session_json(root, codename)
    if not session:
        return
    if session.get("status") in CLOSED_STATUSES or session.get("ended"):
        return

    today = date.today().isoformat()
    now = _utc_now_iso()
    changed = False
    if session.get("status") != "active":
        session["status"] = "active"
        changed = True
    if not (session.get("title") or "").strip():
        session["title"] = codename
        changed = True
    for key in ("ended", "ended_at", "paused_at"):
        if key in session:
            session.pop(key, None)
            changed = True
    if changed:
        _write_session_json(root, codename, session)

    progress_path = root / "sessions" / codename / "progress.json"
    if progress_path.exists():
        progress = _load_json_file(progress_path)
        progress["status"] = "active"
        progress["updated"] = today
        progress["last_bound_at"] = now
        if progress.get("session") in (None, ""):
            progress["session"] = codename
        progress_path.write_text(json.dumps(progress, indent=2) + "\n")

    sync_index_from_session(root, codename, session)


def inbox_path(root: Path, target_codename: str) -> Path:
    """Cross-session messages for `target_codename` live in sessions/_inbox/<target>.md."""
    return root / "sessions" / "_inbox" / f"{target_codename}.md"


def read_inbox(root: Path, codename: str) -> str | None:
    path = inbox_path(root, codename)
    if not path.exists():
        return None
    text = path.read_text().strip()
    return text if text else None


def write_inbox(root: Path, from_codename: str, to_codename: str, message: str) -> Path:
    """Append a message from one session into another session's inbox file."""
    message = sanitize_goal_text(message.strip())
    if not message:
        raise ValueError("inbox message must not be empty")
    for raw in (from_codename, to_codename):
        name = validate_codename(raw)
        if not (root / "sessions" / name).is_dir():
            raise ValueError(f"invalid session codename: {name}")

    path = inbox_path(root, to_codename)
    path.parent.mkdir(parents=True, exist_ok=True)
    stamp = _utc_now_iso()[:10]
    block = f"\n\n---\n\n**From `{from_codename}`** ({stamp})\n\n{message}\n"

    if path.exists():
        path.write_text(path.read_text().rstrip() + block + "\n")
    else:
        header = (
            f"# Inbox for `{to_codename}`\n\n"
            "Messages from other sessions. Written via `./scripts/session-inbox.sh write`.\n"
        )
        path.write_text(header + block + "\n")
    return path


def session_mode(session: dict) -> str:
    """hub = orchestration label (CONTRIBUTING checklist); product work always uses worktrees."""
    mode = (session.get("mode") or "default").strip().lower()
    return mode if mode in ("hub", "default") else "default"


def worktree_alias(task: dict) -> str:
    return (task.get("repo") or task.get("id") or "project").strip() or "project"


def task_worktree_rel(codename: str, task: dict) -> str:
    alias = worktree_alias(task)
    return task.get("worktree") or f"sessions/{codename}/worktrees/{alias}"


def worktree_dest(root: Path, codename: str, task: dict) -> Path:
    return root / task_worktree_rel(codename, task)


def primary_worktree(root: Path, codename: str, session: dict | None = None) -> Path | None:
    session = session or _load_session_json(root, codename) or {}
    tasks = session.get("tasks") or []
    if not tasks:
        return None
    path = worktree_dest(root, codename, tasks[0])
    return path if path.is_dir() else None


def format_worktree_section(root: Path, codename: str, session: dict) -> str:
    tasks = session.get("tasks") or []
    if not tasks:
        return ""
    lines = ["\n## Worktrees\n"]
    for task in tasks:
        rel = task_worktree_rel(codename, task)
        branch = task.get("feature_branch") or task.get("base_branch") or "main"
        exists = (root / rel).is_dir()
        state = "ready" if exists else "run `./scripts/ensure-worktrees.sh " + codename + "`"
        repo = task.get("repo") or "—"
        meta_parts: list[str] = []
        if task.get("pr"):
            meta_parts.append(f"pr: {sanitize_context_text(task['pr'], max_len=200)}")
        if task.get("ci"):
            meta_parts.append(f"ci: {sanitize_context_text(task['ci'], max_len=200)}")
        if task.get("note"):
            meta_parts.append(f"note: {sanitize_context_text(task['note'], max_len=300)}")
        meta = f" — {' | '.join(meta_parts)}" if meta_parts else ""
        lines.append(
            f"- **`{task.get('id', 'main')}`** (`{repo}`) — `{rel}` (branch `{branch}`) — {state}{meta}"
        )
    return "\n".join(lines) + "\n"


def format_guidelines_section(root: Path, codename: str, session: dict) -> str:
    """Agent guideline pointers for session context (template + optional project/worktree docs)."""
    from repos import _path_under_root, load_guidelines, project_guideline_rel

    lines = ["\n## Guidelines\n", "- Template: `.cursor/rules/agent-guidelines.mdc`"]
    guidelines = load_guidelines(root)
    project_rel = project_guideline_rel(guidelines)
    project_path = _path_under_root(root, project_rel)
    if project_path and project_path.is_file():
        lines.append(f"- Project: `{project_rel}`")
    worktree_rel = guidelines.get("worktree")
    if isinstance(worktree_rel, str) and worktree_rel.strip():
        wt = primary_worktree(root, codename, session)
        if wt:
            contrib = (wt / worktree_rel).resolve()
            try:
                contrib.relative_to(wt.resolve())
                if contrib.is_file():
                    lines.append(f"- Worktree: `{contrib.relative_to(root.resolve())}`")
            except ValueError:
                pass
    return "\n".join(lines) + "\n"


_GUARD_ALLOW = {"permission": "allow"}


def _guard_deny(user_message: str, agent_message: str) -> dict:
    return {
        "permission": "deny",
        "user_message": user_message,
        "agent_message": agent_message,
    }


def _path_is_within(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except (ValueError, OSError):
        return False


def _session_codename_from_path(root: Path, resolved: Path) -> str | None:
    sessions_root = root / "sessions"
    if not _path_is_within(resolved, sessions_root) and resolved != sessions_root:
        return None
    rel = resolved.relative_to(sessions_root)
    if not rel.parts:
        return None
    first = rel.parts[0]
    if first in RESERVED_SESSION_DIRS or first.startswith("_"):
        return None
    session_dir = sessions_root / first
    if not session_dir.is_dir():
        return None
    try:
        validate_codename(first)
    except ValueError:
        return None
    return first


def _guard_protected_session_paths(root: Path, resolved: Path) -> dict | None:
    repos_dir = root / "repos"
    if _path_is_within(resolved, repos_dir) or resolved == repos_dir:
        return _guard_deny(
            "repos/ is read-only (reference clones).",
            "Edit only under sessions/<codename>/worktrees/. Run ./scripts/clone-repos.sh to refresh refs.",
        )

    for sub in ("bindings", "context"):
        protected = root / "sessions" / sub
        if _path_is_within(resolved, protected) or resolved == protected:
            return _guard_deny(
                "sessions/bindings and sessions/context are hook-protected.",
                "Do not edit binding or context files.",
            )

    index_json = root / "sessions" / "index.json"
    if resolved == index_json:
        return _guard_deny(
            "sessions/index.json is hook-protected.",
            "Use sync-session.sh to update index.",
        )
    return None


def guard_unbound_path_decision(root: Path, file_path: str) -> dict:
    """Cursor hook when no session is bound: fail-closed on sensitive hub paths."""
    if not file_path:
        return _GUARD_ALLOW

    root = root.resolve()
    try:
        resolved = Path(file_path).resolve()
    except OSError:
        return _guard_deny("Invalid path.", "Could not resolve file path.")

    if not _path_is_within(resolved, root):
        return _guard_deny(
            "Path is outside the hub workspace.",
            "Edit only under this hub root.",
        )

    protected = _guard_protected_session_paths(root, resolved)
    if protected:
        return protected

    other = _session_codename_from_path(root, resolved)
    if other:
        return _guard_deny(
            f"No session bound; cannot edit sessions/{other}/.",
            "Bind a session first (./scripts/bind-session.sh <codename>).",
        )

    return _GUARD_ALLOW


def _load_workflow_state(root: Path, codename: str) -> tuple[dict | None, bool]:
    path = root / "sessions" / codename / "workflow.json"
    if not path.exists():
        return None, False
    try:
        workflow = json.loads(path.read_text())
    except json.JSONDecodeError:
        return None, False
    accepted = bool((workflow.get("gates") or {}).get("plan_user_accepted"))
    return workflow, accepted


def workflow_gate_denies_worktree(root: Path, codename: str) -> dict | None:
    """Block worktree edits when workflow.json exists and plan is not accepted."""
    workflow, accepted = _load_workflow_state(root, codename)
    if workflow is None or accepted:
        return None
    return _guard_deny(
        "Workflow gate: plan not accepted.",
        f"Run ./scripts/workflow-accept-plan.sh {codename} after user accepts the plan.",
    )


def guard_path_decision(root: Path, codename: str, file_path: str) -> dict:
    """Cursor hook: allow/deny edits — repos/ read-only, worktrees writable."""
    if not file_path:
        return _GUARD_ALLOW
    if not codename:
        return _GUARD_ALLOW

    try:
        name = validate_codename(codename)
    except ValueError:
        return _guard_deny("Invalid session binding.", "Bind a valid session codename.")

    root = root.resolve()
    try:
        resolved = Path(file_path).resolve()
    except OSError:
        return _guard_deny("Invalid path.", "Could not resolve file path.")

    if not _path_is_within(resolved, root):
        return _guard_deny(
            "Path is outside the hub workspace.",
            "Edit only under this hub root or bind a session for worktree paths.",
        )

    protected = _guard_protected_session_paths(root, resolved)
    if protected:
        return protected

    inbox_dir = root / "sessions" / "_inbox"
    if _path_is_within(resolved, inbox_dir) or resolved == inbox_dir:
        return _GUARD_ALLOW

    session_dir = root / "sessions" / name
    session = _load_session_json(root, name) or {}
    worktrees_dir = session_dir / "worktrees"
    if _path_is_within(resolved, worktrees_dir):
        gate = workflow_gate_denies_worktree(root, name)
        if gate:
            return gate
        return _GUARD_ALLOW

    if _path_is_within(resolved, session_dir) or resolved == session_dir:
        return _GUARD_ALLOW

    other = _session_codename_from_path(root, resolved)
    if other and other != name:
        return _guard_deny(
            f"This chat is bound to session {name}, not {other}.",
            f"Do not edit sessions/{other}/. This chat is bound to {name}.",
        )

    return _guard_deny(
        f"Bound to session {name}; hub-root paths are blocked.",
        f"Edit under sessions/{name}/worktrees/ and session metadata. "
        f"Registry pins (repos.yaml, .hub-version, .hub-upstream): edit only when unbound. "
        f"Hub layer refresh: ./scripts/hub-upgrade.sh only.",
    )


def format_inbox_section(root: Path, codename: str) -> str:
    content = read_inbox(root, codename)
    if not content:
        return ""
    return f"\n## Inbox (from other sessions)\n\n{content}\n"


def format_workflow_section(root: Path, codename: str) -> str:
    """Inject workflow.json summary when a session uses the workflow orchestrator."""
    workflow_path = root / "sessions" / codename / "workflow.json"
    if not workflow_path.exists():
        return ""

    try:
        workflow = json.loads(workflow_path.read_text())
    except json.JSONDecodeError:
        return "\n## Workflow\n\n- **workflow.json:** invalid JSON — fix before `/workflow`\n"

    phase = sanitize_context_text(str(workflow.get("phase") or "unknown"), max_len=50) or "unknown"
    gates = workflow.get("gates") or {}
    loops = workflow.get("loops") or {}
    artifacts = workflow.get("artifacts") or {}

    lines = ["\n## Workflow\n", f"- **Phase:** `{phase}`"]
    for key in ("brief_accepted", "plan_user_accepted"):
        if key in gates:
            lines.append(f"- **Gate {key}:** {gates[key]}")

    plan_loop = loops.get("plan") or {}
    if plan_loop:
        iteration = plan_loop.get("iteration", 0)
        maximum = plan_loop.get("max", 5)
        verdict = plan_loop.get("last_verdict")
        verdict_text = sanitize_context_text(str(verdict), max_len=30) if verdict else "—"
        lines.append(f"- **Plan loop:** {iteration}/{maximum}; last `{verdict_text}`")

    code_loop = loops.get("code_review") or {}
    if code_loop:
        iteration = code_loop.get("iteration", 0)
        maximum = code_loop.get("max", 5)
        verdict = code_loop.get("last_verdict")
        verdict_text = sanitize_context_text(str(verdict), max_len=30) if verdict else "—"
        lines.append(f"- **Code review loop:** {iteration}/{maximum}; last `{verdict_text}`")

    session_dir = root / "sessions" / codename
    artifact_lines: list[str] = []
    for rel in artifacts.values():
        if not rel or not isinstance(rel, str):
            continue
        rel_clean = rel.strip().lstrip("/")
        if not rel_clean or ".." in Path(rel_clean).parts:
            continue
        exists = (session_dir / rel_clean).exists()
        state = "present" if exists else "missing"
        artifact_lines.append(f"`sessions/{codename}/{rel_clean}` ({state})")
    if artifact_lines:
        lines.append("- **Artifacts:**")
        for entry in artifact_lines:
            lines.append(f"  - {entry}")

    lines.append("- **Commands:** `/workflow`, `/workflow status`")
    try:
        from workflow_resume import workflow_next_action

        resume = workflow_next_action(workflow)
        resume_text = sanitize_context_text(resume, max_len=300)
        if resume_text:
            lines.append(f"- **Resume:** {resume_text}")
    except (ImportError, KeyError, TypeError, ValueError) as exc:
        hint = sanitize_context_text(str(exc), max_len=120)
        lines.append(f"- **Resume:** unavailable ({hint})")
    return "\n".join(lines) + "\n"


def build_context_markdown(root: Path, codename: str, chat_id: str) -> str:
    """Agent-facing context snippet from canonical session metadata."""
    session_dir = root / "sessions" / codename
    session = _load_session_json(root, codename) or {}
    goal = _tasks_goal_line(session_dir)
    tasks = session.get("tasks") or []
    running = [t.get("id") for t in tasks if t.get("status") in ("in_progress", "running", "draft")]
    title = sanitize_context_text(session.get("title") or "(no title)", max_len=200) or "(no title)"

    progress_note = ""
    progress_path = session_dir / "progress.json"
    if progress_path.exists():
        progress = json.loads(progress_path.read_text())
        if progress.get("handoff_note"):
            handoff = sanitize_context_text(progress["handoff_note"], max_len=500)
            if handoff:
                progress_note = f"\n- **Handoff:** {handoff}"

    next_step = sanitize_context_text(session.get("next") or "", max_len=500)
    next_line = f"- **Next:** {next_step}\n" if next_step else ""

    inbox_section = format_inbox_section(root, codename)
    workflow_section = format_workflow_section(root, codename)
    worktree_section = format_worktree_section(root, codename, session)
    tasks_line = ", ".join(running) if running else "—"
    from repos import self_hosted_aliases

    mode = session_mode(session)
    writable = f"`sessions/{codename}/worktrees/**` + session metadata; `repos/` read-only"
    mode_line = (
        f"- **Mode:** hub (orchestration label — product edits still use worktrees)\n"
        if mode == "hub"
        else ""
    )
    wt = primary_worktree(root, codename, session)
    worktree_note = f"\n- **Product root:** `{wt.relative_to(root)}`" if wt else ""
    self_hosted = self_hosted_aliases(root)
    self_hosted_note = ""
    if self_hosted:
        self_hosted_note = (
            "\n- **Self-hosted:** do not edit hub-root `scripts/`, `.cursor/`, or docs; "
            "use worktree for product code. Hub refresh: `./scripts/hub-upgrade.sh` only."
        )

    return f"""# Session context (this chat)

- **Codename:** `{codename}`
- **Conversation:** `{chat_id}`
- **Title:** {title}
{mode_line}- **Status:** {session.get("status", "draft")}
{next_line}- **Tasks in flight:** {tasks_line}
- **Writable:** {writable}{worktree_note}{self_hosted_note}
{progress_note}
{workflow_section}{worktree_section}{inbox_section}
{goal}
{format_guidelines_section(root, codename, session)}

See [SESSIONS.md](../../SESSIONS.md), [docs/REPOS.md](../../docs/REPOS.md), `sessions/{codename}/BOUNDARIES.md`, `session.json`, `repos.yaml`.
"""


def refresh_binding_contexts(
    root: Path,
    codename: str,
    *,
    conversation_id: str | None = None,
) -> None:
    """Rewrite context snippets for all chats bound to this codename (or one chat)."""
    bindings = _bindings_by_codename(root).get(codename, [])
    if conversation_id:
        bindings = [b for b in bindings if b.get("conversation_id") == conversation_id]
    context_dir(root).mkdir(parents=True, exist_ok=True)
    for binding in bindings:
        cid = binding.get("conversation_id")
        if not cid:
            continue
        context_path(root, cid).write_text(build_context_markdown(root, codename, cid))


def sync_session_from_canonical(
    root: Path,
    codename: str,
    *,
    resume: bool = False,
    refresh_context: bool = True,
    conversation_id: str | None = None,
) -> None:
    """Sync derived session references from sessions/<codename>/session.json."""
    name = validate_codename(codename)
    if resume:
        resume_session_on_bind(root, name)
    else:
        sync_index_from_session(root, name)
    if refresh_context:
        refresh_binding_contexts(root, name, conversation_id=conversation_id)


def is_active_session(root: Path, codename: str, index_entry: dict | None = None) -> bool:
    try:
        name = validate_codename(codename)
    except ValueError:
        return False
    session_dir = root / "sessions" / name
    if not session_dir.is_dir():
        return False
    if not (session_dir / "session.json").exists():
        return False
    session_json = _load_session_json(root, codename)
    index_entry = index_entry or {}
    status = (session_json or {}).get("status") or index_entry.get("status") or "draft"
    if status in CLOSED_STATUSES:
        return False
    if index_entry.get("ended") or (session_json or {}).get("ended"):
        return False
    return True


def validate_active_codename(root: Path, codename: str) -> None:
    try:
        name = validate_codename(codename)
    except ValueError as exc:
        raise SystemExit(f"Error: {exc}") from exc
    session_dir = root / "sessions" / name
    if not session_dir.is_dir():
        raise SystemExit(f"Error: sessions/{name}/ does not exist")
    index_sessions = _index_sessions(root)
    if not is_active_session(root, name, index_sessions.get(name, {})):
        raise SystemExit(f"Error: session {name} is not active (ended or missing session.json)")


def _codename_from_name(root: Path, name: str | None) -> str | None:
    if not name:
        return None
    candidates = [name.strip()]
    prefix = tmux_window_prefix()
    if prefix and name.startswith(prefix):
        candidates.append(name[len(prefix) :])
    index_sessions = _index_sessions(root)
    for candidate in candidates:
        if candidate and is_active_session(root, candidate, index_sessions.get(candidate, {})):
            return candidate
    return None


def codename_from_tmux(root: Path | None = None) -> str | None:
    return _codename_from_name(root or hub_root(), get_tmux_window_name())


def codename_from_tmux_pane(root: Path | None = None) -> str | None:
    return _codename_from_name(root or hub_root(), get_tmux_pane_codename())


def _pane_path_under_hub_root(root: Path, pane_path: str) -> bool:
    """True when pane cwd is under hub_root (includes worktree subdirs)."""
    if not pane_path or not pane_path.strip():
        return False
    try:
        resolved = Path(pane_path).expanduser().resolve()
    except OSError:
        return False
    return _path_is_within(resolved, root.resolve())


def get_tmux_session_bound_codenames(root: Path | None = None) -> set[str]:
    """Distinct pane-option codenames on panes in this tmux session under hub_root."""
    if not os.environ.get("TMUX"):
        return set()
    opt = tmux_pane_option()
    result = _run_tmux(
        "list-panes",
        "-s",
        "-F",
        f"#{{@{opt}}}\t#{{pane_current_path}}",
    )
    if not result:
        return set()
    root = (root or hub_root()).resolve()
    codenames: set[str] = set()
    index_sessions = _index_sessions(root)
    for line in result.stdout.splitlines():
        parts = line.split("\t", 1)
        name = parts[0].strip() if parts else ""
        pane_path = parts[1].strip() if len(parts) > 1 else ""
        if not name or not _pane_path_under_hub_root(root, pane_path):
            continue
        if is_active_session(root, name, index_sessions.get(name, {})):
            codenames.add(name)
    return codenames


def codename_from_tmux_session(root: Path | None = None) -> str | None:
    """When exactly one codename is bound on sibling tabs, inherit it for new tabs."""
    root = root or hub_root()
    codenames = get_tmux_session_bound_codenames(root)
    if len(codenames) == 1:
        return next(iter(codenames))
    return None


def resolve_codename(root: Path | None = None) -> tuple[str | None, str]:
    """Return (codename, source) where source is binding, tmux-pane, tmux-session, tmux, or ''."""
    root = root or hub_root()
    cid = conversation_id()
    if cid:
        binding = read_binding(root, cid)
        if binding:
            return binding["codename"], "binding"
    pane_codename = codename_from_tmux_pane(root)
    if pane_codename:
        return pane_codename, "tmux-pane"
    session_codename = codename_from_tmux_session(root)
    if session_codename:
        return session_codename, "tmux-session"
    tmux_codename = codename_from_tmux(root)
    if tmux_codename:
        return tmux_codename, "tmux"
    return None, ""


def resolve_source_label(source: str) -> str:
    return RESOLVE_SOURCE_LABELS.get(source, source)


def safe_id(conversation_id: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]", "_", conversation_id)


def bindings_dir(root: Path | None = None) -> Path:
    root = root or hub_root()
    return root / "sessions" / "bindings"


def context_dir(root: Path | None = None) -> Path:
    root = root or hub_root()
    return root / "sessions" / "context"


def binding_path(root: Path, conversation_id: str) -> Path:
    return bindings_dir(root) / f"{safe_id(conversation_id)}.json"


def context_path(root: Path, conversation_id: str) -> Path:
    return context_dir(root) / f"{safe_id(conversation_id)}.md"


def read_binding(root: Path, conversation_id: str, *, active_only: bool = True) -> dict | None:
    path = binding_path(root, conversation_id)
    if not path.exists():
        return None
    data = _load_json_file(path)
    if not data:
        return None
    if active_only and data.get("status") == "ended":
        return None
    return data


def write_binding(root: Path, conversation_id: str, codename: str) -> dict:
    bindings_dir(root).mkdir(parents=True, exist_ok=True)
    now = _utc_now_iso()
    existing = read_binding(root, conversation_id, active_only=False)
    data = {
        "conversation_id": conversation_id,
        "codename": codename,
        "bound_at": (existing or {}).get("bound_at") or now,
        "last_active_at": now,
    }
    binding_path(root, conversation_id).write_text(json.dumps(data, indent=2) + "\n")
    return data


def clear_binding(root: Path, conversation_id: str) -> bool:
    removed = False
    path = binding_path(root, conversation_id)
    if path.exists():
        path.unlink()
        removed = True
    ctx = context_path(root, conversation_id)
    if ctx.exists():
        ctx.unlink()
        removed = True
    return removed


def write_context_file(root: Path, conversation_id: str, codename: str) -> Path:
    out = context_path(root, conversation_id)
    context_dir(root).mkdir(parents=True, exist_ok=True)
    out.write_text(build_context_markdown(root, codename, conversation_id))
    return out


def bind_session_context(root: Path, codename: str, cid: str | None = None) -> None:
    validate_active_codename(root, codename)
    resume_session_on_bind(root, codename)
    chat_id = cid or conversation_id()
    if chat_id:
        write_binding(root, chat_id, codename)
        write_context_file(root, chat_id, codename)
    set_tmux_pane_codename(codename)
    rename_tmux_for_codename(codename)


def unbind_session_context(root: Path, cid: str | None = None) -> None:
    chat_id = cid or conversation_id()
    if chat_id:
        clear_binding(root, chat_id)
    clear_tmux_pane_codename()


def _bindings_by_codename(root: Path) -> dict[str, list[dict]]:
    by_codename: dict[str, list[dict]] = {}
    bdir = bindings_dir(root)
    if not bdir.exists():
        return by_codename
    for path in sorted(bdir.glob("*.json")):
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError:
            continue
        name = data.get("codename")
        if name:
            by_codename.setdefault(name, []).append(data)
    return by_codename


def list_active_sessions(root: Path | None = None) -> list[dict]:
    root = root or hub_root()
    index_sessions = _index_sessions(root)
    codenames = set(index_sessions)
    sessions_dir = root / "sessions"
    if sessions_dir.exists():
        for path in sessions_dir.iterdir():
            name = path.name
            if path.is_dir() and not name.startswith("_") and name not in RESERVED_SESSION_DIRS:
                if (path / "session.json").exists():
                    codenames.add(name)

    bindings_map = _bindings_by_codename(root)
    current_cid = conversation_id()
    tmux_window = get_tmux_window_name()
    pane_codename = get_tmux_pane_codename()
    session_codenames = get_tmux_session_bound_codenames(root)
    active: list[dict] = []

    for codename in sorted(codenames):
        if not is_active_session(root, codename, index_sessions.get(codename, {})):
            continue
        index_entry = index_sessions.get(codename, {})
        session_json = _load_session_json(root, codename) or {}
        bindings = bindings_map.get(codename, [])
        bound_here = any(b.get("conversation_id") == current_cid for b in bindings) if current_cid else False
        bound_tmux = codename in {
            tmux_window,
            pane_codename,
            tmux_window_label(codename),
        } - {None, ""}
        bound_session = codename in session_codenames and not bound_tmux
        tasks = session_json.get("tasks") or []
        active.append(
            {
                "codename": codename,
                "title": session_json.get("title") or index_entry.get("title") or "",
                "status": session_json.get("status") or index_entry.get("status") or "draft",
                "created": session_json.get("created") or index_entry.get("created") or "",
                "next": (session_json.get("next") or index_entry.get("next") or "").strip(),
                "bound_chats": len(bindings),
                "bound_this_chat": bound_here,
                "bound_this_tmux": bound_tmux,
                "bound_this_session": bound_session,
                "tasks_in_progress": [t.get("id") for t in tasks if t.get("status") == "in_progress"],
            }
        )
    return active


def print_session_table(
    sessions: list[dict],
    *,
    stream=None,
    marker: str = "bound_this_chat",
) -> None:
    stream = stream or sys.stdout
    if not sessions:
        print("No open sessions.", file=stream)
        return
    print(f"{'#':<3} {'codename':<14} {'status':<12} title", file=stream)
    print("-" * 56, file=stream)
    for i, s in enumerate(sessions, 1):
        title = (s["title"] or "(no title)")[:36]
        here = " *" if s.get(marker) else ""
        print(f"{i:<3} {s['codename']:<14} {s['status']:<12} {title}{here}", file=stream)


def prompt_is_start_new(text: str) -> bool:
    t = text.lower().strip()
    return bool(
        re.search(
            r"(^|\s)(start new session|/start-work|start work|new session)(\s|$|—|-|:)",
            t,
        )
    )


def prompt_is_end_session(text: str) -> bool:
    t = text.lower().strip()
    return bool(
        re.search(
            r"(^|\s)(end session|kill session|/end-session|close session|finish session|done with session)(\s|$|—|-|:)",
            t,
        )
    )


def _read_tty_line(prompt: str) -> str:
    try:
        with open("/dev/tty", "r") as tty:
            if prompt:
                sys.stderr.write(prompt)
                sys.stderr.flush()
            line = tty.readline()
    except OSError as exc:
        raise SystemExit(f"Cannot read from /dev/tty: {exc}") from exc
    except KeyboardInterrupt:
        sys.stderr.write("\nSession selection cancelled.\n")
        sys.stderr.flush()
        raise SystemExit(130) from None
    if not line:
        raise SystemExit(1)
    return line.strip()


def run_interactive_session_picker(root: Path | None = None) -> str:
    root = root or hub_root()
    sessions = list_active_sessions(root)

    print("", file=sys.stderr)
    print("Session required for this tab.", file=sys.stderr)
    print("", file=sys.stderr)
    if sessions:
        print(f"{'#':<3} {'codename':<14} {'status':<12} title", file=sys.stderr)
        print("-" * 60, file=sys.stderr)
        for i, s in enumerate(sessions, 1):
            title = (s["title"] or "(no title)")[:32]
            here = " *" if s["bound_this_tmux"] or s.get("bound_this_session") else ""
            print(f"{i:<3} {s['codename']:<14} {s['status']:<12} {title}{here}", file=sys.stderr)
        new_num = len(sessions) + 1
        print(f"{new_num:<3} {'(new)':<14} {'—':<12} fresh codename and session folder", file=sys.stderr)
    else:
        new_num = 1
        print("No open sessions — a new one will be created.", file=sys.stderr)
    print("", file=sys.stderr)
    print("Enter a number, codename, or 'new'.", file=sys.stderr)

    codenames = {s["codename"] for s in sessions}
    while True:
        try:
            choice = _read_tty_line("Session> ")
        except SystemExit:
            print("", file=sys.stderr)
            raise

        if not choice:
            continue
        lower = choice.lower()
        if lower in {"new", "new session", "n"} or (choice.isdigit() and int(choice) == new_num):
            result = subprocess.run(
                [str(root / "scripts" / "new-session.sh")],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                msg = (result.stderr or result.stdout or "new session failed").strip()
                print(msg, file=sys.stderr)
                continue
            stdout = result.stdout.strip()
            if not stdout:
                print("Error: new session returned no codename.", file=sys.stderr)
                continue
            try:
                codename = validate_codename(stdout.splitlines()[0])
            except ValueError as exc:
                print(f"Error: {exc}", file=sys.stderr)
                continue
            prompt_new_session_title(root, codename)
            return codename
        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(sessions):
                return sessions[idx - 1]["codename"]
            print(f"Invalid number: {choice}", file=sys.stderr)
            continue
        if choice in codenames:
            return choice
        try:
            return validate_codename(choice)
        except ValueError:
            pass
        print(f"Unknown session: {choice}", file=sys.stderr)


def ensure_session(
    root: Path | None = None,
    *,
    interactive: bool = True,
    force_pick: bool = False,
) -> str:
    """Resolve or interactively pick+bind a session; returns codename.

    force_pick=True (workspace-agent): always show the session list; ignore existing
    tmux pane/window/session bindings so the user can switch sessions.
    """
    root = root or hub_root()
    if not force_pick:
        codename, source = resolve_codename(root)
        if codename:
            if source in ("tmux-session", "tmux-pane"):
                bind_session_context(root, codename)
            return codename
        if not interactive:
            raise SystemExit("No session bound for this tab.")
        if not os.path.exists("/dev/tty") or not os.access("/dev/tty", os.R_OK):
            raise SystemExit("No /dev/tty for interactive session picker.")
        inherited = codename_from_tmux_session(root)
        if inherited:
            bind_session_context(root, inherited)
            return inherited
        codename = run_interactive_session_picker(root)
        bind_session_context(root, codename)
        return codename

    if not interactive:
        codename, _ = resolve_codename(root)
        if codename:
            return codename
        raise SystemExit("No session bound for this tab.")
    if not os.path.exists("/dev/tty") or not os.access("/dev/tty", os.R_OK):
        raise SystemExit("No /dev/tty for interactive session picker.")
    codename = run_interactive_session_picker(root)
    bind_session_context(root, codename)
    return codename


def format_session_start_prompt(root: Path | None = None) -> str:
    root = root or hub_root()
    sessions = list_active_sessions(root)
    lines = [
        "## Sessions",
        "",
        "This chat is not bound to a session yet. Choose one:",
        "",
    ]
    if sessions:
        lines.append("**Open sessions:**")
        lines.append("")
        for i, s in enumerate(sessions, 1):
            title = sanitize_context_text(s["title"] or "(no title)", max_len=80) or "(no title)"
            bind_note = " *(bound to this chat)*" if s["bound_this_chat"] else ""
            if s["bound_this_tmux"] and not s["bound_this_chat"]:
                bind_note = " *(this tmux tab)*"
            elif s.get("bound_this_session") and not s["bound_this_chat"]:
                bind_note = " *(bound on another tab in this tmux session)*"
            elif s["bound_chats"] and not s["bound_this_chat"]:
                bind_note = f" *({s['bound_chats']} chat(s) bound)*"
            tasks = ""
            if s["tasks_in_progress"]:
                tasks = f" — tasks: {', '.join(s['tasks_in_progress'])}"
            next_note = ""
            next_text = sanitize_context_text(s.get("next") or "", max_len=80)
            if next_text:
                next_note = f" — next: {next_text}"
            lines.append(
                f"{i}. **`{s['codename']}`** — {title} [{s['status']}] "
                f"(created {s['created']}){bind_note}{tasks}{next_note}"
            )
        lines.extend(
            [
                "",
                f"{len(sessions) + 1}. **New session** — fresh codename and session folder",
                "",
                "Reply with the **codename** to continue, or **new** (or **new session**) to start fresh.",
            ]
        )
    else:
        lines.extend(
            [
                "No open sessions found.",
                "",
                "Reply **new** (or **new session**) to create one, or name a codename to bind if you know it.",
            ]
        )
    lines.extend(
        [
            "",
            f"Tip: tmux window renames to `{tmux_window_label('codename') or '<codename>'}` when bound.",
            "",
            "After you choose: `./scripts/bind-session.sh <codename>` or `./scripts/new-session.sh` + bind.",
        ]
    )
    return "\n".join(lines)


def format_session_start_required(root: Path | None = None) -> str:
    prompt = format_session_start_prompt(root)
    return (
        "Session required. No session is bound for this agent run.\n\n"
        "Show the user the session list below exactly as written, then STOP and wait for their reply "
        "(codename or **new**). Do not edit session-scoped work until they choose.\n\n"
        f"{prompt}"
    )


def close_session_work(root: Path, codename: str, note: str = "") -> None:
    """Mark session completed in session.json, index, progress, TASKS."""
    name = validate_codename(codename)
    session_dir = root / "sessions" / name
    today = date.today().isoformat()
    ended_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    session_json_path = session_dir / "session.json"
    if not session_json_path.exists():
        raise FileNotFoundError(f"Missing {session_json_path}")
    session = _load_json_file(session_json_path)
    if not session:
        raise ValueError(f"Invalid or empty session.json for {name}")
    session["status"] = "completed"
    session["ended"] = today
    session["ended_at"] = ended_at
    for task in session.get("tasks", []):
        if task.get("status") in ("in_progress", "draft"):
            task["status"] = "completed"
    session_json_path.write_text(json.dumps(session, indent=2) + "\n")

    progress_path = session_dir / "progress.json"
    progress = _load_json_file(progress_path) if progress_path.exists() else {}
    progress.update({"status": "completed", "ended": today, "ended_at": ended_at})
    if note and not progress.get("description"):
        progress["description"] = note
    progress_path.write_text(json.dumps(progress, indent=2) + "\n")

    tasks_md = session_dir / "TASKS.md"
    footer = f"\n\n## Session closed ({today})\n\n- Codename: `{name}`\n- Status: completed\n"
    if note:
        footer += f"- Note: {note}\n"
    if tasks_md.exists():
        text = tasks_md.read_text()
        if "## Session closed" not in text:
            tasks_md.write_text(text.rstrip() + footer + "\n")
    else:
        tasks_md.write_text(f"# Session {name}\n{footer}\n")

    index_path = root / "sessions" / "index.json"
    index = _load_json_file(index_path)
    if not isinstance(index.get("sessions"), dict):
        index["sessions"] = {}
    entry = index["sessions"].get(name, {})
    entry.update(
        {
            "title": session.get("title") or entry.get("title", ""),
            "status": "completed",
            "created": session.get("created") or entry.get("created", today),
            "ended": today,
        }
    )
    index["sessions"][name] = entry
    index_path.write_text(json.dumps(index, indent=2) + "\n")
