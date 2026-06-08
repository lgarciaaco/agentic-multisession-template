---
name: session-end
description: Close workspace session for this chat.
---

# Session end

Triggers: `end session`, `/end-session`

The before-prompt hook does **not** close sessions — only this flow does.

1. Resolve codename (`resolve-session.sh` or user); `[codename]` is optional when this chat is already bound
2. `./scripts/end-session.sh [codename] [note]`
