"""Inbox write provenance sidecars under sessions/_inbox/.provenance/."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

# Codename rules mirror session_binding.validate_codename intentionally — this module
# must stay importable without session_binding to avoid circular imports.
_CODENAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_RESERVED_SESSION_DIRS = frozenset({"bindings", "context", "_inbox"})


def _validate_codename(codename: str) -> str:
    name = codename.strip()
    if not name:
        raise ValueError("codename must not be empty")
    if name.startswith("_") or name in _RESERVED_SESSION_DIRS:
        raise ValueError(f"invalid session codename: {name}")
    if not _CODENAME_RE.fullmatch(name):
        raise ValueError(
            f"invalid session codename: {name!r} "
            "(use lowercase letters, digits, hyphens; no slashes or ..)"
        )
    return name


def inbox_provenance_dir(root: Path) -> Path:
    return root / "sessions" / "_inbox" / ".provenance"


def inbox_provenance_path(root: Path, target_codename: str) -> Path:
    target = _validate_codename(target_codename)
    return inbox_provenance_dir(root) / f"{target}.json"


def inbox_block_marker(from_session: str, date: str, body: str) -> str:
    payload = f"{from_session}|{date}|{body.strip()}"
    digest = hashlib.sha256(payload.encode()).hexdigest()[:16]
    return f"{from_session}:{date}:{digest}"


def load_inbox_provenance(root: Path, target_codename: str) -> dict[str, dict]:
    path = inbox_provenance_path(root, target_codename)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def save_inbox_provenance(root: Path, target_codename: str, data: dict[str, dict]) -> None:
    path = inbox_provenance_path(root, target_codename)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def record_inbox_block_provenance(
    root: Path,
    target_codename: str,
    marker: str,
    *,
    kind: str,
    verified_from: str,
    caller: str,
) -> None:
    data = load_inbox_provenance(root, target_codename)
    data[marker] = {
        "kind": kind,
        "verified_from": verified_from,
        "caller": caller,
    }
    save_inbox_provenance(root, target_codename, data)


def get_inbox_block_provenance(
    root: Path, target_codename: str, marker: str
) -> dict | None:
    entry = load_inbox_provenance(root, target_codename).get(marker)
    return entry if isinstance(entry, dict) else None
