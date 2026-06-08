#!/usr/bin/env python3
"""Workspace session CLI — shell wrappers and Cursor hooks."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from session_binding import (
    agent_launcher_name,
    bind_session_context,
    close_session_work,
    conversation_id,
    ensure_session,
    format_session_start_prompt,
    format_session_start_required,
    hub_root,
    list_active_sessions,
    print_session_table,
    prompt_is_start_new,
    read_binding,
    read_inbox,
    rename_tmux_for_codename,
    resolve_codename,
    resolve_source_label,
    tmux_window_label,
    unbind_session_context,
    write_context_file,
    write_inbox,
)


def _load_hook_payload() -> dict:
    raw = os.environ.get("HOOK_INPUT", "")
    if raw:
        return json.loads(raw)
    if not sys.stdin.isatty():
        raw = sys.stdin.read()
        if raw.strip():
            return json.loads(raw)
    return {}


def cmd_resolve(_args: argparse.Namespace) -> int:
    root = hub_root()
    codename, _ = resolve_codename(root)
    if not codename:
        print("UNBOUND", file=sys.stderr)
        print(
            f"No session bound. Run: {agent_launcher_name()}  (or ./scripts/bind-session.sh <codename>)",
            file=sys.stderr,
        )
        return 1
    print(codename)
    return 0


def cmd_bind(args: argparse.Namespace) -> int:
    root = hub_root()
    bind_session_context(root, args.codename, conversation_id())
    print(args.codename)
    cid = conversation_id()
    if cid:
        print(f"Bound conversation {cid} -> {args.codename}")
    else:
        print(f"Bound tmux pane -> {args.codename}")
    return 0


def cmd_unbind(_args: argparse.Namespace) -> int:
    root = hub_root()
    cid = conversation_id()
    binding = read_binding(root, cid) if cid else None
    unbind_session_context(root, cid)
    if binding:
        print(f"Unbound: {binding['codename']}" + (f" (conversation {cid})" if cid else ""))
    elif cid:
        print(f"No binding for conversation {cid}")
    else:
        print("Cleared tmux pane binding")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    root = hub_root()
    sessions = list_active_sessions(root)
    if args.format == "json":
        print(json.dumps(sessions, indent=2))
        return 0
    if args.format == "prompt":
        print(format_session_start_prompt(root))
        return 0
    print_session_table(sessions, marker="bound_this_chat")
    return 0


def cmd_ensure(args: argparse.Namespace) -> int:
    print(ensure_session(hub_root(), force_pick=not args.reuse))
    return 0


def cmd_sync(args: argparse.Namespace) -> int:
    root = hub_root()
    codename = args.codename
    if not codename:
        codename, _ = resolve_codename(root)
    if not codename:
        print("Usage: sync [codename]  (or bind a session first)", file=sys.stderr)
        return 1
    sync_session_from_canonical(
        root,
        codename,
        resume=args.resume,
        refresh_context=True,
        conversation_id=conversation_id(),
    )
    print(codename)
    print(f"Synced index and context from sessions/{codename}/session.json")
    return 0


def cmd_rename(args: argparse.Namespace) -> int:
    codename = args.codename
    if not codename:
        codename, _ = resolve_codename(hub_root())
    if not codename:
        print("Usage: rename <codename>  (or bind a session first)", file=sys.stderr)
        return 1
    if rename_tmux_for_codename(codename):
        print(f"tmux window renamed to: {codename}")
        return 0
    if os.environ.get("TMUX"):
        print(f"Warning: could not rename tmux window to {codename}", file=sys.stderr)
        return 1
    print(f"Not in tmux; set terminal title to: {codename}")
    return 0


def cmd_close(args: argparse.Namespace) -> int:
    root = hub_root()
    codename = args.codename
    if not codename:
        codename, _ = resolve_codename(root)
    if not codename:
        print("Usage: close [codename] [note]", file=sys.stderr)
        return 1
    session_dir = root / "sessions" / codename
    if not session_dir.is_dir():
        print(f"Error: no session directory: sessions/{codename}", file=sys.stderr)
        return 1
    close_session_work(root, codename, args.note or "")
    cid = conversation_id()
    unbind_session_context(root, cid)
    print(codename)
    print(f"Closed: sessions/{codename}/")
    if cid:
        print("Cleared binding for this chat and tmux pane")
    else:
        print("Cleared tmux pane binding")
    return 0


def cmd_hook_session_start(_args: argparse.Namespace) -> int:
    payload = _load_hook_payload()
    root = hub_root()
    cid = payload.get("conversation_id", "").strip()
    out: dict = {}
    env: dict = {}

    if cid:
        env["WORKSPACE_CONVERSATION_ID"] = cid
        os.environ["WORKSPACE_CONVERSATION_ID"] = cid

    codename, source = resolve_codename(root)
    if codename:
        if cid and source == "binding":
            write_context_file(root, cid, codename)
        label = resolve_source_label(source)
        window = tmux_window_label(codename) or codename
        extra = (
            f"Session `{codename}` resolved via {label}. "
            f"Tmux window: `{window}`. Writable: sessions/{codename}/worktrees/** + metadata; repos/ read-only."
        )
    else:
        extra = format_session_start_required(root)

    if env:
        out["env"] = env
    if extra:
        out["additional_context"] = extra
    print(json.dumps(out))
    return 0


def cmd_hook_before_prompt(_args: argparse.Namespace) -> int:
    payload = _load_hook_payload()
    root = hub_root()
    cid = payload.get("conversation_id", "").strip()
    prompt = payload.get("prompt", "") or ""
    if not cid:
        return 0

    os.environ["WORKSPACE_CONVERSATION_ID"] = cid
    binding = read_binding(root, cid)

    # End session: session-end skill runs end-session.sh (not here — avoids double close).

    if prompt_is_start_new(prompt) and not binding:
        from session_binding import codename_from_tmux

        tmux_codename = codename_from_tmux(root)
        if tmux_codename:
            bind_session_context(root, tmux_codename, cid)

    return 0


def cmd_hook_session_end(_args: argparse.Namespace) -> int:
    payload = _load_hook_payload()
    cid = payload.get("conversation_id", "").strip()
    if not cid:
        return 0
    root = hub_root()
    if read_binding(root, cid, active_only=False):
        unbind_session_context(root, cid)
    return 0


def cmd_inbox(args: argparse.Namespace) -> int:
    root = hub_root()
    if args.inbox_command == "read":
        content = read_inbox(root, args.codename)
        if not content:
            print(f"No inbox for {args.codename}.")
            return 0
        print(content)
        return 0

    if args.inbox_command == "write":
        try:
            path = write_inbox(root, args.from_session, args.to_session, args.message)
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        print(f"Wrote to {path.relative_to(root)}")
        return 0

    print("Error: unknown inbox command", file=sys.stderr)
    return 1


def cmd_hook_guard_paths(_args: argparse.Namespace) -> int:
    payload = _load_hook_payload()
    root = hub_root()
    cid = conversation_id() or payload.get("conversation_id", "")
    file_path = payload.get("file_path", "") or ""

    if not cid or not file_path:
        print(json.dumps({"permission": "allow"}))
        return 0

    os.environ["WORKSPACE_CONVERSATION_ID"] = cid
    codename, _ = resolve_codename(root)
    if not codename:
        print(json.dumps({"permission": "allow"}))
        return 0

    from session_binding import guard_path_decision

    print(json.dumps(guard_path_decision(root, codename, file_path)))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Workspace session CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("resolve", help="Print resolved session codename")
    bind_p = sub.add_parser("bind", help="Bind chat and/or tmux pane to codename")
    bind_p.add_argument("codename")
    sub.add_parser("unbind", help="Clear chat and tmux pane binding")
    list_p = sub.add_parser("list", help="List open sessions")
    list_p.add_argument("--format", choices=("table", "json", "prompt"), default="table")
    ensure_p = sub.add_parser("ensure", help="Interactively pick a session (workspace-agent)")
    ensure_p.add_argument(
        "--reuse",
        action="store_true",
        help="Skip picker when this tab already has a tmux/chat binding",
    )
    sync_p = sub.add_parser("sync", help="Sync index/context from session.json")
    sync_p.add_argument("codename", nargs="?")
    sync_p.add_argument(
        "--resume",
        action="store_true",
        help="Also mark session active (same as bind resume)",
    )
    rename_p = sub.add_parser("rename", help="Rename tmux window to codename")
    rename_p.add_argument("codename", nargs="?")
    close_p = sub.add_parser("close", help="Close session work and unbind")
    close_p.add_argument("codename", nargs="?")
    close_p.add_argument("--note", default="")

    inbox_p = sub.add_parser("inbox", help="Cross-session inbox read/write")
    inbox_sub = inbox_p.add_subparsers(dest="inbox_command", required=True)
    inbox_read = inbox_sub.add_parser("read", help="Print inbox for a session")
    inbox_read.add_argument("codename")
    inbox_write = inbox_sub.add_parser("write", help="Append message to another session's inbox")
    inbox_write.add_argument("from_session", metavar="from")
    inbox_write.add_argument("to_session", metavar="to")
    inbox_write.add_argument("message")

    sub.add_parser("hook-session-start")
    sub.add_parser("hook-before-prompt")
    sub.add_parser("hook-session-end")
    sub.add_parser("hook-guard-paths")

    args = parser.parse_args(argv)
    handlers = {
        "resolve": cmd_resolve,
        "bind": cmd_bind,
        "unbind": cmd_unbind,
        "list": cmd_list,
        "ensure": cmd_ensure,
        "sync": cmd_sync,
        "rename": cmd_rename,
        "close": cmd_close,
        "inbox": cmd_inbox,
        "hook-session-start": cmd_hook_session_start,
        "hook-before-prompt": cmd_hook_before_prompt,
        "hook-session-end": cmd_hook_session_end,
        "hook-guard-paths": cmd_hook_guard_paths,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
