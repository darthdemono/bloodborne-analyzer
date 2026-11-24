#!/usr/bin/env python3
"""Read Bloodborne's own message files (item.msgbnd.dcx) and write the name tables the analyzer ships in db_bb/.

  python3 tools/gamefiles.py list  <msg dir>/engus         # the FMG tables inside item.msgbnd.dcx
  python3 tools/gamefiles.py names <msg dir>/engus db_bb   # write db_bb/names.json

The DCX / BND4 / FMG readers are the minimal ones from sl2-analyzer's tools, kept here so this repo stays standalone.
Names are never typed by hand: they are read from the install.
"""
import json
import re
import struct
import sys
import zlib
from pathlib import Path


def dcx(data: bytes) -> bytes:
    if data[:4] != b"DCX\0":
        return data
    if data[0x28:0x2C] != b"DFLT":
        raise ValueError(f"DCX compression {data[0x28:0x2C]!r} is not zlib; Bloodborne's message files are DFLT")
    dca = data.index(b"DCA\0")
    return zlib.decompress(data[dca + int.from_bytes(data[dca + 4:dca + 8], "big"):])


def bnd(data: bytes) -> list[tuple[int, str, bytes]]:
    """(id, name, bytes) for every file of a BND4 (the format of *.msgbnd)."""
    data = dcx(data)
    if data[:4] != b"BND4":
        raise ValueError(f"not a BND4 ({data[:4]!r})")
    e = ">" if data[0x09] else "<"
    count = struct.unpack_from(e + "i", data, 0x0C)[0]
    header = struct.unpack_from(e + "q", data, 0x10)[0]
    stride = struct.unpack_from(e + "q", data, 0x20)[0]
    unicode_names, fmt = data[0x30], data[0x31]
    out = []
    for n in range(count):
        p = header + n * stride
        size = struct.unpack_from(e + "q", data, p + 0x08)[0]
        off_at = 0x18 if fmt & 0x20 else 0x10
        offset, file_id, name_off = struct.unpack_from(e + "Iii", data, p + off_at)
        name = ""
        if name_off:
            if unicode_names:
                end = data.find(b"\0\0", name_off)
                while (end - name_off) % 2:
                    end = data.find(b"\0\0", end + 1)
                name = data[name_off:end].decode("utf-16-le", "replace")
            else:
                name = data[name_off:data.find(b"\0", name_off)].decode("shift_jis", "replace")
        out.append((file_id, name, data[offset:offset + size]))
    return out


def fmg(blob: bytes) -> dict[int, str]:
    e = ">" if blob[1] else "<"
    wide = blob[2] == 2
    groups = struct.unpack_from(e + "i", blob, 0x0C)[0]
    if wide:
        str_off, at, stride = struct.unpack_from(e + "q", blob, 0x18)[0], 0x28, 16
    else:
        str_off, at, stride = struct.unpack_from(e + "i", blob, 0x14)[0], 0x1C, 12
    out = {}
    for _ in range(groups):
        idx, first, last = struct.unpack_from(e + "iii", blob, at)
        at += stride
        for j in range(last - first + 1):
            o = str_off + (idx + j) * (8 if wide else 4)
            so = struct.unpack_from(e + ("q" if wide else "i"), blob, o)[0]
            if so:
                end = blob.find(b"\0\0", so)
                while (end - so) % 2:
                    end = blob.find(b"\0\0", end + 1)
                out[first + j] = blob[so:end].decode("utf-16-le", "replace")
    return out


def tables(msg_dir: Path, bundle: str = "item") -> dict[str, dict[int, str]]:
    p = msg_dir / f"{bundle}.msgbnd.dcx"
    return {Path(name.replace("\\", "/")).stem: fmg(blob) for _, name, blob in bnd(p.read_bytes())}


if __name__ == "__main__":
    cmd, msg = sys.argv[1], Path(sys.argv[2])
    t = tables(msg)
    if cmd == "list":
        for k, v in sorted(t.items()):
            print(f"{k:34}{len(v):6} entries, e.g. {next(iter(v.items()), None)}")
    elif cmd == "names":
        out = Path(sys.argv[3])
        out.mkdir(exist_ok=True)
        keep = {"goods": "アイテム名", "weapons": "武器名", "armor": "防具名"}   # the FMG tables are named in Japanese: item, weapon, protector
        junk = re.compile(r"^(\*|NOT NEEDED|%null%|en\d+|\s*)$")   # unused rows the game ships as placeholders
        res = {k: {str(i): s for i, s in t.get(v, {}).items() if not junk.match(s)} for k, v in keep.items()}
        (out / "names.json").write_text(json.dumps(res, ensure_ascii=False, indent=0, sort_keys=True))
        eff = {str(i): x for i, x in tables(msg, "menu").get("魔石効果", {}).items() if not junk.match(x)}   # the gem effect texts, in menu.msgbnd
        (out / "gem_effects.json").write_text(json.dumps(eff, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        print({k: len(v) for k, v in res.items()}, {"gemEffects": len(eff)})
