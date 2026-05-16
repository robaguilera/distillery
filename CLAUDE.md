# distillery

## Workflow

> **Source of truth is always this repo.** Edit files here first — never in deployed locations like `~/.{agent}/skills/`. Those are deploy targets, not sources.

After editing, sync to deployed locations:
- `skills/distillery/` or `template.html` → `./install.sh claude` (or whichever agent)
- Gallery index regenerates automatically when the distillery-gallery skill runs

## Install commands

```bash
./install.sh claude                  # copies skills/distillery/ → ~/.claude/skills/distillery/
./scripts/install-libs.sh            # installs Python dev dependencies into local .venv (requires uv)
```

## Repo layout

```
distillery/
  CLAUDE.md
  install.sh               ← installs skill to a local agent
  requirements.txt
  scripts/
    dev.sh                 ← renders template with sample content, serves locally
    test.sh                ← runs integration tests (--full for slow/LLM tests)
    install-libs.sh        ← installs dev dependencies into local .venv
    yt_template_dev.py     ← dev server helper (called by dev.sh)
  skills/
    distillery/
      SKILL.md             ← skill prompt (source of truth)
      template.html        ← HTML report template (source of truth)
    distillery-gallery/
      SKILL.md             ← gallery skill prompt (source of truth)
      index.html           ← gallery viewer (source of truth)
      scripts/
        backfill_meta.py   ← backfills meta blocks into old reports (auto-called by build_index.py)
        build_index.py     ← builds manifest.json and copies index.html
```

## Dev

```bash
./scripts/dev.sh           # renders template → sample_output.html, serves at http://localhost:8765/
./scripts/test.sh          # fast tests (no LLM)
./scripts/test.sh --full   # all tests including real Claude API calls
```
