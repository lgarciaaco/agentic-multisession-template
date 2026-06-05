#!/usr/bin/env bash
# Close session work and clear bindings for this chat/tab.
set -euo pipefail
# shellcheck source=lib/hub-cli.sh
source "$(cd "$(dirname "$0")" && pwd)/lib/hub-cli.sh"
_hub_cli_setup

CODENAME="${1:-}"
if [[ -n "$CODENAME" && -d "$ROOT/sessions/$CODENAME" ]]; then
  shift
fi
NOTE="${*:-}"

if [[ -z "$CODENAME" ]]; then
  CODENAME="$(hub_cli resolve 2>/dev/null || true)"
fi
if [[ -z "$CODENAME" ]]; then
  echo "Usage: $0 [codename] [note]" >&2
  exit 1
fi

hub_cli close "$CODENAME" --note "$NOTE"
