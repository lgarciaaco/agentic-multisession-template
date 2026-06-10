# Problem analyst rules

**Runner:** parent agent (conductor) in `intake` and `brief_review` phases.  
**Output:** `sessions/<codename>/artifacts/problem-brief.md`  
**Rationale:** [references/research-rationale.md](../references/research-rationale.md)

## Purpose

Structured interviewer — not copywriter, not planner. Capture **what** and **why** in durable form before any plan or code.

## Elicitation procedure

1. Read user message and session context (`session.json`, `TASKS.md` goal if set).
2. Ask targeted questions until every section can be drafted — one question cluster at a time, not a numbered interrogation list.
3. Track unresolved items in **Open questions**; do not present brief for acceptance until empty.
4. Draft brief to template below; validate against checklist.
5. Load `write-like-a-human` skill — final tone pass on brief body only.
6. Present brief (≤1 screen); wait for user `accept brief` or corrections.
7. On accept: set `Status: accepted`, date, clear open questions; conductor sets `gates.brief_accepted: true`.

## Template (required sections)

```markdown
# Problem brief — <title>

**Status:** draft | accepted
**Accepted:** —

## Problem
One paragraph: what is broken, missing, or needed.

## Context
Why now; what triggered this; relevant system area.

## Constraints
Must-haves, must-nots, repos involved, time/scope appetite, compatibility.

## Success criteria
- SC-1: …
- SC-2: …
(3–5 items; observable and testable)

## Out of scope
Explicit non-goals.

## Open questions
Bullets; must be empty before acceptance gate.
```

## Format rules

| Rule | Requirement |
|------|-------------|
| Length | ≤40 lines total excluding title |
| Success criteria | 3–5 items; IDs `SC-1` … `SC-n`; no vague verbs alone ("improve", "better") |
| Constraints | Include scope/time appetite as a constraint, not a solution |
| Jargon | Define or replace; no unresolved acronyms |
| Status | `draft` until user accepts |

## Testability (each SC-n)

Each criterion must be verifiable without reading code:

- **Good:** "Authenticated user sees an error message when payment token is expired"
- **Bad:** "Feature works well"
- **Bad:** "Improve the user experience"

## Forbidden content

- Implementation approach, architecture, file paths, module names
- Task breakdown or repo-specific edit lists (planner's job)
- Market research, competitive analysis, KPI tables
- Persona framing ("I am Mary the analyst…")
- Rewriting user goals beyond clarification

## Gate

- **Exit:** user says `accept brief` / `accept` (when phase is `brief_review`)
- **Iterate:** user corrections → update brief, keep `Status: draft`
- **Freeze:** after accept — changes only via `reopen brief` (conductor command)

## Tone

Structure and testability first. Apply `write-like-a-human` only on the final draft before presentation — never skip the structural checklist for tone.
