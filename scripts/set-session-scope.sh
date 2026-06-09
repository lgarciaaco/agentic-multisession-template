#!/usr/bin/env bash
# Set session title, next hint, and/or TASKS.md goal from session.json canonical metadata.
# Usage: ./scripts/set-session-scope.sh [codename] --title "..." [--goal "..."] [--next "..."]
set -euo pipefail
# shellcheck source=lib/hub-cli.sh
source "$(cd "$(dirname "$0")" && pwd)/lib/hub-cli.sh"
hub_cli scope "$@"
