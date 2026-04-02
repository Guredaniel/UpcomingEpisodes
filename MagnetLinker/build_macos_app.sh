#!/usr/bin/env bash
set -euo pipefail

# Activate virtualenv if present
if [ -f .venv/bin/activate ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

# Use venv Python only; fail loudly if missing
if [ -x .venv/bin/python ]; then
  PYTHON=.venv/bin/python
else
  echo "Error: .venv/bin/python not found. Please create/activate the virtualenv." >&2
  exit 1
fi

echo "Installing macOS requirements..."
if [ -f requirements-macos.txt ]; then
  "$PYTHON" -m pip install -r requirements-macos.txt
else
  "$PYTHON" -m pip install pyinstaller
fi

# Build using existing PyInstaller spec if present
if [ -f MagnetLinker.spec ]; then
  echo "Using MagnetLinker.spec to build app..."
  "$PYTHON" -m PyInstaller --noconfirm MagnetLinker.spec
else
  echo "Spec not found; building from MagnetApp.py..."
  "$PYTHON" -m PyInstaller --noconfirm --windowed --name MagnetLinker --icon=icon.icns --add-data "icon.png:." MagnetApp.py
fi

echo "Build finished. .app should be in the 'dist' directory."