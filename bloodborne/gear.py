"""Gems and runes, the per-item gem slots, and what is worn. Layout notes in notes/format.md.

Between file offset 84 and the username the save keeps:
  * 40-byte records for every gem and rune: handle, id, type (1 gem, 2 rune), shape (gems) or category (runes), then effect ids,
    0xFFFFFFFF where there is none;
  * 60-byte blocks for every weapon and armor piece, keyed by the item's handle: key, id, durability, 0, 1, then five slots of
    (shape, handle of the gem fitted). A closed slot reads 0x80000000.
The worn items are eight handles at fixed distances from the username.
"""
from .container import u32
from .layout import Layout

GEM_START = 84
GEM = 40
BLOCK = 60
NONE = 0xFFFFFFFF
SHAPES = {1: "Radial", 2: "Triangle", 4: "Waning", 8: "Circle", 0x3F: "Droplet"}
CLOSED = 0x80000000
WEAPON_SLOTS = (389, 393, 397, 401)       # slots 1 to 4 in stored order; which is left or right hand is not known
ARMOR_SLOTS = (421, 425, 429, 433)        # head, chest, arms, legs: checked against the item types on a real save


def gems(data: bytes, lay: Layout) -> tuple[list[dict], int]:
    """Every gem and rune record, and the offset where they end."""
    out, pos = [], GEM_START
    while pos + GEM <= lay.username:
        first, second, kind, shape = (u32(data, pos + i) for i in (0, 4, 8, 12))
        if first >> 24 != 0xC0 or kind not in (1, 2):
            break
        eff = [u32(data, pos + 16 + 4 * i) for i in range(6)]
        out.append({"handle": first, "type": "gem" if kind == 1 else "rune", "shape": SHAPES.get(shape) if kind == 1 else None,
                    "category": shape if kind == 2 else None, "effects": [e for e in eff if e != NONE]})
        pos += GEM
    return out, pos


def blocks(data: bytes, lay: Layout, start: int) -> dict[int, dict]:
    """Gem slots per item, keyed by the item's first part (its handle). Skips the 0 / 0xFFFFFFFF filler between runs."""
    out, pos = {}, start
    while pos + BLOCK <= lay.username:
        w = [u32(data, pos + 4 * i) for i in range(5)]
        if w[0] >> 24 in (0x80, 0x90) and w[0] != CLOSED and w[4] == 1:
            slots = []
            for i in range(5):
                shape, gem = u32(data, pos + 20 + 8 * i), u32(data, pos + 24 + 8 * i)
                slots.append({"shape": "Closed" if shape == CLOSED else SHAPES.get(shape, f"{shape:#x}"), "gem": gem if shape != CLOSED and gem not in (0, NONE) else None})
            out[w[0]] = {"id": w[1], "slots": slots}
            pos += BLOCK
        else:
            pos += 8 if (w[0], w[1]) == (0, NONE) else 4
    return out


def worn(data: bytes, lay: Layout) -> dict[str, list[int]]:
    u = lay.username
    return {"weapons": [u32(data, u + o) for o in WEAPON_SLOTS], "armor": [u32(data, u + o) for o in ARMOR_SLOTS]}
