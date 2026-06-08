# Performance reviewer procedure (optional)

1. Spawn only when `scope_manifest.triggers.performance` is true
2. Review manifest code files on hot paths (api, db, workers, handlers)
3. Load [performance.md](../performance.md)
4. REQUIRED for N+1, unbounded fetch, blocking on concurrent paths
5. Write `findings/performance.json`
