# bloodborne-analyzer

Reads a decrypted Bloodborne character file and writes the character's level, stats and Blood Echoes as Markdown or JSON. Point it at a folder of snapshots and it writes the playthrough as a history instead.

```bash
python3 bb_to_md.py                               # the live bbport save
python3 bb_to_md.py userdata0000 -o save.md       # or .json
python3 bb_to_md.py /path/to/bb-snapshots -o history.md
python3 -m unittest discover -s tests
```

Python 3.10 or newer, standard library only.

## What it reads today

Name, level, the six stats, health, stamina, Blood Echoes and insight. A history across snapshots folds byte-identical copies together and reports any stat that drops. That is a small part of the file: 185 of 1,310,720 bytes. What is known and what is not is in `notes/format.md`.

## Saves

bbport and shadPS4 write decrypted saves. A PS4 save is encrypted per account and has to be decrypted first.

Licensed under Apache 2.0. See `LICENSE` and `NOTICE`.
