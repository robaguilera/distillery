---
name: distillery-gallery
description: >
  Open or rebuild the distillery gallery index — your personal library of saved video summaries.
  Use this whenever the user wants to browse, open, or search saved video reports:
  "show my gallery", "open video library", "browse saved videos", "build gallery",
  "what videos have I saved", "show my video notes", "my video summaries",
  "find my saved summary for [topic]", "rebuild the index", "show distillery index",
  "backfill metadata", "update index".
license: MIT
allowed-tools: Bash
---

# distillery-gallery

Manage and browse your saved distillery reports.

## Step 1 — Locate skill scripts

```bash
source ~/.distillery/claude.env 2>/dev/null || { echo "Distillery not installed — run: ./install.sh claude"; exit 1; }
```

## Step 2 — Rebuild index

Check that the reports directory exists before running:

```bash
[ -d ~/Downloads/distillery ] || { echo "No reports directory found — save some videos first with the distillery skill."; exit 1; }
_py="$(dirname "$SKILL_DIR")/.venv/bin/python3"; [ ! -f "$_py" ] && _py=python3; "$_py" "$SKILL_DIR/knowledge_base.py" rebuild --dir ~/Downloads/distillery
```

Tell the user the number of reports indexed, from the script's output.

## Step 3 — Serve gallery

```bash
bash "$SKILL_DIR/serve_report.sh" ~/Downloads/distillery/index.html ~/Downloads/distillery
```

Tell the user the gallery is now available at `http://localhost:8765/index.html`.
