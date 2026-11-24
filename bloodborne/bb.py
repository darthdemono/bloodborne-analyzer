"""summarize(): everything the writers show is computed here, as one JSON-able dict."""
from pathlib import Path

from .container import BLOCK_LEN, check, find_block, read, u32

# offsets inside the character block, validated against 6 real snapshots (level climbs 10 to 16 with vigor 12 to 16, name "Joy")
STATS = {"vigor": 48, "endurance": 56, "strength": 72, "skill": 80, "bloodtinge": 88, "arcane": 96}
BASE_LEVEL_SUM = 50      # level = sum of the six stats - 50: 66 - 50 = 16, 60 - 50 = 10, both seen in the real saves


def summarize(path_or_bytes, name: str = "") -> dict:
    data = check(bytes(path_or_bytes)) if isinstance(path_or_bytes, (bytes, bytearray)) else read(path_or_bytes)
    off = find_block(data)
    out = {"file": name or (Path(path_or_bytes).name if not isinstance(path_or_bytes, (bytes, bytearray)) else ""), "size": len(data), "empty": off is None}
    if off is None:
        out["integrity"] = {"fileBytes": len(data), "decodedBytes": 0, "note": "no character in this slot"}
        return out
    b = data[off:off + BLOCK_LEN]
    stats = {k: b[o] for k, o in STATS.items()}
    level = u32(b, 128)
    out["character"] = {
        "name": b[-33:].replace(b"\0", b"").decode("latin-1"),
        "level": level,
        "levelFromStats": sum(stats.values()) - BASE_LEVEL_SUM,
        "stats": stats,
        "health": u32(b, 8),
        "stamina": u32(b, 32),
        "bloodEchoes": u32(b, 132),
        "insight": u32(b, 116),
    }
    out["integrity"] = {
        "fileBytes": len(data),
        "blockOffset": off,
        "decodedBytes": BLOCK_LEN,
        "note": "only the character block is decoded; inventory, gems, play time, bosses and map state are not read yet (notes/format.md)",
    }
    return out
