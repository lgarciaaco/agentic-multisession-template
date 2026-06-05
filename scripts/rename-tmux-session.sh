#!/usr/bin/env bash
# Rename tmux window to session codename.
set -euo pipefail
# shellcheck source=lib/hub-cli.sh
source "$(cd "$(dirname "$0")" && pwd)/lib/hub-cli.sh"
hub_cli rename "$@"
