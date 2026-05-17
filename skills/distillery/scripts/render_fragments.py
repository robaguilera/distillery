#!/usr/bin/env python3
"""Shared HTML fragment generators for distillery report renderers.

These functions convert structured data from a Canonical Extraction JSON
into the HTML fragments that templates expect. Both render_report.py and
render_batch_report.py import from here.
"""
import html as html_mod


def key_points_to_html(key_points: list) -> str:
    """Convert a keyPoints list to an HTML <li> string."""
    parts = []
    for kp in key_points:
        headline = html_mod.escape(kp.get("headline", ""))
        body = kp.get("body", "")
        quote = kp.get("speakerQuote")
        li = f"<li><strong>{headline}</strong>"
        if body:
            body_escaped = html_mod.escape(body)
            if quote:
                quote_escaped = html_mod.escape(quote)
                li += f"\n<p>{body_escaped} <em>{quote_escaped}</em></p>"
            else:
                li += f"\n<p>{body_escaped}</p>"
        li += "</li>"
        parts.append(li)
    return "\n".join(parts)


def outline_to_html(outline: list, video_id: str) -> str:
    """Convert an outline list to an HTML <li> string with timestamp links."""
    parts = []
    for entry in outline:
        t = int(entry.get("startSeconds", 0))
        title = html_mod.escape(entry.get("title", ""))
        detail = html_mod.escape(entry.get("detail", ""))
        h, rem = divmod(t, 3600)
        m2, s2 = divmod(rem, 60)
        display_ts = f"{h}:{m2:02d}:{s2:02d}" if h > 0 else f"{m2}:{s2:02d}"
        vid = html_mod.escape(video_id, quote=True)
        li = (
            f'<li><a class="ts" data-t="{t}" '
            f'href="https://www.youtube.com/watch?v={vid}&t={t}" '
            f'target="_blank" rel="noopener noreferrer">▶ {display_ts}</a>'
            f" — <span class=\"outline-title\">{title}</span>"
            f"<span class=\"outline-detail\">{detail}</span></li>"
        )
        parts.append(li)
    return "\n".join(parts)


def meta_line(extraction: dict) -> str:
    """Build a plain-text meta line from a Canonical Extraction dict."""
    parts = [
        extraction.get("channel", ""),
        extraction.get("duration", ""),
        extraction.get("publishDate", ""),
        extraction.get("views", ""),
    ]
    line = " · ".join(p for p in parts if p)
    if extraction.get("langWarn"):
        line += " · ⚠ Requested language not available"
    return line


def description_section(desc_html: str) -> str:
    """Wrap a description HTML string in a collapsible <details> block, or return ''."""
    if not desc_html:
        return ""
    return (
        '<details class="description-details"><summary>YouTube Description</summary>'
        f'<div class="video-description">{desc_html}</div></details>'
    )


def themes_to_html(themes: list) -> str:
    """Convert a synthesis themes list to an HTML <li> string."""
    parts = []
    for theme in themes:
        headline = html_mod.escape(theme.get("headline", ""))
        body = html_mod.escape(theme.get("body", ""))
        li = f"<li><strong>{headline}</strong>"
        if body:
            li += f"\n<p>{body}</p>"
        li += "</li>"
        parts.append(li)
    return "\n".join(parts)
