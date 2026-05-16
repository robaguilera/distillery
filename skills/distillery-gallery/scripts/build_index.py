#!/usr/bin/env python3
"""Thin CLI wrapper around knowledge_base.rebuild().

Usage: python3 build_index.py --dir DIR [--output DIR]

All logic lives in knowledge_base.py.  The --output flag is accepted for
backward compatibility but ignored (manifest.json is always written to --dir).
"""
import argparse
import importlib.util
import pathlib
import sys


def _load_knowledge_base():
    spec = importlib.util.spec_from_file_location(
        "knowledge_base", pathlib.Path(__file__).parent / "knowledge_base.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    parser = argparse.ArgumentParser(description="Build distillery manifest.json")
    parser.add_argument("--dir", required=True, help="Directory containing distillery HTML reports")
    parser.add_argument("--output", help="Ignored — kept for backward compatibility")
    args = parser.parse_args()

    kb = _load_knowledge_base()
    kb.rebuild(args.dir)


if __name__ == "__main__":
    main()
