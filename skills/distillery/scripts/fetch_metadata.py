#!/usr/bin/env python3
"""Fetch enriched YouTube metadata via yt-dlp.

Usage: python3 fetch_metadata.py VIDEO_ID
"""
import argparse
import html
import json
import pathlib
import re
import subprocess
import sys

# Shared formatting helpers — single source of truth in media_format.py
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from media_format import _format_views, _format_duration, _format_published  # noqa: E402


def _linkify(line):
    parts = []
    last = 0
    for m in re.finditer(r"https?://\S+", line):
        parts.append(html.escape(line[last:m.start()]))
        url = m.group()
        parts.append(
            f'<a href="{html.escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">'
            f"{html.escape(url)}</a>"
        )
        last = m.end()
    parts.append(html.escape(line[last:]))
    return "".join(parts)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("video_id")
    args = parser.parse_args()

    video_id = args.video_id
    url = f"https://www.youtube.com/watch?v={video_id}"

    # Prefer the venv-local yt-dlp binary (installed alongside this script's python)
    _venv_bin = pathlib.Path(sys.executable).parent / "yt-dlp"
    _ytdlp = str(_venv_bin) if _venv_bin.exists() else "yt-dlp"

    try:
        result = subprocess.run(
            [_ytdlp, "--skip-download", "--quiet", "--no-warnings",
             "--no-check-formats", "--dump-json", url],
            capture_output=True, text=True, timeout=60,
        )
    except FileNotFoundError:
        print("ERROR:YTDLP_MISSING: yt-dlp not installed — run: brew install yt-dlp or pip install yt-dlp")
        sys.exit(0)
    except subprocess.TimeoutExpired:
        print("ERROR:YTDLP_TIMEOUT: yt-dlp timed out after 60s")
        sys.exit(0)

    raw = result.stdout
    if not raw.strip():
        stderr_hint = result.stderr.strip()[:200]
        print(f"ERROR:YTDLP_NO_OUTPUT: yt-dlp produced no output — {stderr_hint}")
        sys.exit(0)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"ERROR:YTDLP_JSON_ERROR: {e} — raw output: {raw[:200]}")
        sys.exit(0)

    desc_raw = (data.get("description") or "")[:3000]
    if len(data.get("description") or "") > 3000:
        desc_raw += "\u2026"
    desc_html = "<br>".join(_linkify(line) for line in desc_raw.split("\n"))

    chapters = data.get("chapters") or []
    published = _format_published(data.get("upload_date") or "")
    views = _format_views(data.get("view_count"))
    duration = _format_duration(data.get("duration"))

    print(f'YTDLP_CHANNEL: {data.get("channel") or ""}')
    print(f"YTDLP_PUBLISHED: {published}")
    print(f"YTDLP_VIEWS: {views}")
    print(f"YTDLP_DURATION: {duration}")
    print(f"YTDLP_DESC_HTML: {desc_html}")
    print(f"YTDLP_CHAPTERS: {json.dumps(chapters)}")


if __name__ == "__main__":
    main()
