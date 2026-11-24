#!/usr/bin/env python3
"""Which flag bits turned on or off between two saves, aligned by the aob anchor.

  python3 tools/flagdiff.py older.userdata0000 newer.userdata0000 [--span 40000]

  python3 tools/flagdiff.py older newer --add "Central Yharnam"   # if exactly one bit turned on, add it to db_bb/lanterns.json

Use it to calibrate an event: BB-Save, do one thing in the game (light a lantern, kill a boss, open a shortcut), BB-Save,
then diff the two snapshots. Offsets are relative to the aob marker, the same as bloodborne/bosses.py.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bloodborne import layout  # noqa: E402


def region(path, span):
    d = Path(path).read_bytes()
    lay = layout.find(d)
    if not lay:
        raise SystemExit(f"{path}: no character")
    return d[lay.aob:lay.aob + span]


def diff(a: bytes, b: bytes, skip_below: int = 200):
    out = []
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y and i >= skip_below:     # the first 200 bytes are volatile (position, timers)
            out.append((i, x, y, y & ~x, x & ~y))
    return out


if __name__ == "__main__":
    span = int(sys.argv[sys.argv.index("--span") + 1]) if "--span" in sys.argv else 40000
    a, b = region(sys.argv[1], span), region(sys.argv[2], span)
    rows = diff(a, b)
    if "--add" in sys.argv:
        name = sys.argv[sys.argv.index("--add") + 1]
        new = [(i, on) for i, x, y, on, off in rows if on]
        bits = [(i, on & -on, on) for i, on in new if bin(on).count("1") == 1]
        if len(new) != 1 or len(bits) != 1:
            raise SystemExit(f"{len(new)} flag bytes turned on ({sum(bin(on).count('1') for _, on in new)} bits): not one clean bit, so nothing was added. "
                             "Light one lantern between the two saves and nothing else.")
        path = Path(__file__).resolve().parent.parent / "db_bb" / "lanterns.json"
        import json
        table = json.loads(path.read_text()) if path.exists() else []
        table = [e for e in table if e["name"] != name] + [{"name": name, "offset": bits[0][0], "mask": bits[0][1]}]
        path.write_text(json.dumps(table, indent=1, ensure_ascii=False) + "\n")
        raise SystemExit(f"added {name}: aob+{bits[0][0]} mask {bits[0][1]:#04x} ({len(table)} lanterns calibrated)")
    print(f"{len(rows)} bytes changed")
    for i, x, y, on, off in rows:
        print(f"aob+{i:<6} {x:02x} -> {y:02x}   bits on {on:#04x}  bits off {off:#04x}")
