"""The game's event flag store, read from the save. Rules from a reverse-engineering of the engine
(hazeyxd23/bloodborne_pc_windows_port docs/party/event_flags.md) and checked here against the boss flags in bosses.py.

A flag id is decimal TAABZnnn: T type digit, AA area, B map block, Z zone, nnn the bit. The store is a pool of 1200 blocks
of 125 bytes (150,000 bytes) that the save holds whole, starting 377 bytes after the aob marker. Block key:
  global (area 0, block 0; ids 0 to 9999 and T0000Znnn for T in 1, 5, 6, 7):  index(T in 0 1 5 6 7) + Z * 5
  map (T in 1 5 6 7 9):  Z * 115 + 50 + 23 * index(T in 1 5 6 7 9) + index of (area, block) in MAPS
The bit is data[block * 125 + (nnn >> 3)] & (0x80 >> (nnn & 7)): the first flag of a byte is its top bit.
"""
from .layout import Layout

POOL_AFTER_AOB = 377
BLOCK = 125
POOL_BLOCKS = 1200
GLOBAL_TYPES = (0, 1, 5, 6, 7)
MAP_TYPES = (1, 5, 6, 7, 9)
MAPS = ((21, 0), (21, 1), (22, 0), (23, 0), (24, 0), (24, 1), (24, 2), (25, 0), (26, 0), (27, 0), (28, 0), (29, 0), (32, 0), (33, 0), (34, 0), (35, 0), (36, 0))


def locate(flag: int) -> tuple[int, int] | None:
    """(offset from the aob marker, bit mask) of an event flag, or None when the store has no block for it (chalice dungeons)."""
    t, area, block, zone, bit = flag // 10_000_000, flag // 100_000 % 100, flag // 10_000 % 10, flag // 1000 % 10, flag % 1000
    if flag < 10_000 or (area == 0 and block == 0):
        if t not in GLOBAL_TYPES:
            return None
        key = GLOBAL_TYPES.index(t) + (flag // 1000 if flag < 10_000 else zone) * 5
    else:
        if t not in MAP_TYPES or (area, block) not in MAPS:
            return None
        key = zone * 115 + 50 + 23 * MAP_TYPES.index(t) + MAPS.index((area, block))
    if key >= POOL_BLOCKS:
        return None
    return POOL_AFTER_AOB + key * BLOCK + (bit >> 3), 0x80 >> (bit & 7)


def is_set(data: bytes, lay: Layout, flag: int) -> bool | None:
    where = locate(flag)
    if where is None:
        return None
    off, mask = where
    return bool(data[lay.aob + off] & mask)
