#!/usr/bin/env bash
# Install Python dev dependencies into local .venv (needed for running tests).
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
uv venv --quiet
uv pip install -r "$REPO/requirements-dev.txt" --quiet
echo "Dev dependencies installed into .venv"
