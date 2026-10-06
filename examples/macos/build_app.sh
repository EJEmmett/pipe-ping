#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

uv run --project ../.. --with pyinstaller pyinstaller \
    --windowed \
    --noconfirm \
    --name Pipe-Ping \
    --osx-bundle-identifier io.github.ejemmett.pipe-ping \
    --copy-metadata pipe-ping \
    --collect-submodules pipe_ping \
    --collect-data pipe_ping \
    --collect-data desktop_notifier \
    launcher.py

plutil -insert LSUIElement -bool YES dist/Pipe-Ping.app/Contents/Info.plist
codesign --force --deep --sign - dist/Pipe-Ping.app

echo "Built dist/Pipe-Ping.app"
