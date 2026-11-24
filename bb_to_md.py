#!/usr/bin/env python3
"""Bloodborne save -> Markdown or JSON. One file gives a report, several files or folders give a combined history.

  python3 bb_to_md.py                                 # the live save on this machine
  python3 bb_to_md.py userdata0000 -o x.md|x.json
  python3 bb_to_md.py dir1 dir2 f -o out.md           # combined history (--combined forces it for one file)
"""
import argparse
import json
import sys
from pathlib import Path

from bloodborne import BloodborneError, summarize
from bloodborne.combine import collect, history, render_history
from bloodborne.render import render
from bloodborne.validate import validate

LIVE = Path.home() / ".local/share/bbport/user/savedata/1/CUSA00900/SPRJ0005/userdata0000"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="*")
    ap.add_argument("-o", "--out")
    ap.add_argument("--combined", action="store_true")
    ap.add_argument("--validate", action="store_true", help="check that each save adds up; exit 1 on any finding")
    a = ap.parse_args()
    paths = a.paths or [str(LIVE)]
    files = collect(paths)
    if a.validate:
        bad = 0
        for f in files:
            try:
                found = validate(summarize(f))
            except BloodborneError as e:
                found = [str(e)]
            for line in found:
                print(f"{f}: {line}")
            bad += bool(found)
        print(f"{len(files)} files checked, {bad} with findings")
        return 1 if bad else 0
    as_json = bool(a.out) and a.out.endswith(".json")
    if len(files) > 1 or a.combined or any(Path(p).is_dir() for p in paths):
        h = history(paths)
        text = json.dumps(h, indent=1) if as_json else render_history(h)
    else:
        try:
            s = summarize(files[0])
        except BloodborneError as e:
            print(f"{files[0]}: {e}", file=sys.stderr)
            return 1
        text = json.dumps(s, indent=1) if as_json else render(s)
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
