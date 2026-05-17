#!/usr/bin/env python3
"""Render a batch multi-video HTML report from template_batch.html.

Usage: echo '{"BATCH_TITLE": "...", "BATCH_VIDEOS_JSON": "...", "SYNTHESIS_JSON": "..."}' \
    | python3 render_batch_report.py OUTPUT_PATH

Keys:
    BATCH_TITLE       — page <title> and header text
    BATCH_VIDEOS_JSON — JSON array of per-video objects (already json.dumps'd)
    SYNTHESIS_JSON    — JSON object for synthesis tab, or the literal string "null"
"""
import json
import pathlib
import re
import sys

try:
    from . import render_fragments as _frag
except (ImportError, ValueError):
    import render_fragments as _frag

EXPECTED_KEYS = {"BATCH_TITLE", "BATCH_VIDEOS_JSON", "SYNTHESIS_JSON"}
AGENT_DIRS = ("agents", "claude", "copilot", "gemini", "cursor", "windsurf", "opencode", "codex")

SCRIPT_SAFE_KEYS = {"BATCH_VIDEOS_JSON", "SYNTHESIS_JSON", "BATCH_DISTILLERY_META"}


def find_template() -> pathlib.Path:
    import os
    skill_dir = os.environ.get("SKILL_DIR")
    if skill_dir:
        p = pathlib.Path(skill_dir).parent / "template_batch.html"
        if p.exists():
            return p
    home = pathlib.Path.home()
    for agent in AGENT_DIRS:
        p = home / f".{agent}" / "skills" / "distillery" / "template_batch.html"
        if p.exists():
            return p
    raise FileNotFoundError(
        "template_batch.html not found — run: ./install.sh claude (or see README)"
    )


def safe_for_script(s: str) -> str:
    """Escape </script> and <!-- so the JSON is safe inside any <script> element."""
    return s.replace("</", "<\\/").replace("<!--", "<\\!--")


def _prepare_video_data(v: dict) -> dict:
    """Ensure a video dict has the HTML fragments expected by template_batch.html."""
    if "schemaVersion" in v:
        # It's a Canonical Extraction — convert it
        video_id = v.get("videoId", "")
        return {
            "videoId": video_id,
            "title": v.get("title", ""),
            "videoUrl": f"https://www.youtube.com/watch?v={video_id}",
            "metaLine": _frag.meta_line(v),
            "summary": v.get("summary", ""),
            "takeaway": v.get("takeaway", ""),
            "keyPoints": _frag.key_points_to_html(v.get("keyPoints", [])),
            "outline": _frag.outline_to_html(v.get("outline", []), video_id),
            "descriptionSection": _frag.description_section(v.get("descriptionHtml", "")),
            "tags": v.get("tags", []),
            "keywords": v.get("keywords", []),
        }
    return v


def _prepare_synthesis_data(s: dict) -> dict:
    """Ensure synthesis dict has the HTML fragments expected by template_batch.html."""
    if s and "themes" in s and isinstance(s["themes"], list):
        s["themes"] = _frag.themes_to_html(s["themes"])
    return s


def render(data: dict, output_path: str, template_path: pathlib.Path | None = None) -> str:
    if template_path is None:
        template_path = find_template()

    # Process videos to ensure they have the HTML fragments the JS expects
    videos_raw = data.get("BATCH_VIDEOS_JSON", "[]")
    try:
        videos = json.loads(videos_raw) if isinstance(videos_raw, str) else videos_raw
        processed_videos = [_prepare_video_data(v) for v in videos]
        data["BATCH_VIDEOS_JSON"] = json.dumps(processed_videos, ensure_ascii=False)
    except Exception:
        pass

    # Process synthesis to ensure it has the HTML fragments the JS expects
    synth_raw = data.get("SYNTHESIS_JSON", "null")
    try:
        if synth_raw and synth_raw != "null":
            synth = json.loads(synth_raw) if isinstance(synth_raw, str) else synth_raw
            processed_synth = _prepare_synthesis_data(synth)
            data["SYNTHESIS_JSON"] = json.dumps(processed_synth, ensure_ascii=False)
    except Exception:
        pass

    html = template_path.read_text(encoding="utf-8")
    for key, value in data.items():
        if key in SCRIPT_SAFE_KEYS:
            value = safe_for_script(value)
        html = html.replace("{{" + key + "}}", value)

    remaining = re.findall(r"\{\{[A-Z_]+\}\}", html)
    if remaining:
        print(f"WARNING: unreplaced template placeholders: {remaining}", file=sys.stderr)

    out = pathlib.Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return str(out)


def _build_batch_meta(data: dict, output_path: str) -> str:
    """Build the gallery-compatible meta JSON for a batch report."""
    from datetime import datetime, timezone

    videos_raw = data.get("BATCH_VIDEOS_JSON", "[]")
    synthesis_raw = data.get("SYNTHESIS_JSON", "null")

    try:
        videos = json.loads(videos_raw) if isinstance(videos_raw, str) else videos_raw
    except json.JSONDecodeError:
        videos = []
    try:
        synthesis = json.loads(synthesis_raw) if isinstance(synthesis_raw, str) else synthesis_raw
    except json.JSONDecodeError:
        synthesis = None

    # Title: prefer synthesis title, fall back to BATCH_TITLE
    title = (synthesis or {}).get("title") or data.get("BATCH_TITLE", "Batch Report")

    # Summary: synthesis summary truncated to ~300 chars
    summary = (synthesis or {}).get("summary", "")
    if summary and len(summary) > 300:
        summary = summary[:297] + "…"

    # Aggregate tags and keywords from individual videos
    all_tags: list[str] = []
    all_keywords: list[str] = []
    video_stubs = []
    for v in videos:
        all_tags.extend(v.get("tags") or [])
        all_keywords.extend(v.get("keywords") or [])
        video_stubs.append({
            "videoId": v.get("videoId", ""),
            "title": v.get("title", ""),
            "channel": v.get("channel", ""),
        })

    # Deduplicate, preserving order
    seen_tags: set[str] = set()
    tags = [t for t in all_tags if t and not (seen_tags.add(t) or t in seen_tags)]  # type: ignore[func-returns-value]
    seen_kw: set[str] = set()
    keywords = [k for k in all_keywords if k and not (seen_kw.add(k) or k in seen_kw)]  # type: ignore[func-returns-value]

    filename = pathlib.Path(output_path).name
    generation_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    meta = {
        "schemaVersion": 1,
        "type": "batch",
        "title": title,
        "filename": filename,
        "generationDate": generation_date,
        "videoCount": len(videos),
        "summary": summary,
        "tags": tags[:8],
        "keywords": keywords[:20],
        "videos": video_stubs,
    }
    return json.dumps(meta, ensure_ascii=False)


def main():
    if len(sys.argv) != 2:
        print("Usage: echo '{...}' | render_batch_report.py OUTPUT_PATH", file=sys.stderr)
        sys.exit(1)

    output_path = sys.argv[1]

    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"ERROR: invalid JSON on stdin: {e}", file=sys.stderr)
        sys.exit(1)

    missing = EXPECTED_KEYS - set(data.keys())
    if missing:
        print(f"WARNING: missing keys: {sorted(missing)}", file=sys.stderr)

    # Auto-generate the gallery meta block from batch data
    data["BATCH_DISTILLERY_META"] = _build_batch_meta(data, output_path)

    try:
        result = render(data, output_path)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Rendered → {result}")


if __name__ == "__main__":
    main()
