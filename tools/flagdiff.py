#!/usr/bin/env python3
"""Which event flags turned on or off between two saves, decoded to flag ids and names.

  python3 tools/flagdiff.py older.userdata0000 newer.userdata0000

Offsets are relative to the aob marker. Each changed bit is mapped back through the flag store layout (bloodborne/flags.py) to its
flag id, and named when it is a lamp (db_bb/lamps.json) or a boss (bloodborne/bosses.py). The first 200 bytes (position, timers)
are skipped. Use it to find out what an event in the game changed.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from bloodborne import flags, layout  # noqa: E402
from bloodborne.bosses import BOSSES  # noqa: E402

SPAN = 150_000 + flags.POOL_AFTER_AOB


def reverse() -> dict[tuple[int, int], list[int]]:
    """(byte offset, mask) -> every flag id the store layout puts there."""
    out: dict[tuple[int, int], list[int]] = {}
    ids = list(range(10_000))
    for t in (1, 5, 6, 7):
        ids += [t * 10_000_000 + z * 1000 + n for z in range(10) for n in range(1000)]
    for t in flags.MAP_TYPES:
        for area, block in flags.MAPS:
            ids += [t * 10_000_000 + area * 100_000 + block * 10_000 + z * 1000 + n for z in range(10) for n in range(1000)]
    for i in ids:
        w = flags.locate(i)
        if w:
            out.setdefault(w, []).append(i)
    return out


def names() -> dict[int, str]:
    out = {}
    lamps = ROOT / "db_bb" / "lamps.json"
    if lamps.exists():
        out |= {x["flag"]: f"lamp: {x['name']}" for x in json.loads(lamps.read_text())}
    return out


def region(path):
    d = Path(path).read_bytes()
    lay = layout.find(d)
    if not lay:
        raise SystemExit(f"{path}: no character")
    return d[lay.aob:lay.aob + SPAN]


if __name__ == "__main__":
    a, b = region(sys.argv[1]), region(sys.argv[2])
    rev, nm = reverse(), names()
    boss = {w: n for n, fl in BOSSES for w in [(o, m) for o, m in fl]}
    n = 0
    for i, (x, y) in enumerate(zip(a, b)):
        if x == y or i < 200:
            continue
        for bit in range(8):
            m = 0x80 >> bit
            if (x ^ y) & m:
                n += 1
                ids = rev.get((i, m), [])
                label = ", ".join(f"{f}" + (f" ({nm[f]})" if f in nm else "") for f in ids[:3])
                # boss defeat bits are listed by name from the boss table
                tag = f" [boss: {boss[(i, m)]}]" if (i, m) in boss else ""
                print(f"aob+{i:<6} bit {m:#04x} {'on ' if y & m else 'off'}  {label or 'no flag id maps here'}{tag}")
    print(f"{n} flag bits changed")
