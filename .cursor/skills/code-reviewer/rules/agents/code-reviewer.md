# Code reviewer procedure

1. Read `scope_manifest.json`; review only assigned language files (`kind: code`)
2. Load rules: [universal.md](../universal.md) + [languages/<lang>.md](../../languages/<lang>.md)
3. `changeset`/`task`: focus changed hunks + imports, callers, paired tests
4. `full`: prioritize per scope-and-delta; light security/design sweep
5. Defer style nits to CI when linter configured
6. Do not duplicate test-agent, security-agent, or structure-agent deep passes — light flags only
7. Write [findings-schema.md](../../references/findings-schema.md) JSON to `findings/code-<lang>.json`
