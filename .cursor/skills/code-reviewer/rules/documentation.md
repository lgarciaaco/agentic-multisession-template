# Documentation rules

Corpus review: consistency, duplication, coherence. Doc findings default to **REQUIRED** (not BLOCKER) unless synthesizer maps explicit security lies separately.

## Accuracy

- REQUIRED: documented commands/scripts must exist and match current CLI behavior
- REQUIRED: paths (`sessions/`, `worktrees/`, `repos/`) must match repo layout and hooks
- REQUIRED: `AGENTS.md` skills table must match `.cursor/skills/*/SKILL.md` entries
- Flag broken internal links and references to removed files

## Consistency

- REQUIRED: same term for same concept across docs (`codename`, not mixed with "session name")
- Flag contradictory instructions (e.g. writable paths differ between `BOUNDARIES.md` and `SESSIONS.md`)
- Flag session lifecycle steps that disagree across `AGENTS.md`, `SESSIONS.md`, skills

## Duplication

- SUGGESTION: same setup/bootstrap steps repeated in multiple docs with conflicting detail
- SUGGESTION: overlapping "start work" / "end session" instructions — prefer single canonical source + links

## Coherence

- REQUIRED: bootstrap → bind → worktree → implement → sync → end reads as one story
- REQUIRED: `BOUNDARIES.md` / guard behavior described in docs matches `guard_path_decision` logic
- Flag persistence docs (`checkpoints`, `reviews/`) missing when skill references them
- Flag code examples in docs that cannot run or are not marked illustrative

## Hub template (full scope)

Always include in corpus: `AGENTS.md`, `SESSIONS.md`, `CONTRIBUTING.md`, `docs/REPOS.md`, `.cursor/skills/**/SKILL.md`, `sessions/_template/BOUNDARIES.md`.

## Severity

- Wrong command/path/guard → **REQUIRED**
- Duplication / terminology / polish → **SUGGESTION** or **NIT**
- Do not emit **BLOCKER** from docs agent (code/security agents own BLOCKER)
