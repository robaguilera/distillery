#!/usr/bin/env bash
# Render the HTML template with sample content and serve it locally.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
uv run python3 "$REPO/scripts/yt_template_dev.py"
bash "$REPO/skills/distillery/scripts/serve_report.sh" \
  ~/Downloads/distillery/reports/distillery_sample_output.html
