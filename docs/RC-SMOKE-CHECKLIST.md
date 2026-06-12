# RC smoke checklist — 1.0.0-rc.1

Run once on the **rc tip** (merged PRs 1–6, `.hub-version` = `1.0.0-rc.1`) before tag prep (PR-7).

**Where to run:** hub install root (directory with local `repos.yaml`, `sessions/`, and `.hub-launcher`). Product edits for rc PRs use `sessions/<codename>/worktrees/hub/`; smoke validates both install root scripts and bound-session guards.

**Template copy:** ship this file under `docs/`; session runs may record results in `sessions/<codename>/artifacts/rc-smoke-results.md` (gitignored).

---

## Prerequisites

- Python 3.10+
- `pip install -r scripts/requirements.txt`
- Optional: `./scripts/install-workspace-agent.sh` (tmux launcher)
- Bound session codename for guard/workflow steps

---

## Checklist

| ID | Area | Command / action | Expected |
|----|------|------------------|----------|
| S1 | Dependencies | `python3 -c "import yaml"` | Exit 0 |
| S2 | Registry | `./scripts/repos-status.sh` | JSON `state: ready` (or `needs_clone` on fresh hub) |
| S3 | Version | `cat .hub-version` | `1.0.0-rc.1` |
| S4 | Session bind | `./scripts/resolve-session.sh` | Prints bound codename |
| S5 | Worktree guard | Bound session: edit allowed under `sessions/<codename>/worktrees/**`; denied under `scripts/`, `repos/` | allow / deny / deny |
| S6 | Workflow artifacts | `test -f sessions/<codename>/workflow.json` and `artifacts/action-plan.md` | Files exist when `/workflow` active |
| S7 | Pre-PR suite | `python3 -m unittest discover -s scripts -p 'test_*.py'` | All tests pass |
| S8 | Binding smoke | `python3 scripts/test_session_binding.py` | OK |
| S9 | Workflow gate scripts | `python3 scripts/test_workflow_gates.py` && `python3 scripts/test_workflow_resume.py` | OK |

### S5 guard verification (optional script)

From hub root with bound codename `<codename>`:

```bash
python3 -c "
from pathlib import Path
import sys
sys.path.insert(0, 'scripts/lib')
from hub_paths import hub_root
from session_binding import guard_path_decision
root = hub_root()
c = '<codename>'
checks = [
  ('worktree', root / f'sessions/{c}/worktrees/hub/README.md'),
  ('hub_scripts', root / 'scripts/repos-status.sh'),
  ('repos', root / 'repos/hub/README.md'),
]
for name, path in checks:
  d = guard_path_decision(root, c, str(path))
  print(name, d.get('permission'))
"
```

Expected: `worktree allow`, `hub_scripts deny`, `repos deny`.

---

## Execution log

Record each run here or in session `artifacts/rc-smoke-results.md`.

| ID | Date | Result | Notes |
|----|------|--------|-------|
| S1 | 2026-06-10 | PASS | PyYAML import OK |
| S2 | 2026-06-10 | PASS | `state: ready`, `self_hosted: true` |
| S3 | 2026-06-10 | PASS | `.hub-version` = `1.0.0-rc.1` |
| S4 | 2026-06-10 | PASS | `resolve-session.sh` → `nova` |
| S5 | 2026-06-10 | PASS | worktree allow; hub_scripts deny; repos deny |
| S6 | 2026-06-10 | PASS | `workflow.json` + `action-plan.md` present for `nova` |
| S7 | 2026-06-10 | PASS | 199 tests OK (worktree rc tip) |
| S8 | 2026-06-10 | PASS | `test_session_binding.py` OK |
| S9 | 2026-06-10 | PASS | workflow gate + resume tests OK |

**Overall:** PASS (9/9) on rc tip @ merge PR #22 (`aab0da3`).

---

## After smoke

- Fix any FAIL before PR-7 tag prep
- Re-run S7–S9 after hub-layer changes
- See [WORKFLOW.md](WORKFLOW.md) for `/workflow` gate flow
