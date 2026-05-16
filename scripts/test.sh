#!/usr/bin/env bash
# Run integration tests. Pass --full to include slow tests (real Claude API calls).
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
if [ "${1:-}" = "--full" ]; then
  uv run pytest "$REPO/tests/test_e2e.py" -v
else
  uv run pytest "$REPO/tests/test_e2e.py" -v -m "not slow"
fi
