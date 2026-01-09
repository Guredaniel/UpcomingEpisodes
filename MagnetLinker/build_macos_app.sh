#!/usr/bin/env bash
set -euo pipefail

# Activate virtualenv if present
if [ -f .venv/bin/activate ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

echo "Installing macOS requirements..."
if [ -f requirements-macos.txt ]; then
  pip install -r requirements-macos.txt
else
  pip install pyinstaller
fi

# Build using existing PyInstaller spec if present
if [ -f MagnetLinker.spec ]; then
  echo "Using MagnetLinker.spec to build app..."
  pyinstaller --noconfirm MagnetLinker.spec
else
  echo "Spec not found; building from MagnetApp.py..."
  pyinstaller --noconfirm --windowed --name MagnetLinker MagnetApp.py
fi

echo "Build finished. .app should be in the 'dist' directory."