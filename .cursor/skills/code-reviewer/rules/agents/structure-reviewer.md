# Structure reviewer procedure

1. Spawn when `scope_manifest.triggers.structure` is true (any code file in manifest)
2. Read `scope_manifest.json` — delta files, `target` worktree root, optional `workflow.codename`
3. Load [structure.md](../structure.md)
4. Read layout source: hub `docs/PROJECT.md` if exists; else `docs/PROJECT.md.example` **Layout** for hub repos; else infer from repo root (README, existing folders)
5. **Duplication:** compare new/changed code files to rest of repo; search for existing implementations before REQUIRED on redundancy
6. **Layout:** validate paths against PROJECT layout or repo conventions
7. **Dead code:** on deletions or refactors in delta, trace references (imports, docs, tests, skills, scripts)
8. Defer doc-only duplication to docs agent; defer line-level bugs to code agents
9. Write `findings/structure.json` per [findings-schema.md](../../references/findings-schema.md) — agent id `structure`
10. Return: file path + counts by severity
