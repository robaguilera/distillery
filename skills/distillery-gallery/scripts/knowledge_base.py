#!/usr/bin/env python3
"""Knowledge base for distillery gallery reports.

Public interface
----------------
store(canonical_extraction)   – Add/update one report in manifest.json.
all()                         – Return all indexed reports.
query(tags, keywords)         – Filter reports by tags or keyword substring.
rebuild(scan_dir)             – Full filesystem scan → manifest.json + index.html.
migrate_legacy(html_path)     – Backfill meta into a legacy report (explicit only).

CLI
---
python3 knowledge_base.py store PATH_TO_SIDECAR.json
python3 knowledge_base.py rebuild --dir DIR
"""
import argparse
import importlib.util
import json
import pathlib
import re
import sys
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CHAN_DURATION_RE = re.compile(r'^\d+\s*(min|h\b)', re.IGNORECASE)
_CHAN_DATE_RE = re.compile(
    r'^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d',
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Private helpers: manifest I/O
# ---------------------------------------------------------------------------

def _read_manifest(manifest_path: pathlib.Path) -> dict:
    """Read manifest.json; return empty manifest if missing or invalid."""
    if manifest_path.exists():
        try:
            return json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {"generated": "", "count": 0, "reports": []}


def _write_manifest_returning(manifest_path: pathlib.Path, reports: list[dict]) -> dict:
    """Write sorted reports to manifest.json and return the manifest dict."""
    reports.sort(key=lambda m: m.get("filename", ""), reverse=True)
    manifest = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": len(reports),
        "reports": reports,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


# ---------------------------------------------------------------------------
# Private helpers: index.html patching
# ---------------------------------------------------------------------------

def _find_index_html() -> pathlib.Path | None:
    """Find the gallery index.html shipped with this skill."""
    candidates = [
        pathlib.Path(__file__).parent.parent / "index.html",  # skills/distillery-gallery/index.html
        pathlib.Path(__file__).parent / "index.html",          # scripts/index.html (fallback)
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def _write_index_html(out_dir: pathlib.Path, manifest: dict) -> None:
    """Patch index.html with inlined manifest and write to out_dir."""
    index_src = _find_index_html()
    index_dst = out_dir / "index.html"
    if not index_src:
        return
    index_html = index_src.read_text(encoding="utf-8")
    safe_json = json.dumps(manifest, ensure_ascii=False).replace("</", "<\\/")
    inline_script = (
        "<script>window.__MANIFEST__ = "
        + safe_json
        + ";</script>"
    )
    patched = index_html.replace("<script>\n(function", inline_script + "\n<script>\n(function", 1)
    if patched == index_html:
        patched = index_html.replace("</body>", inline_script + "\n</body>", 1)
    index_dst.write_text(patched, encoding="utf-8")
    print(f"index.html → {index_dst}")


# ---------------------------------------------------------------------------
# Private helpers: meta extraction + channel sanitisation
# ---------------------------------------------------------------------------

def _sanitize_channel(value: str) -> str:
    if not value:
        return ""
    if "&middot;" in value:
        return ""
    if value.count("·") >= 2:
        return ""
    if _CHAN_DURATION_RE.match(value):
        return ""
    if _CHAN_DATE_RE.match(value):
        return ""
    return value


def _extract_meta(path: pathlib.Path) -> dict | None:
    """Extract metadata from a report's .json sidecar file.

    Returns the sidecar dict if found, or None if no sidecar exists.
    Legacy reports without a sidecar are skipped; use migrate_legacy() /
    backfill_meta.py to handle those explicitly.
    """
    sidecar = path.with_suffix(".json")
    if sidecar.exists():
        try:
            return json.loads(sidecar.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def store(canonical_extraction: dict, out_dir: str | None = None) -> None:
    """Add or update one report in manifest.json.

    Identifies duplicates by the ``filename`` field — updates in place if
    found, appends otherwise.  Does NOT scan the filesystem.

    Parameters
    ----------
    canonical_extraction:
        Dict with at minimum a ``filename`` field.
    out_dir:
        Directory where ``manifest.json`` lives.  Defaults to
        ``~/Downloads/distillery``.
    """
    data = dict(canonical_extraction)  # don't mutate caller's dict
    filename = data.get("filename", "")
    if not filename:
        raise ValueError("canonical_extraction must have a 'filename' field")

    if out_dir is None:
        manifest_path = pathlib.Path.home() / "Downloads" / "distillery" / "manifest.json"
    else:
        manifest_path = pathlib.Path(out_dir).expanduser().resolve() / "manifest.json"

    existing = _read_manifest(manifest_path)
    reports = existing.get("reports", [])

    # Channel sanitisation
    if data.get("type") == "batch":
        data.setdefault("channel", f"{data.get('videoCount', '?')} videos")
    else:
        data["channel"] = _sanitize_channel(data.get("channel", ""))

    # Find and update or append
    idx = next((i for i, r in enumerate(reports) if r.get("filename") == filename), None)
    if idx is not None:
        reports[idx] = data
    else:
        reports.append(data)

    manifest = _write_manifest_returning(manifest_path, reports)
    print(f"manifest.json → {manifest_path}  ({manifest['count']} reports)")
    _write_index_html(manifest_path.parent, manifest)


def _store_from_sidecar_path(sidecar_path: pathlib.Path) -> None:
    """CLI helper: load a sidecar JSON and call store() with the correct out_dir.

    The manifest lives at ``sidecar_path.parent.parent / "manifest.json"``
    (sidecars live in ``reports/``, manifest is in the parent dir).
    """
    data = json.loads(sidecar_path.read_text(encoding="utf-8"))
    # Always derive from the actual sidecar path so the manifest entry always
    # carries the "reports/" prefix the gallery needs to build correct URLs.
    data["filename"] = "reports/" + sidecar_path.with_suffix(".html").name
    out_dir = str(sidecar_path.parent.parent)
    store(data, out_dir=out_dir)


def all() -> list[dict]:
    """Return all indexed reports from manifest.json.

    Looks for manifest.json in ~/Downloads/distillery/ by default.
    """
    default_path = pathlib.Path.home() / "Downloads" / "distillery" / "manifest.json"
    manifest = _read_manifest(default_path)
    return manifest.get("reports", [])


def query(tags: list[str] = None, keywords: list[str] = None) -> list[dict]:
    """Return reports matching any of the given tags OR keywords.

    - Tags: exact match against any item in the report's ``tags`` list.
    - Keywords: case-insensitive substring match against any item in
      the report's ``keywords`` list.
    """
    reports = all()
    results = []
    tags_set = set(tags) if tags else set()
    kw_lower = [k.lower() for k in keywords] if keywords else []

    for report in reports:
        if tags_set and tags_set.intersection(report.get("tags", [])):
            results.append(report)
            continue
        if kw_lower:
            report_kws = [k.lower() for k in report.get("keywords", [])]
            if any(q in rk for q in kw_lower for rk in report_kws):
                results.append(report)
    return results


def rebuild(scan_dir: str) -> None:
    """Full rebuild from filesystem scan.

    Produces identical output to the original ``build_index.py main()``.
    Does NOT call backfill_meta automatically — reports without a meta
    block are skipped with a warning.
    """
    scan_path = pathlib.Path(scan_dir).expanduser().resolve()
    out_dir = scan_path  # manifest.json goes in the same dir as the scan root

    if not scan_path.is_dir():
        print(f"ERROR: directory not found: {scan_path}", file=sys.stderr)
        sys.exit(1)

    out_dir.mkdir(parents=True, exist_ok=True)

    seen: set[str] = set()
    reports: list[dict] = []
    skipped = 0

    # Phase 1: reports/ subdir (new location)
    reports_subdir = scan_path / "reports"
    if reports_subdir.is_dir():
        for path in sorted(reports_subdir.glob("*distillery*.html"),
                           key=lambda p: p.name, reverse=True):
            meta = _extract_meta(path)
            if meta is None:
                skipped += 1
                print(f"  skipped (no sidecar): reports/{path.name}")
                continue
            meta["filename"] = "reports/" + path.name
            seen.add(path.name)
            if meta.get("type") == "batch":
                meta.setdefault("channel", f"{meta.get('videoCount', '?')} videos")
            else:
                meta["channel"] = _sanitize_channel(meta.get("channel", ""))
            reports.append(meta)

    # Phase 2: root (backward compat — old flat layout)
    for path in sorted(scan_path.glob("*distillery*.html"),
                       key=lambda p: p.name, reverse=True):
        if path.name == "index.html" or path.name in seen:
            continue
        meta = _extract_meta(path)
        if meta is None:
            skipped += 1
            print(f"  skipped (no sidecar): {path.name}")
            continue
        if not meta.get("filename"):
            meta["filename"] = path.name
        if meta.get("type") == "batch":
            meta.setdefault("channel", f"{meta.get('videoCount', '?')} videos")
        else:
            meta["channel"] = _sanitize_channel(meta.get("channel", ""))
        reports.append(meta)

    # Re-sort combined list newest-first
    reports.sort(key=lambda m: m.get("filename", ""), reverse=True)

    manifest = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": len(reports),
        "reports": reports,
    }

    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"manifest.json → {manifest_path}  ({len(reports)} reports, {skipped} skipped)")

    _write_index_html(out_dir, manifest)


def migrate_legacy(html_path: str) -> bool:
    """Backfill meta into a legacy HTML report.

    Only called explicitly — never triggered automatically by rebuild().
    Returns True if the file was modified.
    """
    path = pathlib.Path(html_path).expanduser().resolve()
    try:
        spec = importlib.util.spec_from_file_location(
            "backfill_meta", pathlib.Path(__file__).parent / "backfill_meta.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.backfill_file(path, dry_run=False)
    except Exception as exc:
        print(f"ERROR: migrate_legacy failed for {path}: {exc}", file=sys.stderr)
        return False


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _cli_store(args):
    sidecar = pathlib.Path(args.path).expanduser().resolve()
    if not sidecar.exists():
        print(f"ERROR: file not found: {sidecar}", file=sys.stderr)
        sys.exit(1)
    _store_from_sidecar_path(sidecar)


def _cli_rebuild(args):
    rebuild(args.dir)


def main():
    parser = argparse.ArgumentParser(description="Distillery knowledge base CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_store = sub.add_parser("store", help="Add/update one report from a sidecar JSON")
    p_store.add_argument("path", help="Path to the .json sidecar file")

    p_rebuild = sub.add_parser("rebuild", help="Full rebuild from filesystem scan")
    p_rebuild.add_argument(
        "--dir", required=True, help="Directory containing distillery HTML reports"
    )

    args = parser.parse_args()
    if args.command == "store":
        _cli_store(args)
    elif args.command == "rebuild":
        _cli_rebuild(args)


if __name__ == "__main__":
    main()
