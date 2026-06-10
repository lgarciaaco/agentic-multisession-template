---
name: skill-optimizer
description: >-
  Streamline hub skills: remove bloat, agent-unfriendly language, duplication, and
  decorative formatting while preserving behavior. Load when creating, reviewing, or
  improving any skill under .cursor/skills/.
---

# Skill optimizer

Print: `Using skill-optimizer for skill streamlining`

## Analyze

Flag: emojis in specs (except activation line), "tell/show/present user", duplicated error/pattern sections, verbose commentary, redundant examples.

## Remove

Emojis in output specs; user-facing narration; duplicate error blocks; example-heavy prose; agent-inappropriate "human-friendly" filler.

## Preserve

All commands, paths, gates, API/script calls, essential error handling, activation print line.

## Convert

User-interaction steps → direct agent commands. Explanations → concise specs. Examples → format definitions where needed.

## Validate

Same behavior; 40–60% shorter when possible; agent command structure; essential errors retained.

For tone-heavy artifacts (delivery reports, PR text), run [write-like-a-human](../write-like-a-human/SKILL.md) after structural edits.

## Report (optional)

Analysis count, line reduction, core operations preserved.
