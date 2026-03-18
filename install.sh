#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ZENBREAK_HOME="$HOME/.zenbreak"
PLIST_NAME="com.zenbreak.app.plist"
PLIST_SRC="$SCRIPT_DIR/$PLIST_NAME"
PLIST_DST="$HOME/Library/LaunchAgents/$PLIST_NAME"

echo "Installing ZenBreak..."

mkdir -p "$ZENBREAK_HOME"
mkdir -p "$ZENBREAK_HOME/stats"

if [ ! -f "$ZENBREAK_HOME/config.json" ]; then
    cp "$SCRIPT_DIR/config.default.json" "$ZENBREAK_HOME/config.json"
    echo "Created default config at $ZENBREAK_HOME/config.json"
fi

sed "s|ZENBREAK_DIR|$SCRIPT_DIR|g; s|ZENBREAK_HOME|$ZENBREAK_HOME|g" \
    "$PLIST_SRC" > "$PLIST_DST"

echo "Installed LaunchAgent at $PLIST_DST"

launchctl load "$PLIST_DST" 2>/dev/null || true
echo "ZenBreak will now start automatically at login."
echo "To start now: python3 -m zenbreak.app"
echo "To uninstall: launchctl unload $PLIST_DST && rm $PLIST_DST"
