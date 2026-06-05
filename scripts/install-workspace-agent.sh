#!/usr/bin/env bash
# Install a per-project agent launcher on PATH (~/.local/bin).
# Each hub gets its own command (e.g. my-app → my-agent) and config dir.
set -euo pipefail

HUB="$(cd "$(dirname "$0")/.." && pwd)"
SLUG="${WORKSPACE_HUB_SLUG:-$(basename "$HUB")}"
BIN_DIR="${WORKSPACE_BIN_DIR:-$HOME/.local/bin}"

if [[ -n "${WORKSPACE_AGENT_LAUNCHER:-}" ]]; then
  LAUNCHER="$WORKSPACE_AGENT_LAUNCHER"
elif [[ "$SLUG" == *-agent ]]; then
  LAUNCHER="$SLUG"
else
  LAUNCHER="${SLUG%%-*}-agent"
fi

CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/${SLUG}"
WRAPPER="$BIN_DIR/${LAUNCHER}"

mkdir -p "$CONFIG_DIR" "$BIN_DIR"
printf '%s\n' "$HUB" > "$CONFIG_DIR/hub"
printf '%s\n' "$LAUNCHER" > "$HUB/.hub-launcher"
printf '%s\n' "$SLUG" > "$HUB/.hub-slug"

cat > "$WRAPPER" <<EOF
#!/usr/bin/env bash
# Hub agent launcher — $LAUNCHER (hub: $SLUG)
# Installed by $HUB/scripts/install-workspace-agent.sh
set -euo pipefail

hub="\${WORKSPACE_ROOT:-}"
config="\${XDG_CONFIG_HOME:-\$HOME/.config}/${SLUG}/hub"
if [[ -z "\$hub" && -f "\$config" ]]; then
  hub="\$(< "\$config")"
fi
if [[ -z "\$hub" || ! -d "\$hub" ]]; then
  echo "Error: hub '$SLUG' not found. Set WORKSPACE_ROOT or re-run:" >&2
  echo "  $HUB/scripts/install-workspace-agent.sh" >&2
  exit 1
fi
export WORKSPACE_ROOT="\$hub"

exec "\$hub/scripts/workspace-agent.sh" "\$@"
EOF

chmod +x "$WRAPPER"
chmod +x "$HUB"/scripts/*.sh

echo "Installed: $WRAPPER"
echo "Command:   $LAUNCHER"
echo "Hub:       $HUB"
echo "Config:    $CONFIG_DIR/hub"
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
  echo ""
  echo "Add to PATH (e.g. in ~/.bashrc):"
  echo "  export PATH=\"$BIN_DIR:\$PATH\""
fi
echo ""
echo "Usage from anywhere: $LAUNCHER"
