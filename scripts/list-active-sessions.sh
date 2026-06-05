#!/usr/bin/env bash
# List open sessions (table, json, or agent prompt text).
set -euo pipefail
# shellcheck source=lib/hub-cli.sh
source "$(cd "$(dirname "$0")" && pwd)/lib/hub-cli.sh"

FORMAT="${1:-table}"
case "$FORMAT" in
  json) hub_cli list --format json ;;
  prompt) hub_cli list --format prompt ;;
  table | *) hub_cli list --format table ;;
esac
