# 1.0.0-rc.1 release record

**First stable candidate** — hub template release completing the kerrigan rc track (seven PRs, June 2026).

Installed version: `.hub-version` → `1.0.0-rc.1`  
Git tag (after PR-7 merge): `v1.0.0-rc.1`

## PR track

| PR | Scope | Session |
|----|-------|---------|
| [#19](https://github.com/lgarciaaco/agentic-multisession-template/pull/19) | Skills audit + workflow subagent isolation | kerrigan |
| [#20](https://github.com/lgarciaaco/agentic-multisession-template/pull/20) | Codebase audit + doc consolidation | raynor |
| [#21](https://github.com/lgarciaaco/agentic-multisession-template/pull/21) | Version bump + CHANGELOG rc.1 | kerrigan |
| [#22](https://github.com/lgarciaaco/agentic-multisession-template/pull/22) | Release positioning (stable candidate) | tychus |
| [#23](https://github.com/lgarciaaco/agentic-multisession-template/pull/23) | RC smoke checklist | nova |
| [#24](https://github.com/lgarciaaco/agentic-multisession-template/pull/24) | Final polish + tag prep | artanis |

## Success criteria evidence

| ID | Criterion | Evidence |
|----|-----------|----------|
| SC-1 | Tag + CHANGELOG rc.1 as first stable candidate | `.hub-version` `1.0.0-rc.1`; CHANGELOG `[1.0.0-rc.1]`; tag `v1.0.0-rc.1` on rc tip |
| SC-2 | Seven PRs merged in order | Table above; workflow delivery reports per session |
| SC-3 | Docs consolidated; no milestone-track jargon in shipped tree | PR #20; final grep sweep PR #24 |
| SC-4 | Six skills reviewed | PR #19 |
| SC-5 | Full codebase audit before version bump | PR #20 |
| SC-6 | Pre-PR suite + smoke on rc tip | [RC-SMOKE-CHECKLIST.md](RC-SMOKE-CHECKLIST.md) PASS 9/9 |
| SC-7 | Workflow subagent isolation enforced | PR #19; `test_workflow_plan_reviewer_rules.py` |

## Post-rc

- Feedback on rc.1 informs **1.0.0** (final tag out of scope for rc track)
- Hub upgrades: `./scripts/hub-status.sh` · `./scripts/hub-upgrade.sh`
