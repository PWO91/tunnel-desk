#!/bin/bash
# Build TunnelDesk z PyInstaller z ikoną

# Nazwa pliku wynikowego
APP_NAME="TunnelDesk"
PY_FILE="main.py"
DATA_FILE="connections.json"
ICON_FILE="icon.ico"

# Usuń stare buildy
rm -rf dist build __pycache__ "$APP_NAME.spec"

# Uruchom PyInstaller
pyinstaller \
    --windowed \
    --onefile \
    --add-data "$DATA_FILE:." \
    --icon "$ICON_FILE" \
    --name "$APP_NAME" \
    "$PY_FILE"

echo "Build complete! Output binary is located at dist/$APP_NAME"