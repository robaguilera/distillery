#!/usr/bin/env python3
"""Unified ingestion: fetch transcript + metadata and merge into one JSON dict.

Usage: python3 ingest.py VIDEO_ID [LANG_PREF]

Calls fetch_transcript.py and fetch_metadata.py as subprocesses, merges
their outputs with yt-dlp winning on channel/published/views/duration,
and prints a single JSON object to stdout.
"""
import json
import pathlib
import subprocess
import sys

# ── Public interface ───────────────────────────────────────────────────────

def ingest(video_id: str, lang_pref: str = "") -> dict:
    """Fetch and merge transcript + metadata for a video.

    Returns a unified dict with all fields needed for distillation.
    yt-dlp wins on channel/published/views/duration when available.
    yt-dlp errors are non-fatal; transcript errors are fatal (error field set).
    """
    here = pathlib.Path(__file__).parent
    py = sys.executable

    # Fetch transcript (fatal on error)
    # Use "--" before video_id so argparse won't mistake IDs starting with "-" for flags
    cmd = [py, str(here / "fetch_transcript.py"), "--", video_id]
    if lang_pref:
        cmd.append(lang_pref)
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        t = json.loads(proc.stdout)
    except subprocess.TimeoutExpired:
        return {"error": "ERROR:TRANSCRIPT_FETCH_FAILED: timeout fetching transcript"}
    except json.JSONDecodeError:
        return {"error": "ERROR:TRANSCRIPT_FETCH_FAILED: unexpected output from fetch_transcript"}

    if t.get("error"):
        return {"error": t["error"]}

    # Fetch metadata (non-fatal — log and fall back)
    m: dict = {}
    try:
        m_proc = subprocess.run(
            [py, str(here / "fetch_metadata.py"), "--", video_id],
            capture_output=True, text=True, timeout=60,
        )
        m = json.loads(m_proc.stdout)
    except Exception:
        pass

    return {
        "video_id":        video_id,
        "transcript":      t.get("transcript", ""),
        "lang":            t.get("lang", ""),
        "lang_warn":       t.get("lang_warn", False),
        "lang_warn_msg":   t.get("lang_warn_msg", ""),
        # yt-dlp wins on these four; falls back to HTML-scraped values
        "title":           t.get("title", ""),
        "channel":         m.get("channel") or t.get("channel", ""),
        "published":       m.get("published") or t.get("published", ""),
        "views":           m.get("views") or t.get("views", ""),
        "duration":        m.get("duration") or t.get("duration", ""),
        # yt-dlp exclusive fields
        "description_html": m.get("description_html", ""),
        "chapters":         m.get("chapters", []),
        # Timing fields for filename generation
        "date":            t.get("date", ""),
        "time":            t.get("time", ""),
        "error":           None,
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Fetch and merge video transcript + metadata")
    parser.add_argument("video_id")
    parser.add_argument("lang_pref", nargs="?", default="")
    args = parser.parse_args()

    result = ingest(args.video_id, args.lang_pref)

    if result.get("error"):
        print(result["error"])
        sys.exit(1)

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
