"""The 16-byte slot records of the inventory, the storage and the key-item list.

  byte 0       a handle (the slot's own number, wraps)
  bytes 4..8   first part: a handle for armor, weapons and gems; id + 0xB0 for goods
  bytes 8..12  second part: the thing itself (see decode)
  bytes 12..16 amount

An empty slot has 0xFFFFFFFF in the second part. Sources and checks in notes/format.md.
"""
from .container import u32
from .layout import SLOT

NONE = 0xFFFFFFFF
IMPRINTS = {10000: "Uncanny", 20000: "Lost"}


def decode(rec: bytes):
    """One slot as a dict, or None when it is empty."""
    first, second, amount = u32(rec, 4), u32(rec, 8), u32(rec, 12)
    if second == NONE or not (first or second):
        return None
    b7, b11 = rec[7], rec[11]
    out = {"handle": rec[0], "first": first, "amount": amount}
    if b7 == 0xB0 and b11 == 0x40:
        return {**out, "kind": "goods", "id": second & 0xFFFFFF}
    if b11 == 0x10:
        return {**out, "kind": "armor", "id": second & 0xFFFFFF}
    if b7 == 0xC0:
        return {**out, "kind": "gem", "id": second & 0xFFFFFF, "raw": second}
    if b7 == 0x80:
        level = (second % 10000) // 100
        imprint = IMPRINTS.get((second % 100000) - (second % 10000))
        base = second - level * 100 - {None: 0, "Uncanny": 10000, "Lost": 20000}[imprint]
        return {**out, "kind": "weapon", "id": base, "level": level, "imprint": imprint}
    return {**out, "kind": "unknown", "id": second, "raw": second}


def read(data: bytes, start: int, count: int) -> list[dict]:
    out = []
    for i in range(count):
        s = decode(data[start + i * SLOT:start + (i + 1) * SLOT])
        if s:
            out.append({"slot": i, **s})
    return out
