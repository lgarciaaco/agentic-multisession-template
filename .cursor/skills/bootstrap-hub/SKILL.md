---
name: bootstrap-hub
description: Bootstrap a new project hub copied from agentic-multisession-template. Install deps, launcher, update docs, run tests.
---

# Bootstrap hub

Triggers: `bootstrap hub`, `set up template`, `customize template`, `new project from template`

1. Read [CUSTOMIZE.md](../../CUSTOMIZE.md) at hub root
2. Stay in this hub only — do not read other local repos unless the user explicitly points you there
3. Run **mandatory** steps only unless the user asked for optional items
4. Update `README.md` and `AGENTS.md` with project name; remove or shorten the template-bootstrap block in `AGENTS.md` when done
5. `python3 scripts/test_session_binding.py` — all pass
6. Tell user the installed launcher: `cat .hub-launcher` for tmux; `/start-work` for Cursor chat

Do not add domain logic unless the user specifies the project purpose.
