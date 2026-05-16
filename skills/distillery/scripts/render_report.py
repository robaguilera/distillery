#!/usr/bin/env python3
"""Render an HTML report by substituting JSON values into a view template.

Usage (legacy format):
    echo '{"VIDEO_ID": "...", ...}' | python3 render_report.py OUTPUT_PATH

Usage (Canonical Extraction format):
    echo '{canonical json}' | python3 render_report.py --view default OUTPUT_PATH

The script auto-detects the input format by checking for the 'schemaVersion' key.
Legacy format: uppercase keys (VIDEO_ID, VIDEO_TITLE, …)
Canonical format: schemaVersion + typed content fields

Discovers templates via SKILL_DIR env var (set by ~/.distillery/{agent}.env),
falling back to the legacy agent directory search.
"""
import html as html_mod
import json
import pathlib
import re
import sys

EXPECTED_KEYS = {
    "VIDEO_ID", "VIDEO_TITLE", "VIDEO_URL", "META_LINE", "SUMMARY",
    "KEY_POINTS", "TAKEAWAY", "OUTLINE", "DESCRIPTION_SECTION", "VIDEO_LENS_META",
}

AGENT_DIRS = ("agents", "claude", "copilot", "gemini", "cursor", "windsurf", "opencode", "codex")

_TEMPLATE_NAMES = {
    "default":          "template.html",
    "study-guide":      "template_study_guide.html",
    "executive-brief":  "template_executive_brief.html",
}


def find_template(view: str = "default") -> pathlib.Path:
    """Find the template for the given view, preferring ~/.distillery/."""
    import os
    name = _TEMPLATE_NAMES.get(view, "template.html")
    skill_dir = os.environ.get("SKILL_DIR")
    if skill_dir:
        p = pathlib.Path(skill_dir).parent / name
        if p.exists():
            return p
        p = pathlib.Path(skill_dir).parent / "template.html"
        if p.exists():
            return p
    home = pathlib.Path.home()
    for agent in AGENT_DIRS:
        p = home / f".{agent}" / "skills" / "distillery" / name
        if p.exists():
            return p
        p = home / f".{agent}" / "skills" / "distillery" / "template.html"
        if p.exists():
            return p
    raise FileNotFoundError(
        "template.html not found — run: ./install.sh claude (or see README)"
    )


# ── Canonical Extraction → template key conversion ────────────────────────

def _key_points_to_html(key_points: list) -> str:
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


def _outline_to_html(outline: list, video_id: str) -> str:
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


def _meta_line(extraction: dict) -> str:
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


def canonical_to_template_keys(extraction: dict) -> dict:
    """Convert a schemaVersion-1 Canonical Extraction to template substitution keys."""
    video_id = extraction.get("videoId", "")
    title = html_mod.escape(extraction.get("title", ""))
    video_url = f"https://www.youtube.com/watch?v={html_mod.escape(video_id, quote=True)}"

    meta_obj = {
        "schemaVersion":  extraction.get("schemaVersion", 1),
        "videoId":        video_id,
        "title":          extraction.get("title", ""),
        "channel":        extraction.get("channel", ""),
        "duration":       extraction.get("duration", ""),
        "publishDate":    extraction.get("publishDate", ""),
        "generationDate": extraction.get("generationDate", ""),
        "summary":        extraction.get("summary", "")[:300],
        "tags":           extraction.get("tags", []),
        "keywords":       extraction.get("keywords", []),
        "filename":       extraction.get("filename", ""),
    }

    desc_html = extraction.get("descriptionHtml", "")
    description_section = (
        '<details class="description-details"><summary>YouTube Description</summary>'
        f'<div class="video-description">{desc_html}</div></details>'
        if desc_html else ""
    )

    return {
        "VIDEO_ID":             video_id,
        "VIDEO_TITLE":          title,
        "VIDEO_URL":            video_url,
        "META_LINE":            html_mod.escape(_meta_line(extraction)),
        "SUMMARY":              html_mod.escape(extraction.get("summary", "")),
        "TAKEAWAY":             html_mod.escape(extraction.get("takeaway", "")),
        "KEY_POINTS":           _key_points_to_html(extraction.get("keyPoints", [])),
        "OUTLINE":              _outline_to_html(extraction.get("outline", []), video_id),
        "DESCRIPTION_SECTION":  description_section,
        "VIDEO_LENS_META":      json.dumps(meta_obj, ensure_ascii=False).replace("</", "<\\/"),
        "TRANSCRIPT":           html_mod.escape(extraction.get("transcript", "")),
    }


# ── Core render function ───────────────────────────────────────────────────

def render(
    data: dict,
    output_path: str,
    template_path: pathlib.Path | None = None,
    view: str = "default",
    write_sidecar: bool = False,
) -> str:
    """Substitute data into template and write to output_path. Returns the output path.

    Accepts both legacy (uppercase keys) and Canonical Extraction (schemaVersion) formats.
    When write_sidecar=True, also writes a .json sidecar alongside the HTML file.
    """
    if "schemaVersion" in data:
        # Canonical Extraction format — convert to template keys
        if write_sidecar:
            sys.path.insert(0, str(pathlib.Path(__file__).parent))
            import canonical as _canonical
            _canonical.write_sidecar(data, output_path)
        data = canonical_to_template_keys(data)
        if template_path is None:
            template_path = find_template(view)
    else:
        if template_path is None:
            template_path = find_template(view)

    html = template_path.read_text(encoding="utf-8")
    for key, value in data.items():
        html = html.replace("{{" + key + "}}", value)

    remaining = re.findall(r"\{\{[A-Z_]+\}\}", html)
    if remaining:
        print(f"WARNING: unreplaced template placeholders: {remaining}", file=sys.stderr)

    out = pathlib.Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return str(out)


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Render a distillery HTML report from JSON on stdin"
    )
    parser.add_argument("--view", default="default",
                        choices=list(_TEMPLATE_NAMES.keys()),
                        help="View template to use (default: default)")
    parser.add_argument("output_path", help="Destination .html file path")
    args = parser.parse_args()

    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"ERROR: invalid JSON on stdin: {e}", file=sys.stderr)
        sys.exit(1)

    is_canonical = "schemaVersion" in data
    if not is_canonical:
        missing = EXPECTED_KEYS - set(data.keys())
        if missing:
            print(f"WARNING: missing keys: {sorted(missing)}", file=sys.stderr)

    try:
        result = render(data, args.output_path, view=args.view, write_sidecar=is_canonical)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Rendered → {result}")


if __name__ == "__main__":
    main()
