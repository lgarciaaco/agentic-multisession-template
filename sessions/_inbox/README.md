# Session inbox

One file per target session: `<codename>.md` (e.g. `alpha.md`).

**Write (session A → session B):**

```bash
./scripts/session-inbox.sh write bravo alpha "Feature shipped — ready for review."
```

**Read:** bind session B (injected into chat context) or:

```bash
./scripts/session-inbox.sh read alpha
```

Any bound session may write here (`sessions/_inbox/` is shared). Do not put secrets in inbox files.
