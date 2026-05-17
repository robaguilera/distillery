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


# ── Output parsers ─────────────────────────────────────────────────────────

def _parse_transcript_output(output: str) -> dict:
    result: dict = {"lang_warn": False, "lang_warn_msg": ""}
    transcript_lines: list[str] = []
    header_done = False

    for line in output.splitlines():
        if not header_done:
            if line.startswith("ERROR:"):
                result["error"] = line
                return result
            elif line.startswith("LANG_WARN: "):
                result["lang_warn"] = True
                result["lang_warn_msg"] = line[11:]
            elif line.startswith("TITLE: "):
                result["title"] = line[7:]
            elif line.startswith("CHANNEL: "):
                result["channel"] = line[9:]
            elif line.startswith("PUBLISHED: "):
                result["published"] = line[11:]
            elif line.startswith("VIEWS: "):
                result["views"] = line[7:]
            elif line.startswith("DURATION: "):
                result["duration"] = line[10:]
            elif line.startswith("DATE: "):
                result["date"] = line[6:]
            elif line.startswith("TIME: "):
                result["time"] = line[6:]
            elif line.startswith("LANG: "):
                result["lang"] = line[6:]
                header_done = True
        else:
            transcript_lines.append(line)

    result["transcript"] = "\n".join(transcript_lines)
    return result


def _parse_metadata_output(output: str) -> dict:
    result: dict = {}
    for line in output.splitlines():
        if line.startswith("YTDLP_CHANNEL: "):
            result["channel"] = line[15:]
        elif line.startswith("YTDLP_PUBLISHED: "):
            result["published"] = line[17:]
        elif line.startswith("YTDLP_VIEWS: "):
            result["views"] = line[13:]
        elif line.startswith("YTDLP_DURATION: "):
            result["duration"] = line[16:]
        elif line.startswith("YTDLP_DESC_HTML: "):
            result["description_html"] = line[17:]
        elif line.startswith("YTDLP_CHAPTERS: "):
            try:
                result["chapters"] = json.loads(line[16:])
            except json.JSONDecodeError:
                result["chapters"] = []
        elif line.startswith("ERROR:"):
            result["error"] = line
    return result


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
    cmd = [py, str(here / "fetch_transcript.py"), video_id]
    if lang_pref:
        cmd.append(lang_pref)
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        t = _parse_transcript_output(proc.stdout)
    except subprocess.TimeoutExpired:
        return {"error": "ERROR:TRANSCRIPT_FETCH_FAILED: timeout fetching transcript"}

    if t.get("error"):
        return {"error": t["error"]}

    # Fetch metadata (non-fatal — log and fall back)
    m: dict = {}
    try:
        m_proc = subprocess.run(
            [py, str(here / "fetch_metadata.py"), video_id],
            capture_output=True, text=True, timeout=60,
        )
        m = _parse_metadata_output(m_proc.stdout)
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
