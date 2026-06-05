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
RESOLVE_SOURCE_LABELS = {
    "binding": "this chat",
    "tmux-pane": "tmux tab",
    "tmux-session": "tmux session (sibling tab)",
    "tmux": "tmux window name",
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def hub_root() -> Path:
    env = os.environ.get("WORKSPACE_ROOT", "").strip()
    if env:
        return Path(env)
    return Path(__file__).resolve().parent.parent.parent


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
    """Derive window prefix from hub slug (e.g. immo-investor → immo-)."""
    name = slug.strip()
    if not name:
        return ""
    if name.endswith("-agent"):
        name = name[: -len("-agent")]
    stem = name.split("-", 1)[0] if "-" in name else name
    return f"{stem}-"


def tmux_window_prefix() -> str:
    if "WORKSPACE_TMUX_WINDOW_PREFIX" in os.environ:
        return os.environ["WORKSPACE_TMUX_WINDOW_PREFIX"]
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
    name = codename.strip()
    if not name:
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


def _index_sessions(root: Path) -> dict:
    index_path = root / "sessions" / "index.json"
    if not index_path.exists():
        return {}
    return json.loads(index_path.read_text()).get("sessions", {})


def _load_session_json(root: Path, codename: str) -> dict | None:
    path = root / "sessions" / codename / "session.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def _write_session_json(root: Path, codename: str, session: dict) -> None:
    path = root / "sessions" / codename / "session.json"
    path.write_text(json.dumps(session, indent=2) + "\n")


def _tasks_goal_line(session_dir: Path) -> str:
    tasks_path = session_dir / "TASKS.md"
    if not tasks_path.exists():
        return ""
    lines = tasks_path.read_text().splitlines()
    goal_lines: list[str] = []
    in_goal = False
    for line in lines:
        if line.startswith("## Goal"):
            in_goal = True
            goal_lines.append(line)
            continue
        if in_goal:
            if line.startswith("## "):
                break
            if line.strip():
                goal_lines.append(line)
    return "\n".join(goal_lines)


def sync_index_from_session(root: Path, codename: str, session: dict | None = None) -> None:
    """Copy canonical fields from session.json into sessions/index.json."""
    session = session or _load_session_json(root, codename) or {}
    index_path = root / "sessions" / "index.json"
    index = json.loads(index_path.read_text())
    entry = index.setdefault("sessions", {}).get(codename, {})
    entry.update(
        {
            "title": session.get("title") or entry.get("title", ""),
            "status": session.get("status") or entry.get("status", "draft"),
            "created": session.get("created") or entry.get("created", date.today().isoformat()),
        }
    )
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
    for key in ("ended", "ended_at", "paused_at"):
        if key in session:
            session.pop(key, None)
            changed = True
    if changed:
        _write_session_json(root, codename, session)

    progress_path = root / "sessions" / codename / "progress.json"
    if progress_path.exists():
        progress = json.loads(progress_path.read_text())
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
    message = message.strip()
    if not message:
        raise ValueError("inbox message must not be empty")
    for name in (from_codename, to_codename):
        session_dir = root / "sessions" / name
        if not session_dir.is_dir() or name.startswith("_") or name in RESERVED_SESSION_DIRS:
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
    """hub = hub maintenance at root; default = product work in worktrees."""
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
        lines.append(
            f"- **`{task.get('id', 'main')}`** (`{repo}`) — `{rel}` (branch `{branch}`) — {state}"
        )
    return "\n".join(lines) + "\n"


def guard_path_decision(root: Path, codename: str, file_path: str) -> dict:
    """Cursor hook: allow/deny edits — art-style repos/ read-only, worktrees writable."""
    allow = {"permission": "allow"}
    if not codename or not file_path:
        return allow

    norm = file_path.replace("\\", "/")
    hub = str(root).replace("\\", "/")
    if not norm.startswith(hub):
        return allow

    if f"/sessions/{codename}/" in norm or norm.endswith(f"/sessions/{codename}"):
        return allow

    if "/sessions/_inbox/" in norm:
        return allow

    if "/repos/" in norm and "/sessions/" not in norm:
        return {
            "permission": "deny",
            "user_message": "repos/ is read-only (reference clones).",
            "agent_message": f"Edit only under sessions/{codename}/worktrees/. Run ./scripts/clone-repos.sh to refresh refs.",
        }

    match = re.search(r"/sessions/([a-z0-9-]+)/", norm)
    if match and match.group(1) != codename:
        other = match.group(1)
        if other not in RESERVED_SESSION_DIRS and (root / "sessions" / other).is_dir():
            return {
                "permission": "deny",
                "user_message": f"This chat is bound to session {codename}, not {other}.",
                "agent_message": f"Do not edit sessions/{other}/. This chat is bound to {codename}.",
            }

    return allow


def format_inbox_section(root: Path, codename: str) -> str:
    content = read_inbox(root, codename)
    if not content:
        return ""
    return f"\n## Inbox (from other sessions)\n\n{content}\n"


def build_context_markdown(root: Path, codename: str, chat_id: str) -> str:
    """Agent-facing context snippet from canonical session metadata."""
    session_dir = root / "sessions" / codename
    session = _load_session_json(root, codename) or {}
    goal = _tasks_goal_line(session_dir)
    tasks = session.get("tasks") or []
    running = [t.get("id") for t in tasks if t.get("status") in ("in_progress", "running", "draft")]
    title = session.get("title") or "(no title)"

    progress_note = ""
    progress_path = session_dir / "progress.json"
    if progress_path.exists():
        progress = json.loads(progress_path.read_text())
        if progress.get("handoff_note"):
            progress_note = f"\n- **Handoff:** {progress['handoff_note']}"

    inbox_section = format_inbox_section(root, codename)
    worktree_section = format_worktree_section(root, codename, session)
    tasks_line = ", ".join(running) if running else "—"
    mode = session_mode(session)
    if mode == "hub":
        writable = "hub root (`scripts/`, `.cursor/`, docs) + `sessions/<codename>/`"
    else:
        writable = f"`sessions/{codename}/worktrees/**` + session metadata; `repos/` read-only"
    mode_line = f"- **Mode:** hub\n" if mode == "hub" else ""
    wt = primary_worktree(root, codename, session)
    worktree_note = f"\n- **Product root:** `{wt.relative_to(root)}`" if wt else ""

    return f"""# Session context (this chat)

- **Codename:** `{codename}`
- **Conversation:** `{chat_id}`
- **Title:** {title}
{mode_line}- **Status:** {session.get("status", "draft")}
- **Tasks in flight:** {tasks_line}
- **Writable:** {writable}{worktree_note}
{progress_note}
{worktree_section}{inbox_section}
{goal}

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
    if resume:
        resume_session_on_bind(root, codename)
    else:
        sync_index_from_session(root, codename)
    if refresh_context:
        refresh_binding_contexts(root, codename, conversation_id=conversation_id)


def is_active_session(root: Path, codename: str, index_entry: dict | None = None) -> bool:
    session_dir = root / "sessions" / codename
    if not session_dir.is_dir() or codename.startswith("_") or codename in RESERVED_SESSION_DIRS:
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
    session_dir = root / "sessions" / codename
    if not session_dir.is_dir():
        raise SystemExit(f"Error: sessions/{codename}/ does not exist")
    index_sessions = _index_sessions(root)
    if not is_active_session(root, codename, index_sessions.get(codename, {})):
        raise SystemExit(f"Error: session {codename} is not active (ended or missing session.json)")


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


def get_tmux_session_bound_codenames(root: Path | None = None) -> set[str]:
    """Distinct pane-option codenames set on panes in the current tmux session."""
    if not os.environ.get("TMUX"):
        return set()
    opt = tmux_pane_option()
    result = _run_tmux("list-panes", "-s", "-F", f"#{{@{opt}}}")
    if not result:
        return set()
    root = root or hub_root()
    codenames: set[str] = set()
    for line in result.stdout.splitlines():
        name = line.strip()
        if name and is_active_session(root, name, _index_sessions(root).get(name, {})):
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
    data = json.loads(path.read_text())
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
                check=True,
            )
            return result.stdout.strip().splitlines()[0]
        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(sessions):
                return sessions[idx - 1]["codename"]
            print(f"Invalid number: {choice}", file=sys.stderr)
            continue
        if choice in codenames:
            return choice
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
            if source == "tmux-session":
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
            title = s["title"] or "(no title)"
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
            lines.append(
                f"{i}. **`{s['codename']}`** — {title} [{s['status']}] "
                f"(created {s['created']}){bind_note}{tasks}"
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
    session_dir = root / "sessions" / codename
    today = date.today().isoformat()
    ended_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    session_json_path = session_dir / "session.json"
    session = json.loads(session_json_path.read_text())
    session["status"] = "completed"
    session["ended"] = today
    session["ended_at"] = ended_at
    for task in session.get("tasks", []):
        if task.get("status") in ("in_progress", "draft"):
            task["status"] = "completed"
    session_json_path.write_text(json.dumps(session, indent=2) + "\n")

    progress_path = session_dir / "progress.json"
    progress = json.loads(progress_path.read_text()) if progress_path.exists() else {}
    progress.update({"status": "completed", "ended": today, "ended_at": ended_at})
    if note and not progress.get("description"):
        progress["description"] = note
    progress_path.write_text(json.dumps(progress, indent=2) + "\n")

    tasks_md = session_dir / "TASKS.md"
    footer = f"\n\n## Session closed ({today})\n\n- Codename: `{codename}`\n- Status: completed\n"
    if note:
        footer += f"- Note: {note}\n"
    if tasks_md.exists():
        text = tasks_md.read_text()
        if "## Session closed" not in text:
            tasks_md.write_text(text.rstrip() + footer + "\n")
    else:
        tasks_md.write_text(f"# Session {codename}\n{footer}\n")

    index_path = root / "sessions" / "index.json"
    index = json.loads(index_path.read_text())
    entry = index.setdefault("sessions", {}).get(codename, {})
    entry.update(
        {
            "title": session.get("title") or entry.get("title", ""),
            "status": "completed",
            "created": session.get("created") or entry.get("created", today),
            "ended": today,
        }
    )
    index["sessions"][codename] = entry
    index_path.write_text(json.dumps(index, indent=2) + "\n")
