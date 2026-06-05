#!/usr/bin/env bash
# Sync sessions/index.json and chat context from sessions/<codename>/session.json.
set -euo pipefail
# shellcheck source=lib/hub-cli.sh
source "$(cd "$(dirname "$0")" && pwd)/lib/hub-cli.sh"
hub_cli sync "$@"
