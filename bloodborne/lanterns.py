"""Lamps (lanterns) lit, from the event flag store. db_bb/lamps.json is generated from the game's own text by tools/gamefiles.py:
{"flag", "name"} per lamp, where the flag is 7AAB02nn and the name is event text 7000AABn. Hunter's Dream is not a lamp flag."""
import json
from functools import lru_cache
from pathlib import Path

from . import flags
from .layout import Layout

TABLE = Path(__file__).resolve().parent.parent / "db_bb" / "lamps.json"


@lru_cache(maxsize=1)
def table() -> list[dict]:
    return json.loads(TABLE.read_text(encoding="utf-8")) if TABLE.exists() else []


def read(data: bytes, lay: Layout, lamps: list[dict] | None = None) -> dict:
    lamps = table() if lamps is None else lamps
    return {"known": len(lamps), "lit": [x["name"] for x in lamps if flags.is_set(data, lay, x["flag"])]}
