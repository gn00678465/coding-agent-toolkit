#!/usr/bin/env python3
"""Validate a Review Forge JSON artifact against its schema.

Usage: python3 -I validate.py <schema-name> <artifact.json>
       schema-name: scope | lane-review | lane-vote | summary | final-report

Exit codes: 0 valid, 1 invalid, 2 usage or unreadable input,
3 the jsonschema package is unavailable (check required fields by hand).
"""

import json
import sys
from pathlib import Path

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "assets" / "schemas"
NAMES = ("scope", "lane-review", "lane-vote", "summary", "final-report")


def main(argv: list[str]) -> int:
    if len(argv) != 3 or argv[1] not in NAMES:
        print(__doc__.strip(), file=sys.stderr)
        return 2

    try:
        from jsonschema import Draft202012Validator
        from referencing import Registry, Resource
        from referencing.jsonschema import DRAFT202012
    except ImportError:
        print("validator unavailable: pip install jsonschema", file=sys.stderr)
        return 3

    try:
        artifact = json.loads(Path(argv[2]).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"unreadable artifact: {exc}", file=sys.stderr)
        return 2

    registry = Registry()
    for path in SCHEMA_DIR.glob("*.schema.json"):
        schema = json.loads(path.read_text(encoding="utf-8"))
        registry = registry.with_resource(
            schema.get("$id", f"review-forge/{path.name}"),
            Resource.from_contents(schema, default_specification=DRAFT202012),
        )

    schema = json.loads((SCHEMA_DIR / f"{argv[1]}.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, registry=registry)
    errors = sorted(validator.iter_errors(artifact), key=lambda e: list(e.absolute_path))
    for error in errors:
        location = "/".join(str(p) for p in error.absolute_path) or "<root>"
        print(f"{location}: {error.message}")
    if errors:
        return 1
    print("valid")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
