# Performance rules (deep pass)

Optional performance agent. Code agents apply light perf checks from [universal.md](universal.md).

## Data access

- REQUIRED: N+1 query or per-item fetch in loops
- REQUIRED: unbounded list/query without pagination on user-facing paths

## Concurrency

- REQUIRED: sync blocking I/O on concurrent request handlers
- REQUIRED: CPU-bound work on async event loop without offload

## Hot paths

- SUGGESTION: repeated parse/serialize of large objects in loops
- SUGGESTION: string concat in tight loops; chained array passes over same data

## Scope

- Only flag issues in files assigned by manifest
- Do not recommend micro-optimizations that harm readability without measured need
