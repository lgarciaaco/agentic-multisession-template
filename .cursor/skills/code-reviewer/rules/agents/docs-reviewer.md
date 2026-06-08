# Docs reviewer procedure

1. Read `scope_manifest.json` — use `doc_corpus` as full set (not delta-only)
2. Load [documentation.md](../documentation.md) + [languages/docs-<lang>.md](../../languages/) when lang in manifest
3. Cross-check docs against code/scripts/hooks for accuracy
4. Evaluate consistency, duplication, coherence across corpus
5. Default severity REQUIRED for wrong paths/commands/drift; SUGGESTION for duplication
6. Never emit BLOCKER
7. Write `findings/docs.json`
