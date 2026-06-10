---
name: write-like-a-human
description: >-
  Final tone pass on human-facing text (briefs, delivery reports, GitHub comments).
  Load when workflow artifacts or PR text are shown to a person. Not for code or paths.
---

# Write like a human

Print: `Using write-like-a-human skill`

## Workflow

1. Context: reader, channel, language, thread vs new, desired outcome after read.
2. Voice: match thread tone; default direct, warm, one clear ask.
3. Draft: purpose in first 1–2 sentences; main ask early.
4. Anti-AI pass: full rules in [reference.md](./reference.md) (structure, vocabulary, contrastive negation, burstiness, hard bans).
5. Channel pass: table below.
6. Deliver paste-ready text only (meta after `---` if needed).

Tone rules live in **reference.md** — do not duplicate ban lists here.

## Channel defaults

| Channel | Shape |
|---------|--------|
| GitHub comment | 2–5 sentences; impact first; `file:line`; one fix |
| PR review report | 1–2 sentence take; findings as prose; one next step |
| Slack/chat | 1–3 short blocks |
| Email (EN) | 2–4 paragraphs; specific subject |

## Anti-AI pass (checklist)

Cut ~20%; vary sentence length; one concrete detail; read aloud; scan negation and em-dash glue.

## Hub integration

| Artifact | When |
|----------|------|
| `artifacts/problem-brief.md` | problem-analyst final pass before `brief_review` gate |
| `artifacts/delivery-report.md` | optional before user inform gate |
| GitHub PR body/comments | before `gh pr create` or review post |

## Reference

[reference.md](./reference.md) · structural skill edits: [skill-optimizer](../skill-optimizer/SKILL.md)
