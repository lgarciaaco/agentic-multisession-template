#!/usr/bin/env bash
# Refresh hub scripts/hooks/docs from the upstream template in place.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export WORKSPACE_ROOT="$ROOT"

DRY_RUN=0
YES=0
TARGET=""
ALLOW_UNTRUSTED=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1 ;;
    --yes|-y) YES=1 ;;
    --allow-untrusted-upstream) ALLOW_UNTRUSTED=1 ;;
    --to)
      TARGET="${2:-}"
      if [[ -z "$TARGET" ]]; then
        echo "Error: --to requires a version (e.g. 0.4.0)" >&2
        exit 1
      fi
      shift
      ;;
    -h|--help)
      cat <<'EOF'
Usage: ./scripts/hub-upgrade.sh [--dry-run] [--yes] [--to VERSION] [--allow-untrusted-upstream]

Updates hub-managed paths (scripts/, .cursor/, docs/, template examples) from the
upstream agentic-multisession-template. Does not touch repos/, repos.yaml, or
sessions/<codename>/ history.

Environment:
  WORKSPACE_TEMPLATE_UPSTREAM       Override template git URL (https only)
  WORKSPACE_TEMPLATE_REF            Upstream ref for latest check (default: main)
  WORKSPACE_ALLOW_UNTRUSTED_UPSTREAM  Set to 1 with --allow-untrusted-upstream
EOF
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
  esac
  shift
done

if [[ "$DRY_RUN" -eq 0 && "$YES" -eq 0 && -t 0 ]]; then
  echo "This updates hub scripts/hooks/docs in place. Product repos and session folders stay." >&2
  echo "Run with --yes to proceed, or --dry-run to preview." >&2
  exit 1
fi

if [[ "$ALLOW_UNTRUSTED" -eq 1 ]]; then
  export WORKSPACE_ALLOW_UNTRUSTED_UPSTREAM=1
fi

STATUS_JSON="$(./scripts/hub-status.sh)"
echo "$STATUS_JSON" | python3 -c "
import json, sys
data = json.load(sys.stdin)
print('Upstream:', data.get('upstream', '?'), file=sys.stderr)
print('Ref:', data.get('upstream_ref', '?'), 'SHA:', data.get('upstream_sha', '?'), file=sys.stderr)
if data.get('upstream_trusted') is False:
    print('Warning: upstream is not the default template repo.', file=sys.stderr)
if data.get('state') != 'ok':
    print('Status:', data.get('state'), '-', data.get('error', data.get('agent_action', '')), file=sys.stderr)
"

export HUB_UPGRADE_DRY_RUN="$DRY_RUN"
export HUB_UPGRADE_TARGET="$TARGET"

python3 - <<'PY'
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path("scripts/lib").resolve()))
from hub_upgrade import hub_upgrade

target = os.environ.get("HUB_UPGRADE_TARGET", "").strip() or None
result = hub_upgrade(
    target_version=target,
    dry_run=os.environ.get("HUB_UPGRADE_DRY_RUN") == "1",
)
print(json.dumps(result, indent=2))
sys.exit(0 if result.get("ok") else 1)
PY
