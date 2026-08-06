#!/usr/bin/env bash
#
# Configure OpenCode to use the skills in this repository.
#
# Generates ~/.config/opencode/opencode.jsonc from opencode-skills.json and
# installs the launcher that disables competing skill discovery. Safe to re-run:
# an existing configuration is backed up first.
#
# Usage:
#   ./bootstrap.sh              install
#   ./bootstrap.sh --verify     report drift without changing anything
#   ./bootstrap.sh --dry-run    print the configuration that would be written

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GENERATOR="$REPO_ROOT/tools/generate_opencode_config.py"
CONFIG_PATH="${XDG_CONFIG_HOME:-$HOME/.config}/opencode/opencode.jsonc"
LAUNCHER_DIR="$HOME/.local/bin"
LAUNCHER_PATH="$LAUNCHER_DIR/opencode"

MODE=install
case "${1-}" in
  --verify)  MODE=verify ;;
  --dry-run) MODE=dry-run ;;
  --help|-h) sed -n '3,13p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
  "")        ;;
  *)         echo "unknown option: $1 (try --help)" >&2; exit 2 ;;
esac

command -v python3 >/dev/null 2>&1 || { echo "error: python3 is required" >&2; exit 1; }
[ -f "$GENERATOR" ] || { echo "error: missing $GENERATOR" >&2; exit 1; }

if [ "$MODE" = verify ]; then
  python3 "$GENERATOR" --verify "$CONFIG_PATH"
  exit $?
fi

if [ "$MODE" = dry-run ]; then
  python3 "$GENERATOR"
  exit $?
fi

# 1. Configuration, derived from opencode-skills.json.
python3 "$GENERATOR" --write "$CONFIG_PATH"

# 2. Launcher. Both flags are required: a name allowlist cannot distinguish two
#    same-named skills arriving from different sources, so discovery is disabled
#    and the manifest paths are the only source.
#
#    Finding the real binary matters once a launcher is already installed: it
#    shadows the vendor binary on PATH, so `command -v opencode` returns the
#    launcher itself.
find_vendor_binary() {
  if [ -x "$HOME/.opencode/bin/opencode" ]; then
    printf '%s' "$HOME/.opencode/bin/opencode"
    return
  fi
  if [ -f "$LAUNCHER_PATH" ]; then
    local previous
    previous="$(sed -n 's/^exec "\(.*\)" "\$@"$/\1/p' "$LAUNCHER_PATH" | head -1)"
    if [ -n "$previous" ] && [ -x "$previous" ]; then
      printf '%s' "$previous"
      return
    fi
  fi
  local directory
  local IFS=:
  for directory in $PATH; do
    [ -n "$directory" ] || continue
    [ "$directory" = "$LAUNCHER_DIR" ] && continue
    if [ -x "$directory/opencode" ]; then
      printf '%s' "$directory/opencode"
      return
    fi
  done
}

VENDOR_BINARY="$(find_vendor_binary)"

if [ -z "$VENDOR_BINARY" ]; then
  echo
  echo "warning: no OpenCode binary found; install it first:"
  echo "    curl -fsSL https://opencode.ai/install | bash"
  echo "then re-run this script to install the launcher."
  exit 0
fi

mkdir -p "$LAUNCHER_DIR"
cat > "$LAUNCHER_PATH" <<LAUNCHER
#!/usr/bin/env bash
export OPENCODE_DISABLE_CLAUDE_CODE_SKILLS=1
export OPENCODE_DISABLE_EXTERNAL_SKILLS=1
exec "$VENDOR_BINARY" "\$@"
LAUNCHER
chmod +x "$LAUNCHER_PATH"
echo "wrote $LAUNCHER_PATH -> $VENDOR_BINARY"

# 3. The launcher only helps if it wins on PATH.
RESOLVED="$(command -v opencode 2>/dev/null || true)"
if [ "$RESOLVED" != "$LAUNCHER_PATH" ]; then
  echo
  echo "warning: 'opencode' resolves to ${RESOLVED:-nothing}, not the launcher."
  echo "         Put $LAUNCHER_DIR ahead of the vendor directory on PATH:"
  echo "             export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

# 4. Confirm OpenCode resolves exactly the manifest skills.
echo
if command -v opencode >/dev/null 2>&1; then
  RESOLVED_JSON="$(mktemp)"
  trap 'rm -f "$RESOLVED_JSON"' EXIT
  if opencode debug skill > "$RESOLVED_JSON" 2>/dev/null; then
    python3 "$GENERATOR" --check-resolved "$RESOLVED_JSON" --repository "$REPO_ROOT" || true
  else
    echo "note: could not run 'opencode debug skill'; skipping verification"
  fi
fi

echo
echo "Done. Restart any running OpenCode session to load the new configuration."
