#!/usr/bin/env python3
"""Orchestration for Batch Mode: ingesting multiple videos and assembling the report.

Usage:
    python3 batch.py ingest <url1> <url2> ...
    python3 batch.py assemble --title "Batch Title" --distillations file1.json file2.json \
        --synthesis synth.json
"""
import argparse
import json
import sys

# Import local modules
try:
    from . import ingest as _ingest
    from . import render_batch_report
    from . import video_id as _video_id
except (ImportError, ValueError):
    import ingest as _ingest
    import render_batch_report
    import video_id as _video_id

def cmd_ingest(args):
    """Ingest multiple URLs and print a list of metadata objects."""
    results = []
    for url in args.urls:
        video_id = _video_id.from_url(url)
        if not video_id:
            print(f"Error: could not extract video ID from: {url}", file=sys.stderr)
            continue

        res = _ingest.ingest(video_id)
        if res.get("error"):
            print(f"Error ingesting {url}: {res['error']}", file=sys.stderr)
            continue
        results.append(res)

    print(json.dumps(results, ensure_ascii=False))

def cmd_assemble(args):
    """Assemble individual distillations and synthesis into a final batch report."""
    videos = []
    for fpath in args.distillations:
        with open(fpath, "r", encoding="utf-8") as f:
            videos.append(json.load(f))

    synthesis = None
    if args.synthesis:
        with open(args.synthesis, "r", encoding="utf-8") as f:
            synthesis = json.load(f)

    payload = {
        "BATCH_TITLE": args.title,
        "BATCH_VIDEOS_JSON": json.dumps(videos, ensure_ascii=False),
        "SYNTHESIS_JSON": json.dumps(synthesis, ensure_ascii=False) if synthesis else "null"
    }

    # Use the renderer's logic to build the full report
    render_batch_report.render(payload, args.output)
    print(f"Batch report rendered → {args.output}")

def cmd_manifest(args):
    """Assemble and render a batch report from a manifest JSON on stdin."""
    try:
        manifest = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"ERROR: invalid JSON manifest on stdin: {e}", file=sys.stderr)
        sys.exit(1)

    videos = manifest.get("distillations", [])
    synthesis = manifest.get("synthesis")
    title = manifest.get("title", "Batch Report")
    output = manifest.get("output")

    if not output:
        print("ERROR: 'output' path missing from manifest", file=sys.stderr)
        sys.exit(1)

    payload = {
        "BATCH_TITLE": title,
        "BATCH_VIDEOS_JSON": json.dumps(videos, ensure_ascii=False),
        "SYNTHESIS_JSON": json.dumps(synthesis, ensure_ascii=False) if synthesis else "null"
    }

    render_batch_report.render(payload, output)
    print(f"Batch report rendered (via manifest) → {output}")

def main():
    parser = argparse.ArgumentParser(description="Distillery Batch Orchestrator")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Ingest
    ing_p = subparsers.add_parser("ingest", help="Ingest multiple URLs")
    ing_p.add_argument("urls", nargs="+", help="YouTube URLs or IDs")

    # Assemble
    ass_p = subparsers.add_parser("assemble", help="Assemble and render a batch report")
    ass_p.add_argument("--title", required=True, help="Batch title")
    ass_p.add_argument("--output", required=True, help="Output .html path")
    ass_p.add_argument(
        "--distillations", nargs="+", required=True, help="Paths to Canonical Extraction JSON files"
    )
    ass_p.add_argument("--synthesis", help="Path to Synthesis JSON file")

    # Manifest
    subparsers.add_parser("manifest", help="Assemble and render from a JSON manifest on stdin")

    args = parser.parse_args()

    if args.command == "ingest":
        cmd_ingest(args)
    elif args.command == "assemble":
        cmd_assemble(args)
    elif args.command == "manifest":
        cmd_manifest(args)

if __name__ == "__main__":
    main()
