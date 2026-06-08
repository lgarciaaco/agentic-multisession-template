#!/usr/bin/env bash
# Create a new codename session: sessions/<codename>/
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

NAME="${1:-}"

python3 <<PY
import json
import sys
from datetime import date
from pathlib import Path

try:
    import yaml
except ImportError:
    print("PyYAML required: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

root = Path("$ROOT")
name = "$NAME".strip()

codenames_path = root / "sessions" / "_codenames.yaml"
example_codenames = root / "sessions" / "_codenames.example.yaml"
if not codenames_path.exists():
    if example_codenames.exists():
        codenames_path.write_text(example_codenames.read_text())
    else:
        codenames_path.write_text(
            yaml.dump(
                {
                    "pools": {
                        "default": [
                            "alpha", "bravo", "charlie", "delta",
                            "echo", "foxtrot", "golf", "hotel",
                        ]
                    },
                    "used": [],
                },
                default_flow_style=False,
                sort_keys=False,
            )
        )

data = yaml.safe_load(codenames_path.read_text())
used = set(data.get("used", []))

if name:
    if name in used:
        print(f"Error: codename '{name}' already used.", file=sys.stderr)
        sys.exit(1)
    codename = name
else:
    codename = None
    for pool in data.get("pools", {}).values():
        for candidate in pool:
            if candidate not in used:
                codename = candidate
                break
        if codename:
            break
    if not codename:
        print("Error: no codenames left in pool.", file=sys.stderr)
        sys.exit(1)

session_dir = root / "sessions" / codename
if session_dir.exists():
    print(f"Error: {session_dir} already exists.", file=sys.stderr)
    sys.exit(1)

template = root / "sessions" / "_template"
for item in ("session.json", "BOUNDARIES.md", "TASKS.md", "progress.json"):
    src = template / item
    if not src.exists():
        print(f"Error: missing template {src}", file=sys.stderr)
        sys.exit(1)

session_dir.mkdir(parents=True)
(session_dir / "worktrees").mkdir(parents=True)
today = date.today().isoformat()

for item in ("session.json", "BOUNDARIES.md", "TASKS.md", "progress.json"):
    text = (template / item).read_text()
    text = text.replace("CODENAME", codename).replace("YYYY-MM-DD", today)
    (session_dir / item).write_text(text)

index_path = root / "sessions" / "index.json"
if not index_path.exists():
    example_index = root / "sessions" / "index.example.json"
    if example_index.exists():
        index_path.write_text(example_index.read_text())
    else:
        index_path.write_text('{"sessions": {}}\n')

index = json.loads(index_path.read_text())
index.setdefault("sessions", {})[codename] = {
    "title": "",
    "status": "draft",
    "created": today,
}
index_path.write_text(json.dumps(index, indent=2) + "\n")

if codename not in used:
    used.add(codename)
    data["used"] = sorted(used)
    codenames_path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))

print(codename)
PY
