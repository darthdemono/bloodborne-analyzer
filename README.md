# bloodborne-analyzer

Reads a decrypted Bloodborne character file and writes the character, its inventory, storage, key items and boss flags as Markdown or JSON. Point it at a folder of snapshots and it writes the playthrough as a history instead.

```bash
python3 bb_to_md.py                               # the live bbport save
python3 bb_to_md.py userdata0000 -o save.md       # or .json
python3 bb_to_md.py /path/to/bb-snapshots -o history.md
python3 bb_to_md.py --validate /path/to/saves     # does each save add up; exit 1 on a finding
python3 -m unittest discover -s tests
```

Python 3.10 or newer, standard library only.

## The web app

`index.html` and `app/*.js` are a port of the reader that runs in the page: drop a `userdata0000` or a whole folder of snapshots and it renders the same report, with Markdown and JSON downloads. Nothing is uploaded. Serve it from this folder (`python3 -m http.server <free port> --bind 127.0.0.1`), because the game tables are fetched from `db_bb/`. A port drifts silently, so `node tools/parity.mjs <folder|save>...` runs both readers on the same saves and compares the summary (value and key order), the Markdown byte for byte, the validation and the history. It passes on all 130 saves and backups on the author's machine, and `tests/test_web.py` runs it on synthetic saves.

## What it reads today

Name, level, the six stats, health, stamina, Blood Echoes, insight, play time, deaths, New Game cycle, the full inventory, storage and key-item lists with the game's own item names, worn weapons and armor, every blood gem and rune with its effects and what it is fitted to, the gem slots of each weapon and armor piece, and 22 boss flags. Lanterns are read from a table you calibrate from your own play (`tools/flagdiff.py --add`). A history across snapshots folds byte-identical copies together, shows play time and deaths, lists the gear and items that appeared between snapshots, and reports a stat that drops or play time that goes back (an older save was restored). `--validate` checks that the level matches the stats and the values are in range.

Names are read from the game: `python3 tools/gamefiles.py names <game>/dvdroot_ps4/msg/engus db_bb` writes `db_bb/names.json` from your own install. Without it the report shows ids.

Not read yet: map position, appearance, lanterns until calibrated and most event flags. What is known and what is not is in `notes/format.md`, and what is left against sl2-analyzer is in `notes/roadmap.md`.

## Saves

bbport and shadPS4 write decrypted saves. A PS4 save is encrypted per account and has to be decrypted first.

Licensed under Apache 2.0. See `LICENSE` and `NOTICE`.
