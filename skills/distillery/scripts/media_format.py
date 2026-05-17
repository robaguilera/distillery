#!/usr/bin/env python3
"""Shared formatting helpers for YouTube media metadata.

These helpers are the single source of truth for human-readable formatting
of views, duration, and publish date. They are imported by ingest.py,
fetch_transcript.py, and fetch_metadata.py.
"""


def _format_views(vc) -> str:
    if vc is None:
        return ""
    vc = int(vc)
    return (f"{vc/1e6:.1f}M views" if vc >= 1_000_000
            else f"{vc/1e3:.0f}K views" if vc >= 1_000
            else f"{vc} views")


def _format_duration(dur_s) -> str:
    h, rem = divmod(int(dur_s or 0), 3600)
    m2 = rem // 60
    return f"{h}h {m2}m" if h > 0 else f"{m2} min"


def _format_published(upload_date: str) -> str:
    """Format YYYYMMDD string → 'Mon DD YYYY'."""
    if len(upload_date) != 8:
        return ""
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return f"{months[int(upload_date[4:6])-1]} {int(upload_date[6:8])} {upload_date[:4]}"
