"""summarize(): everything the writers show is computed here, as one JSON-able dict."""
import json
from functools import lru_cache
from pathlib import Path

from . import gear, lanterns, layout, records
from .bosses import BOSSES
from .container import check, read, u32

# distances from the username (layout.py); u32 unless noted
STATS = {"vigor": -103, "endurance": -95, "strength": -79, "skill": -71, "bloodtinge": -63, "arcane": -55}
BASE_LEVEL_SUM = 50      # level = sum of the six stats - 50, true on every real save
HEADER = 12              # loaded map and play time, the only fixed absolute offsets


@lru_cache(maxsize=1)
def names() -> dict:
    """Item, weapon and armor names read from the game by tools/gamefiles.py; empty when db_bb/ was not generated."""
    p = Path(__file__).resolve().parent.parent / "db_bb" / "names.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


@lru_cache(maxsize=1)
def gem_effects() -> dict:
    p = Path(__file__).resolve().parent.parent / "db_bb" / "gem_effects.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _label(item: dict) -> str:
    n = item.get("name") or f"unnamed {item['kind']} {item['id']}"
    if item["kind"] == "weapon":
        n += (f" +{item['level']}" if item["level"] else "") + (f" ({item['imprint']})" if item["imprint"] else "")
    return n


def _gear(data: bytes, lay, inv: dict) -> tuple[list, dict]:
    """Gems and runes with what they are fitted to, the gem slots on each weapon and armor piece, and the worn items."""
    gems, end = gear.gems(data, lay)
    table = gem_effects()
    by_handle = {}
    for g in gems:
        g["effects"] = [{"id": e, "text": table.get(str(e), "")} for e in g["effects"]]
        g["fittedTo"] = None
        by_handle[g["handle"]] = g
    blocks = gear.blocks(data, lay, end)
    items = {}
    for grp in ("weapons", "armor"):
        for it in inv[grp]:
            items[it["first"]] = it
            b = blocks.get(it["first"])
            it["gemSlots"] = [{"shape": sl["shape"], "gem": sl["gem"]} for sl in b["slots"]] if b else []
            for sl in it["gemSlots"]:
                if sl["gem"] in by_handle:
                    by_handle[sl["gem"]]["fittedTo"] = _label(it)
    w = gear.worn(data, lay)
    worn = {k: [_label(items[h]) if h in items else None for h in v] for k, v in w.items()}
    return gems, worn


def _named(slots: list[dict]) -> list[dict]:
    table = names()
    for s in slots:
        s["name"] = table.get({"goods": "goods", "weapon": "weapons", "armor": "armor"}.get(s["kind"], ""), {}).get(str(s["id"]), "")
    return slots


def _name(data: bytes, user: int) -> str:
    raw = data[user + 1:user + 33]
    return raw.decode("utf-16le", errors="replace").split("\0")[0]


def _grouped(slots: list[dict]) -> dict:
    slots = _named(slots)
    out = {"goods": [], "armor": [], "weapons": [], "gems": [], "other": []}
    for s in slots:
        out[{"goods": "goods", "armor": "armor", "weapon": "weapons", "gem": "gems"}.get(s["kind"], "other")].append(s)
    return out


def summarize(path_or_bytes, name: str = "") -> dict:
    data = check(bytes(path_or_bytes)) if isinstance(path_or_bytes, (bytes, bytearray)) else read(path_or_bytes)
    lay = layout.find(data)
    out = {"file": name or (Path(path_or_bytes).name if not isinstance(path_or_bytes, (bytes, bytearray)) else ""), "size": len(data), "empty": lay is None}
    if lay is None:
        out["integrity"] = {"fileBytes": len(data), "decodedBytes": 0, "note": "no character in this slot"}
        return out
    u = lay.username
    g = lambda off: u32(data, u + off)
    stats = {k: g(o) for k, o in STATS.items()}
    play_ms = u32(data, 8)
    out["header"] = {"loadedMap": f"{u32(data, 4):#010x}", "playtimeMs": play_ms, "playtime": f"{play_ms // 3600000}:{play_ms // 60000 % 60:02d}:{play_ms // 1000 % 60:02d}"}
    out["character"] = {
        "name": _name(data, u),
        "level": g(-23),
        "levelFromStats": sum(stats.values()) - BASE_LEVEL_SUM,
        "stats": stats,
        "health": {"current": g(-147), "withBuffs": g(-143), "base": g(-139)},
        "stamina": {"current": g(-119), "withBuffs": g(-115), "base": g(-111)},
        "bloodEchoes": g(-19),
        "insight": g(-35),
        "gender": data[u + 35], "voice": data[u + 36], "origin": data[u + 39],
        "newGameCycle": data[u + 68831],
        "deaths": u32(data, lay.aob + 360),
    }
    out["inventory"] = _grouped(records.read(data, lay.inventory, layout.INV_SLOTS))
    out["gems"], out["equipped"] = _gear(data, lay, out["inventory"])
    out["storage"] = _grouped(records.read(data, lay.storage, layout.STORAGE_SLOTS))
    out["keyItems"] = _grouped(records.read(data, lay.key, layout.KEY_SLOTS))
    flags = {n: all((data[lay.aob + off] & mask) == mask for off, mask in fl) for n, fl in BOSSES}
    out["lanterns"] = lanterns.read(data, lay)
    out["bosses"] = {"tracked": len(BOSSES), "defeated": [n for n, dead in flags.items() if dead]}
    decoded = HEADER + 185 + (layout.INV_SLOTS + layout.STORAGE_SLOTS + layout.KEY_SLOTS) * layout.SLOT + len(BOSSES) * 1
    out["integrity"] = {
        "fileBytes": len(data),
        "username": u, "inventory": lay.inventory, "storage": lay.storage, "keyItems": lay.key, "flags": lay.aob,
        "decodedBytes": decoded,
        "note": "gem effects, equipped gear, map position, appearance and most event flags are not read yet (notes/format.md)",
    }
    return out
