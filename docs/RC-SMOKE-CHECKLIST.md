# RC smoke checklist

Run once on the **installed rc tip** before tag prep. Compare `cat .hub-version` to `./scripts/hub-status.sh` (installed vs upstream) — do not hardcode a fixed rc semver in this checklist.

**Where to run:** hub install root (directory with local `repos.yaml`, `sessions/`, and `.hub-launcher`). Product edits for rc PRs use `sessions/<codename>/worktrees/hub/`; smoke validates both install root scripts and bound-session guards.

**Template copy:** ship this file under `docs/`; session runs may record results in `sessions/<codename>/artifacts/rc-smoke-results.md` (gitignored).

---

## Prerequisites

- Python 3.10+
- `pip install -r scripts/requirements.txt`
- Optional: `./scripts/install-workspace-agent.sh` (tmux launcher)
- Bound session codename for guard and workflow steps

---

## Checklist

| ID | Area | Command / action | Expected |
|----|------|------------------|----------|
| S1 | Dependencies | `python3 -c "import yaml"` | Exit 0 |
| S2 | Registry | `./scripts/repos-status.sh` | JSON `state: ready` (or `needs_clone` on fresh hub) |
| S3 | Version | `cat .hub-version` and `./scripts/hub-status.sh` | Installed `.hub-version` matches `hub-status.sh` installed line (no hardcoded rc semver in Expected) |
| S4 | Session bind | `./scripts/resolve-session.sh` | Prints bound codename |
| S5 | Worktree guard | Bound session: edit allowed under `sessions/<codename>/worktrees/**`; denied under `scripts/`, `repos/` | allow / deny / deny |
| S6 | Workflow artifacts | `test -f sessions/<codename>/workflow.json && test -f sessions/<codename>/artifacts/action-plan.md` | Files exist when `/workflow-orchestrator` is active |
| S7 | Pre-PR suite | `python3 -m unittest discover -s scripts -p 'test_*.py'` | All tests pass |
| S8 | Binding smoke | `python3 scripts/test_session_binding.py` | OK |
| S9 | Workflow gate scripts | `python3 scripts/test_workflow_gates.py` && `python3 scripts/test_workflow_resume.py` | OK |
| S10 | Program monitor | `python3 scripts/program-monitor.py <parent>` (active program parent) | JSON or text table with child phase/gate columns; no traceback |
| S11 | Route feedback dry-run | `python3 scripts/program-route-feedback.py <parent> <child> --gate brief_review --message "accept brief" --dry-run` | Prints routed message; no tmux send-keys |
| S12 | Tab cleanup | `python3 scripts/test_program_orchestrator.py ProgramChildTabsTests.test_cleanup_completed_children_updates_status_and_closes_tab` | OK (or covered by S7 suite) |

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

Historical snapshot from an earlier rc smoke run — record new runs here or in session `artifacts/rc-smoke-results.md`.

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
| S10–S12 | 2026-06-13 | PENDING | rc.4 post-xray smoke — optional program rows added; run when program parent + tmux available (head `14a3cfe`) |

**Overall:** PASS (9/9) on rc tip @ merge PR #22 (`aab0da3`). rc.4 S10–S12 pending.

---

## After smoke

- Fix any FAIL before the next rc tag prep
- Re-run S7–S9 after hub-layer changes
- See [docs/WORKFLOW.md](./WORKFLOW.md) for `/workflow-orchestrator` gate flow
