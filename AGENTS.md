# Agent guide

## First run (agentic bootstrap)

User cloned **agentic-multisession-template**, `cd` here, started you. **You** drive setup.

```bash
./scripts/repos-status.sh    # always start here — JSON state
```

Canonical bootstrap playbook: **`.cursor/skills/bootstrap-hub/SKILL.md`** · [docs/REPOS.md](docs/REPOS.md) · [README.md](README.md#quick-start-agentic-first)

Hub install if needed: `pip install -r scripts/requirements.txt` && `./scripts/install-workspace-agent.sh`

---

## Start work

**Tmux:** `$(cat .hub-launcher)` — not bare `agent`.

**Cursor:** **start work** / **`/start-work`** → `.cursor/skills/session-start/SKILL.md`

1. `./scripts/repos-status.sh` — if not `ready` and user wants **product** work, bootstrap repos first (ask if missing).
2. `./scripts/resolve-session.sh` or picker → bind codename (hooks auto-persist from tmux pane/window, not sibling inherit; first-prompt fallback — see [SESSIONS.md](SESSIONS.md) Chat auto-bind; `./scripts/session-audit.sh` to verify)
3. **Scope metadata** — when work intent is clear, run `./scripts/set-session-scope.sh <codename> --title "…" --goal "…"` before the first product edit (see [SESSIONS.md](SESSIONS.md))
4. `session.json` tasks need `"repo": "<alias>"` matching `repos.yaml`; then `./scripts/ensure-worktrees.sh <codename>`
5. Edit product in `sessions/<codename>/worktrees/<repo>/` only — hub-root blocked when bound ([docs/REPOS.md](docs/REPOS.md) Guards); hub refresh via `./scripts/hub-upgrade.sh`
6. `./scripts/sync-session.sh <codename>` after other metadata edits (non-workflow: also reconciles `TASKS.md` ## Tasks from `session.json` — empty `tasks: []` yields header rows plus empty-state note)

Optional session fields in `session.json`: **`next`** (resume hint); per-task **`pr`**, **`ci`**, **`note`** (shown in chat context). See [docs/REPOS.md](docs/REPOS.md).

When `repos.yaml` uses **GitHub fork workflow** (`github_fork_user`, `remote: github`): push feature branches to **`fork`**, not upstream `origin`. Run `./scripts/configure-git-remotes.sh` if remotes look wrong. See `.cursor/rules/git-fork-pr.mdc`.

Regenerate a multi-root editor workspace: `./scripts/generate-workspace.sh` → `<hub-slug>.code-workspace`.

## Workflow pipeline

**`/workflow-orchestrator`** / **`/workflow-orchestrator status`** → `.cursor/skills/workflow-orchestrator/SKILL.md`

**`/sessions-orchestrator`** → `.cursor/skills/sessions-orchestrator/SKILL.md` · [docs/PROGRAM_ORCHESTRATOR.md](docs/PROGRAM_ORCHESTRATOR.md)

**Check children / `/sessions-orchestrator status`:** parallel Task(child-reviewer) per active child (`model: claude-4.6-sonnet-medium-thinking`); parent chat is **one screen max** — `Parent next:` plus slim markdown table (`Child`, `Phase`, `Gate`, `Next` columns) only. Full **Parent assessment**, **Cross-child check**, and **Child agent action** live in `artifacts/program-status.md` (merge via `./scripts/program-status-report.sh <parent> --reviews-json <path>`). No **Your action — `<codename>`** blocks in chat.

Single-session **Problem → Plan → Code → Review → PR → CI → Delivery** in one chat. State: `sessions/<codename>/workflow.json`; artifacts under `sessions/<codename>/artifacts/`. Chat context includes phase, gates, loops, artifact paths, and **Resume** when `workflow.json` exists.

| Trigger | Action |
|---------|--------|
| `/workflow-orchestrator` | Start or resume from `workflow.json` phase |
| `/workflow-orchestrator status` | One-screen status |
| `/pr-review` | Code review → `.cursor/skills/code-reviewer/SKILL.md` |
| `accept brief` / `accept` | Gate 1 |
| `accept plan` | Gate 2 → `./scripts/workflow-accept-plan.sh <codename>` |
| Inbox at gate | `python3 scripts/workflow-pull-inbox-gate.py <codename> [--apply]` every 2m while at brief/plan gate |
| `reopen brief` / `reopen plan` | `python3 scripts/workflow-reopen-brief.py <codename>` / `python3 scripts/workflow-reopen-plan.py <codename>` |

Workflow phase scripts and CLI commands: [SESSIONS.md#commands](SESSIONS.md#commands).

User gates **only at brief and plan**. Program parent→child gate routing uses **`program-route-feedback.py`** (tmux send-keys to child panes — not inbox). Standalone workflow sessions may still poll inbox at gates via `workflow-pull-inbox-gate.py`; program gate commands no longer auto-apply from inbox. Inbox CLI writes require bound caller to match `from`. Autonomous inner loops for plan, code review, PR creation, and CI observe — no commit/PR pause before review. Plan loop: author dispositions → reviewer validates. Code loop: fixer dispositions SUGGESTION/NIT → specialists validate → **PASS**. After PASS: auto commit + draft PR → CI observe (rebase on conflict, fix on failure, 5-iteration cap) → delivery. Delivery report is inform only. Walkthrough: [docs/WORKFLOW.md](docs/WORKFLOW.md).

## End

**end session** / **`/end-session`** → `.cursor/skills/session-end/SKILL.md` → `./scripts/end-session.sh`

## Hub template upgrade

Installed version: **`.hub-version`** (currently **1.0.0-rc.4**). Upstream check: **`./scripts/hub-status.sh`**.

**1.0.0-rc.1** was the **first stable candidate** release line — not an incremental dev milestone. Later rc bumps (rc.2, rc.3, …) tune production-ready hub machinery toward **1.0.0**; report gaps before the final tag.

Ask **"Is there a new template version?"** → `./scripts/hub-status.sh` → explain hub changes + session notes in plain language (installed `.hub-version` vs upstream template releases).

Say **"Upgrade"** → `.cursor/skills/hub-upgrade/SKILL.md` → `./scripts/hub-upgrade.sh --yes` (hub layer only; keeps `repos.yaml` and session folders).

## Reference

[SESSIONS.md](SESSIONS.md) · [docs/REPOS.md](docs/REPOS.md) · bound `BOUNDARIES.md`

## Scope

- **Product:** `sessions/<codename>/worktrees/**` + session metadata; `repos/` read-only ([docs/REPOS.md](docs/REPOS.md) Guards)
- **Forbidden:** other `sessions/<other>/`, edits under `repos/`, hub-root when bound, direct edits under `sessions/_inbox/` when bound (use `./scripts/session-inbox.sh write` — [docs/REPOS.md](docs/REPOS.md) Guards)

## Coding guidelines

Two levels — read together:

| Level | Source |
|-------|--------|
| **Template** | `.cursor/rules/agent-guidelines.mdc` — docs sync + test minimum (always on) |
| **Hub PRs** | `.cursor/rules/hub-contributing.mdc` — always injected (`alwaysApply: true`); follow only when `session.json` `"mode": "hub"` |
| **Project** | `docs/PROJECT.md` — generic template shipped with the hub; customize from [docs/PROJECT.md.example](docs/PROJECT.md.example) for your stack |

Session context lists which guideline files exist on bind. Optional `guidelines:` in `repos.yaml` — see [docs/REPOS.md](docs/REPOS.md).

## Skills

| | Path |
|-|------|
| Bootstrap | `.cursor/skills/bootstrap-hub` |
| Start | `.cursor/skills/session-start` |
| Program | `.cursor/skills/sessions-orchestrator` |
| Workflow | `.cursor/skills/workflow-orchestrator` |
| Code review (`/pr-review`) | `.cursor/skills/code-reviewer` |
| Hub upgrade | `.cursor/skills/hub-upgrade` |
| Git commit | `.cursor/skills/git-commit` |
| PR create | `.cursor/skills/pr-create` |
| End | `.cursor/skills/session-end` |
| Human tone | `.cursor/skills/write-like-a-human` |
| Skill streamline | `.cursor/skills/skill-optimizer` |
| Loop | `.cursor/skills/loop` — `/loop [interval] <prompt>`, inbox gate polling |

## Skill streamline

Load [`.cursor/skills/skill-optimizer/SKILL.md`](.cursor/skills/skill-optimizer/SKILL.md) when creating, reviewing, or improving any skill under `.cursor/skills/` — especially before opening a hub PR that touches skill copy.

**When to load:** hub skill edits, workflow skill additions, or when a skill grows verbose agent-unfriendly prose (duplicate error blocks, user-facing narration, decorative formatting).

**Must preserve:** all commands, paths, gates, script and API calls, essential error handling, activation print lines, and behavioral semantics — streamlining is structural, not functional.

**Quality targets:** concise agent-command specs; user-interaction steps converted to direct commands; redundant examples trimmed to format definitions where needed. Aim for shorter, scannable skills — no mandated percent line-reduction rule.

After structural edits on human-facing artifacts (briefs, delivery reports, PR text), run [write-like-a-human](.cursor/skills/write-like-a-human/SKILL.md) as a final tone pass.

## Cross-session inbox

`./scripts/session-inbox.sh write <from> <to> "message"` · read on bind or `./scripts/session-inbox.sh read <codename>`

Program parent gate: parent **always reviews** child brief/plan against decomposition at gates (monitor `parent_next_action`, `gate_review` paths). Route with required `--gate` and `--message` (gate strings must match script choices):

```bash
python3 scripts/program-route-feedback.py <parent> <child> \
  --gate brief_review --message "accept brief"
python3 scripts/program-route-feedback.py <parent> <child> \
  --gate plan_user_review --message "accept plan"
python3 scripts/program-route-feedback.py <parent> <child> \
  --gate brief_review --message "reopen brief"
python3 scripts/program-route-feedback.py <parent> <child> \
  --gate plan_user_review --message "reopen plan"
```

Free-text corrections: `program-route-feedback.py <parent> <child> --message "…"` (no `--gate`). See [sessions/_inbox/README.md](sessions/_inbox/README.md) and [docs/PROGRAM_ORCHESTRATOR.md](docs/PROGRAM_ORCHESTRATOR.md) § Parent gate review (mandatory).

**Idempotent routing:** Route each gate command once per gate. Before autonomous re-sends, check `program-monitor.py` child fields `routable` and `route_skip_reason`. `program-route-feedback.py` skips already-accepted accepts, duplicate messages within 5 minutes, and corrections outside gate phases; use `--force` to override those skips (wrong-phase gate routes still fail). Details: [docs/PROGRAM_ORCHESTRATOR.md](docs/PROGRAM_ORCHESTRATOR.md) Local-trust boundaries.

## Git / PRs

- **Never** `gh pr merge --auto` or auto-merge
- **Never** merge/push `main` unless user explicitly asks
- **Fork workflow** (when configured in `repos.yaml`): push to `fork`, PR with `--head {github_fork_user}:branch` — [CONTRIBUTING.md](CONTRIBUTING.md), `.cursor/rules/git-fork-pr.mdc`
