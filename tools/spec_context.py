#!/usr/bin/env python3
"""Select checkout-local Spec Kit context without guessing a Git branch."""
import argparse
import json
from pathlib import Path
import re


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("feature", help="Feature directory name, e.g. 004-spec-kit-integration")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    feature = root / "specs" / args.feature
    if not re.fullmatch(r"\d{3}-[a-z0-9-]+", args.feature) or not feature.is_dir():
        parser.error("Use an existing feature directory name under specs/, without a path prefix")
    if not feature.resolve().is_relative_to(root / "specs"):
        parser.error("Feature must stay inside specs/")
    pointer = root / ".specify/feature.json"
    temporary = pointer.with_suffix(".json.tmp")
    temporary.write_text(json.dumps({"feature_directory": f"specs/{args.feature}"}) + "\n", encoding="utf-8")
    temporary.replace(pointer)
    print(f"Selected specs/{args.feature}")


if __name__ == "__main__":
    main()
