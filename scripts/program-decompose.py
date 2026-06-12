#!/usr/bin/env python3
"""Decompose program ingest into proposed child sessions."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from hub_paths import hub_root, resolve_session_artifact  # noqa: E402
from program_state import default_program, load_program, save_program  # noqa: E402
from repos import load_repos  # noqa: E402
from session_binding import validate_codename  # noqa: E402

SECTION_RE = re.compile(r"^#{2,3}\s+(.+?)\s*$", re.MULTILINE)


def _load_index_codenames(root: Path) -> set[str]:
    index_path = root / "sessions" / "index.json"
    if not index_path.exists():
        return set()
    import json

    data = json.loads(index_path.read_text())
    sessions = data.get("sessions") or {}
    return {validate_codename(name) for name in sessions.keys()}


def _suggest_codename(root: Path, used: set[str], index: int) -> str:
    pool_path = root / "sessions" / "_codenames.yaml"
    candidates: list[str] = []
    if pool_path.exists():
        import yaml

        data = yaml.safe_load(pool_path.read_text()) or {}
        pools = data.get("pools") or {}
        default_pool = pools.get(data.get("active_pool") or "default") or []
        candidates.extend(str(name) for name in default_pool)
    for fallback in ("november", "oscar", "papa", "quebec", "romeo", "sierra"):
        if fallback not in candidates:
            candidates.append(fallback)
    taken = set(used) | _load_index_codenames(root)
    for name in candidates:
        try:
            codename = validate_codename(name)
        except ValueError:
            continue
        if codename not in taken:
            return codename
    return validate_codename(f"child-{index + 1}")


def _default_repo_alias(root: Path) -> str:
    repos = load_repos(root)
    if not repos:
        raise ValueError("repos.yaml has no entries — configure repos before decomposing")
    if "template" in repos:
        return "template"
    return next(iter(repos.keys()))


def parse_ingest(text: str, *, root: Path, default_repo: str) -> list[dict[str, Any]]:
    """Parse markdown ingest into proposed child rows."""
    body = text.strip()
    if not body:
        return []
    sections = list(SECTION_RE.finditer(body))
    rows: list[dict[str, Any]] = []
    used_codenames: set[str] = set()

    if not sections:
        chunks = [line.strip() for line in body.splitlines() if line.strip()]
        if len(chunks) == 1:
            chunks = [body]
        for idx, chunk in enumerate(chunks[:8]):
            title = chunk.split(".", 1)[0].strip()[:80] or f"Child {idx + 1}"
            suggested = _suggest_codename(root, used_codenames, idx)
            used_codenames.add(suggested)
            rows.append(
                {
                    "id": f"pc{idx + 1}",
                    "suggested_codename": suggested,
                    "title": title,
                    "goal": chunk,
                    "repo": default_repo,
                    "depends_on": [],
                }
            )
        return rows

    for idx, match in enumerate(sections):
        title = match.group(1).strip()
        start = match.end()
        end = sections[idx + 1].start() if idx + 1 < len(sections) else len(body)
        goal = body[start:end].strip()
        suggested = _suggest_codename(root, used_codenames, idx)
        used_codenames.add(suggested)
        rows.append(
            {
                "id": f"pc{idx + 1}",
                "suggested_codename": suggested,
                "title": title,
                "goal": goal or title,
                "repo": default_repo,
                "depends_on": [],
            }
        )
    return rows


def render_program_plan(parent: str, rows: list[dict[str, Any]]) -> str:
    lines = [
        f"# Program plan — {parent}",
        "",
        "Proposed child sessions (await **approve decomposition** before bootstrap).",
        "",
        "| ID | Codename | Repo | Title | Depends |",
        "|----|----------|------|-------|---------|",
    ]
    for row in rows:
        depends = ", ".join(row.get("depends_on") or []) or "—"
        lines.append(
            f"| {row['id']} | {row['suggested_codename']} | {row['repo']} | {row['title']} | {depends} |"
        )
    lines.extend(["", "## Goals", ""])
    for row in rows:
        lines.append(f"### {row['id']} — {row['title']}")
        lines.append("")
        lines.append(row.get("goal") or "")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def decompose_program(
    root: Path,
    codename: str,
    *,
    ingest_path: Path | None = None,
    ingest_text: str | None = None,
) -> dict[str, Any]:
    parent = validate_codename(codename)
    session_dir = root / "sessions" / parent
    if not session_dir.is_dir():
        raise ValueError(f"session directory not found: {session_dir}")

    if ingest_text is None:
        if ingest_path is None:
            program_doc = load_program(session_dir) if (session_dir / "program.json").exists() else default_program(parent)
            rel = program_doc.get("ingest_path") or "artifacts/program-ingest.md"
            ingest_path = resolve_session_artifact(session_dir, rel)
        ingest_text = ingest_path.read_text(encoding="utf-8")

    if not ingest_text.strip():
        raise ValueError("ingest is empty — provide markdown content or a non-empty ingest file")

    default_repo = _default_repo_alias(root)
    rows = parse_ingest(ingest_text, root=root, default_repo=default_repo)
    if len(rows) < 1:
        raise ValueError("ingest produced no child rows — add headings or bullet items")

    program = load_program(session_dir) if (session_dir / "program.json").exists() else default_program(parent)
    program["proposed_children"] = rows
    program["decomposition_approved"] = False
    save_program(session_dir, program, codename=parent)

    plan_path = resolve_session_artifact(session_dir, program["plan_path"])
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(render_program_plan(parent, rows), encoding="utf-8")
    return program


def main() -> int:
    parser = argparse.ArgumentParser(description="Decompose program ingest into child plan")
    parser.add_argument("codename", help="Parent session codename")
    parser.add_argument(
        "ingest",
        nargs="?",
        help="Ingest markdown file (default: program.json ingest_path or stdin when '-')",
    )
    args = parser.parse_args()

    root = hub_root()
    codename = validate_codename(args.codename)

    try:
        if args.ingest == "-":
            text = sys.stdin.read()
            decompose_program(root, codename, ingest_text=text)
        elif args.ingest:
            path = Path(args.ingest)
            if not path.is_file():
                print(f"ingest file not found: {path}", file=sys.stderr)
                return 1
            decompose_program(root, codename, ingest_path=path)
        else:
            decompose_program(root, codename)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    session_dir = root / "sessions" / codename
    program = load_program(session_dir)
    print(program["plan_path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
