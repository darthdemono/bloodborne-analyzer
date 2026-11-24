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

## What it reads today

Name, level, the six stats, health, stamina, Blood Echoes, insight, play time, deaths, New Game cycle, the full inventory, storage and key-item lists with the game's own item names, and 22 boss flags. A history across snapshots folds byte-identical copies together, shows play time and deaths, lists the gear and items that appeared between snapshots, and reports a stat that drops or play time that goes back (an older save was restored). `--validate` checks that the level matches the stats and the values are in range.

Names are read from the game: `python3 tools/gamefiles.py names <game>/dvdroot_ps4/msg/engus db_bb` writes `db_bb/names.json` from your own install. Without it the report shows ids.

Not read yet: gem effects, equipped gear, map position, appearance and most event flags. What is known and what is not is in `notes/format.md`, and what is left against sl2-analyzer is in `notes/roadmap.md`.

## Saves

bbport and shadPS4 write decrypted saves. A PS4 save is encrypted per account and has to be decrypted first.

Licensed under Apache 2.0. See `LICENSE` and `NOTICE`.
