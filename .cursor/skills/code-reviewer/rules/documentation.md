# Documentation rules

Corpus review: consistency, **documentation** duplication, coherence. Code duplication, layout, and dead code → **structure agent** ([structure.md](structure.md)). Doc findings default to **REQUIRED** (not BLOCKER) unless synthesizer maps explicit security lies separately.

## Accuracy

- REQUIRED: documented commands/scripts must exist and match current CLI behavior
- REQUIRED: paths (`sessions/`, `worktrees/`, `repos/`) must match repo layout and hooks
- REQUIRED: `AGENTS.md` skills table must match `.cursor/skills/*/SKILL.md` entries
- Flag broken internal links and references to removed files

## Consistency

- REQUIRED: same term for same concept across docs (`codename`, not mixed with "session name")
- Flag contradictory instructions (e.g. writable paths differ between `BOUNDARIES.md` and `SESSIONS.md`)
- Flag session lifecycle steps that disagree across `AGENTS.md`, `SESSIONS.md`, skills

## Duplication (documentation only)

- Same install/bootstrap steps in README, AGENTS.md, SESSIONS.md without canonical link
- Terminology drift for hub concepts (codename, worktree, binding)
- Code duplication or dead modules → structure agent, not docs agent
- SUGGESTION: overlapping "start work" / "end session" instructions — prefer single canonical source + links

## Coherence

- REQUIRED: bootstrap → bind → worktree → implement → sync → end reads as one story
- REQUIRED: `BOUNDARIES.md` / guard behavior described in docs matches `guard_path_decision` logic
- Flag persistence docs (`checkpoints`, `reviews/`) missing when skill references them
- Flag code examples in docs that cannot run or are not marked illustrative

## Staleness (product repos, changeset mode)

When a changeset implements a feature, task, or milestone, verify project tracking docs reflect it:

- REQUIRED: milestone/task status tables in `CURRENT.md` (or equivalent) must be updated — pending → done/in-progress
- REQUIRED: dependency diagrams or task lists in plan docs (`docs/*.md`) must mark completed tasks
- SUGGESTION: `CHANGELOG.md` should have an entry for features that ship in this PR
- Check: does the text in tracking docs reference the correct session/branch/PR (not a stale prior session name)?
- Flag any mismatch between what the code delivers and what tracking docs say is pending/done

These are REQUIRED when a tracking doc file is present in the repo and the changeset implements a trackable deliverable.

## Hub template (full scope)

Always include in corpus: `AGENTS.md`, `SESSIONS.md`, `CONTRIBUTING.md`, `docs/REPOS.md`, `docs/PROJECT.md.example`, `.cursor/rules/agent-guidelines.mdc`, `.cursor/rules/hub-contributing.mdc`, `.cursor/skills/**/SKILL.md`, `sessions/_template/BOUNDARIES.md`.

## Severity

- Wrong command/path/guard → **REQUIRED**
- Duplication / terminology / polish → **SUGGESTION** or **NIT**
- Do not emit **BLOCKER** from docs agent (code/security agents own BLOCKER)
