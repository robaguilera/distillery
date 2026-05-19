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

try:
    from . import canonical as _canonical
except (ImportError, ValueError):
    import canonical as _canonical

EXPECTED_KEYS = {"BATCH_TITLE", "BATCH_VIDEOS_JSON", "SYNTHESIS_JSON"}
AGENT_DIRS = ("agents", "claude", "copilot", "gemini", "cursor", "windsurf", "opencode", "codex")


def _find_shared_asset(name: str) -> pathlib.Path | None:
    """Locate a shared asset (shared.css, shared_app.js) alongside the templates."""
    import os
    skill_dir = os.environ.get("SKILL_DIR")
    if skill_dir:
        p = pathlib.Path(skill_dir).parent / name
        if p.exists():
            return p
    home = pathlib.Path.home()
    for agent in AGENT_DIRS:
        p = home / f".{agent}" / "skills" / "distillery" / name
        if p.exists():
            return p
    return None

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

    # Auto-generate batch meta before video processing — _prepare_video_data drops channel/tags/keywords
    if not data.get("BATCH_DISTILLERY_META"):
        data["BATCH_DISTILLERY_META"] = _build_batch_meta(data, output_path)

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

    # Inject shared CSS and JS before per-report substitution
    for asset_key, asset_name in (("SHARED_CSS", "shared.css"), ("SHARED_JS", "shared_app.js")):
        if "{{" + asset_key + "}}" in html:
            asset_path = _find_shared_asset(asset_name)
            if asset_path is not None:
                html = html.replace("{{" + asset_key + "}}", asset_path.read_text(encoding="utf-8"))
            else:
                print(f"WARNING: {asset_name} not found — install may be incomplete", file=sys.stderr)

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

    # Write sidecar so the Knowledge Base has a clean metadata source
    meta_raw = data.get("BATCH_DISTILLERY_META")
    if meta_raw:
        try:
            meta_dict = json.loads(meta_raw) if isinstance(meta_raw, str) else meta_raw
            _canonical.write_sidecar(meta_dict, str(out))
        except Exception as exc:
            print(f"WARNING: could not write batch sidecar: {exc}", file=sys.stderr)

    return str(out)


def _parse_duration_seconds(s: str) -> int:
    """Parse duration strings like '1h 16m', '22 min', '1h' into seconds."""
    import re
    if not s:
        return 0
    hm = re.match(r'(\d+)h(?:\s+(\d+)m)?', s)
    if hm:
        return int(hm.group(1)) * 3600 + int(hm.group(2) or 0) * 60
    m = re.match(r'(\d+)\s*min', s)
    if m:
        return int(m.group(1)) * 60
    return 0


def _format_duration_seconds(total: int) -> str:
    """Format total seconds as '1h 16m', '45 min', etc."""
    if total <= 0:
        return ""
    minutes = total // 60
    if minutes < 60:
        return f"{minutes} min"
    h, m = divmod(minutes, 60)
    return f"{h}h {m}m" if m else f"{h}h"


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

    # Aggregate tags, keywords, and duration from individual videos
    tag_counts: dict[str, int] = {}
    all_keywords: list[str] = []
    total_seconds = 0
    video_stubs = []
    for v in videos:
        for t in (v.get("tags") or []):
            if t:
                tag_counts[t] = tag_counts.get(t, 0) + 1
        all_keywords.extend(v.get("keywords") or [])
        total_seconds += _parse_duration_seconds(v.get("duration", ""))
        video_stubs.append({
            "videoId": v.get("videoId", ""),
            "title": v.get("title", ""),
            "channel": v.get("channel", ""),
        })

    # Most-common tags first (by video count), cap at 3
    tags = [t for t, _ in sorted(tag_counts.items(), key=lambda x: -x[1])][:3]
    seen_kw: set[str] = set()
    keywords = [k for k in all_keywords if k and not (seen_kw.add(k) or k in seen_kw)]  # type: ignore[func-returns-value]

    duration = _format_duration_seconds(total_seconds)
    filename = pathlib.Path(output_path).name
    generation_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    meta = {
        "schemaVersion": 1,
        "type": "batch",
        "title": title,
        "filename": filename,
        "generationDate": generation_date,
        "videoCount": len(videos),
        "duration": duration,
        "summary": summary,
        "tags": tags,
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
