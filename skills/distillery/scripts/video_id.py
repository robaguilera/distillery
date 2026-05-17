#!/usr/bin/env python3
"""Canonical YouTube video ID extraction.

Provides two functions:
- from_url(url)  — extract an 11-character video ID from any YouTube URL or
                   pass through a bare ID unchanged.
- from_html(html) — extract a video ID embedded in a rendered distillery
                    report (iframe embed or watch-link href).
"""
import re

_YT_ID_RE = re.compile(r'^[A-Za-z0-9_-]{11}$')
_URL_PATTERNS = [
    # Standard watch URL:  ?v=VIDEO_ID
    re.compile(r'[?&]v=([A-Za-z0-9_-]{11})'),
    # Short URL:           youtu.be/VIDEO_ID
    re.compile(r'youtu\.be/([A-Za-z0-9_-]{11})'),
    # Embed URL:           /embed/VIDEO_ID
    re.compile(r'/embed/([A-Za-z0-9_-]{11})'),
    # Shorts URL:          /shorts/VIDEO_ID
    re.compile(r'/shorts/([A-Za-z0-9_-]{11})'),
]


def from_url(url_or_id: str) -> str:
    """Return the 11-character video ID from a YouTube URL or bare ID.

    If the input is already a bare 11-character ID it is returned as-is.
    Returns an empty string if no valid ID can be found.
    """
    s = url_or_id.strip()
    if _YT_ID_RE.match(s):
        return s
    for pat in _URL_PATTERNS:
        m = pat.search(s)
        if m:
            return m.group(1)
    return ""


def from_html(html: str) -> str:
    """Return the video ID embedded in a rendered distillery report HTML.

    Checks, in order:
    1. iframe src="https://www.youtube.com/embed/VIDEO_ID"
    2. href="https://www.youtube.com/watch?v=VIDEO_ID"

    Returns an empty string if nothing is found.
    """
    # iframe embed
    m = re.search(r'youtube\.com/embed/([A-Za-z0-9_-]{11})', html)
    if m:
        return m.group(1)
    # watch link
    m = re.search(r'youtube\.com/watch\?v=([A-Za-z0-9_-]{11})', html)
    if m:
        return m.group(1)
    return ""
