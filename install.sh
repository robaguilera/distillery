#!/usr/bin/env bash
# install.sh — install distillery for a supported coding agent
# Usage: ./install.sh AGENT
#   AGENT: claude | gemini | opencode | cursor | agents | windsurf | copilot | codex

set -euo pipefail

AGENT="${1:-}"

case "$AGENT" in
  agents)   DIR="$HOME/.agents/skills" ;;
  claude)   DIR="$HOME/.claude/skills" ;;
  gemini)   DIR="$HOME/.gemini/skills" ;;
  opencode) DIR="$HOME/.opencode/skills" ;;
  cursor)   DIR="$HOME/.cursor/skills" ;;
  windsurf) DIR="$HOME/.windsurf/skills" ;;
  copilot)  DIR="$HOME/.copilot/skills" ;;
  codex)    DIR="$HOME/.codex/skills" ;;
  "")
    echo "Usage: ./install.sh AGENT"
    echo "  AGENT: claude | gemini | opencode | cursor | agents | windsurf | copilot | codex"
    exit 1
    ;;
  *)
    echo "Error: unknown agent '$AGENT'. Valid: claude, gemini, opencode, cursor, agents, windsurf, copilot, codex"
    exit 1
    ;;
esac

# Require Python 3.10+ (yt-dlp constraint)
PY=$(command -v python3 || true)
if [ -z "$PY" ]; then
  echo "Error: python3 not found. Install Python 3.10 or later."
  exit 1
fi
PY_OK=$("$PY" -c "import sys; print(sys.version_info >= (3,10))")
if [ "$PY_OK" != "True" ]; then
  echo "Error: Python 3.10+ required (found $("$PY" --version))."
  exit 1
fi

SHARED_DIR="$HOME/.distillery"
SKILL_DIR="$DIR/distillery"
GALLERY_DIR="$DIR/distillery-gallery"

# ── Shared scripts + venv ──────────────────────────────────────────────────
echo "Installing shared scripts → $SHARED_DIR/scripts/"
# Clean then copy both dirs — don't use --delete on the second rsync or it
# wipes everything the first one wrote.
rm -rf "$SHARED_DIR/scripts"
mkdir -p "$SHARED_DIR/scripts"
rsync -a --exclude='__pycache__' skills/distillery/scripts/ "$SHARED_DIR/scripts/"
rsync -a --exclude='__pycache__' skills/distillery-gallery/scripts/ "$SHARED_DIR/scripts/"

# Templates live one level above scripts/ so render scripts can find them
cp skills/distillery/template.html "$SHARED_DIR/template.html"
cp skills/distillery/template_batch.html "$SHARED_DIR/template_batch.html"
for tmpl in skills/distillery/template_*.html; do
  [ -f "$tmpl" ] && cp "$tmpl" "$SHARED_DIR/$(basename "$tmpl")"
done
# Shared CSS and JS (injected at render time into every single-video template)
cp skills/distillery/shared.css "$SHARED_DIR/shared.css"
cp skills/distillery/shared_app.js "$SHARED_DIR/shared_app.js"
# Gallery viewer lives one level above scripts/ so knowledge_base.py can find it
cp skills/distillery-gallery/index.html "$SHARED_DIR/index.html"
echo "  copied scripts and templates"

echo "Creating Python venv → $SHARED_DIR/.venv/"
python3 -m venv "$SHARED_DIR/.venv"
"$SHARED_DIR/.venv/bin/pip" install --quiet -r requirements.txt
echo "  installed: $(grep -v '^#' requirements.txt | tr '\n' ' ')"

# Write agent env file (idempotent — each agent gets its own, others are untouched)
cat > "$SHARED_DIR/$AGENT.env" << ENVEOF
export SKILL_DIR="$SHARED_DIR/scripts"
ENVEOF
echo "  wrote $SHARED_DIR/$AGENT.env"

# ── Agent skill directories (SKILL.md + gallery index only) ───────────────
echo "Installing distillery skill → $SKILL_DIR"
mkdir -p "$SKILL_DIR"
# Substitute the agent name so each SKILL.md sources its own .env file
sed "s/claude\.env/$AGENT.env/g" skills/distillery/SKILL.md > "$SKILL_DIR/SKILL.md"
echo "  copied SKILL.md (agent: $AGENT)"

echo "Installing distillery-gallery → $GALLERY_DIR"
mkdir -p "$GALLERY_DIR"
cp skills/distillery-gallery/index.html "$GALLERY_DIR/index.html"
sed "s/claude\.env/$AGENT.env/g" skills/distillery-gallery/SKILL.md > "$GALLERY_DIR/SKILL.md"
echo "  copied gallery SKILL.md and index.html"

echo ""
echo "Done. Open your agent and run: /distillery <youtube-url>"
