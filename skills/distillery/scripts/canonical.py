#!/usr/bin/env python3
"""Canonical Extraction: schema definition, validation, and sidecar I/O.

The Canonical Extraction is the structured JSON produced from a media item —
the source of truth that all Views render from.

schemaVersion 0 = legacy (no schema, embedded VIDEO_LENS_META only)
schemaVersion 1 = this schema
"""
import json
import pathlib

SCHEMA_VERSION = 1

# Required top-level string fields
_REQUIRED_FIELDS = {
    "videoId", "title", "channel", "duration", "publishDate",
    "generationDate", "view", "summary", "takeaway", "filename",
}

_VALID_VIEWS = {"default", "study-guide", "executive-brief"}


def validate(data: dict) -> list[str]:
    """Return a list of validation error strings (empty = valid)."""
    errors = []
    for field in _REQUIRED_FIELDS:
        if field not in data:
            errors.append(f"missing required field: {field}")
    if "keyPoints" in data and not isinstance(data["keyPoints"], list):
        errors.append("keyPoints must be an array")
    if "outline" in data and not isinstance(data["outline"], list):
        errors.append("outline must be an array")
    if "tags" in data and not isinstance(data["tags"], list):
        errors.append("tags must be an array")
    if "keywords" in data and not isinstance(data["keywords"], list):
        errors.append("keywords must be an array")
    view = data.get("view", "")
    if view and view not in _VALID_VIEWS:
        errors.append(f"view must be one of {_VALID_VIEWS}, got: {view!r}")
    return errors


def build(data: dict) -> dict:
    """Return a complete schemaVersion-1 Canonical Extraction from raw LLM output.

    Fills defaults for missing optional fields. Raises ValueError on missing
    required fields.
    """
    errors = validate(data)
    if errors:
        raise ValueError(f"Invalid canonical extraction: {'; '.join(errors)}")

    return {
        "schemaVersion":  SCHEMA_VERSION,
        "videoId":        data["videoId"],
        "title":          data["title"],
        "channel":        data.get("channel", ""),
        "duration":       data.get("duration", ""),
        "views":          data.get("views", ""),
        "publishDate":    data.get("publishDate", ""),
        "generationDate": data["generationDate"],
        "view":           data.get("view", "default"),
        "summary":        data["summary"],
        "takeaway":       data["takeaway"],
        "keyPoints":      data.get("keyPoints", []),
        "outline":        data.get("outline", []),
        "tags":           data.get("tags", []),
        "keywords":       data.get("keywords", []),
        "filename":       data["filename"],
        # Non-LLM fields passed alongside canonical content
        "descriptionHtml": data.get("descriptionHtml", ""),
        "langWarn":        data.get("langWarn", False),
    }


def write_sidecar(extraction: dict, html_path: str) -> pathlib.Path:
    """Write the Canonical Extraction as a .json sidecar alongside the HTML report."""
    sidecar = pathlib.Path(html_path).with_suffix(".json")
    sidecar.write_text(
        json.dumps(extraction, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return sidecar


def read_sidecar(html_path: str) -> dict | None:
    """Read the .json sidecar for an HTML report, or None if it doesn't exist."""
    sidecar = pathlib.Path(html_path).with_suffix(".json")
    if not sidecar.exists():
        return None
    try:
        return json.loads(sidecar.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
