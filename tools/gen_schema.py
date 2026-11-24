#!/usr/bin/env python3
"""Regenerate schema.json from the summary shape. Run after changing summarize(); tests/test_schema.py fails if it drifts."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bloodborne import summarize  # noqa: E402
from tests.test_saves import make_save  # noqa: E402


def shape(v):
    if isinstance(v, dict):
        return {"type": "object", "required": list(v), "properties": {k: shape(x) for k, x in v.items()}}
    if isinstance(v, bool):
        return {"type": "boolean"}
    if isinstance(v, int):
        return {"type": "integer"}
    return {"type": "string"}


if __name__ == "__main__":
    s = summarize(make_save(), "x")
    schema = {"$schema": "https://json-schema.org/draft/2020-12/schema", "title": "Bloodborne save summary",
              "oneOf": [shape(s), {"type": "object", "required": ["file", "size", "empty", "integrity"]}]}
    Path(__file__).resolve().parent.parent.joinpath("schema.json").write_text(json.dumps(schema, indent=1) + "\n")
