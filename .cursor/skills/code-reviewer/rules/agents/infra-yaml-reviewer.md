# Infra YAML reviewer procedure (optional)

1. Spawn only when `scope_manifest.triggers.infra` is true
2. Review manifest infra paths: `deploy/**`, `.github/workflows/**`, `**/ansible/**`, related shell scripts in delta
3. Load [infra-yaml.md](../infra-yaml.md)
4. Systematic pass: Ansible idempotency, GHA trigger/checkout semantics, deploy health checks, systemd/timer behavior, secret setup scripts
5. BLOCKER and REQUIRED per infra-yaml.md; cite failure scenario on re-run or concurrent deploy
6. Write `findings/infra-yaml.json` with `"agent": "infra-yaml"`
