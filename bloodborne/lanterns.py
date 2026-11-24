"""Lanterns lit, from a calibration table: db_bb/lanterns.json is a list of {"name", "offset", "mask"}, the offset from the aob marker.

The game data does not say which save bit belongs to which lantern, so the table is built from your own play with
tools/flagdiff.py --add "Lantern name" older newer: BB-Save, light ONE lantern, BB-Save, run it. A lantern that is not
in the table is simply not reported, never reported as unlit.
"""
import json
from functools import lru_cache
from pathlib import Path

from .layout import Layout

TABLE = Path(__file__).resolve().parent.parent / "db_bb" / "lanterns.json"


@lru_cache(maxsize=1)
def table() -> list[dict]:
    return json.loads(TABLE.read_text(encoding="utf-8")) if TABLE.exists() else []


def read(data: bytes, lay: Layout, entries: list[dict] | None = None) -> dict:
    entries = table() if entries is None else entries
    lit = [e["name"] for e in entries if (data[lay.aob + e["offset"]] & e["mask"]) == e["mask"]]
    return {"calibrated": len(entries), "lit": lit}
