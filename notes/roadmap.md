# Roadmap against sl2-analyzer

Each feature of `~/Code/sl2-analyzer`, and where Bloodborne stands. "Blocked" means the save fields are not decoded yet, so there is nothing to show; the blocker is the format reader, not the UI.

| sl2-analyzer feature | Bloodborne | Notes |
|---|---|---|
| Markdown report for one save | done | name, level, stats, health, stamina, echoes, insight |
| JSON output + `schema.json` | done | `tools/gen_schema.py`, `tests/test_schema_validate.py` |
| Combined history of a folder | done | folds identical copies, reports a stat that drops |
| `--validate` ("does this save add up") | done | level rule, stat range, name, health |
| Tests on real saves | done | level = stat sum - 50 on every snapshot |
| Browser app + parity gate (`app/*.js`, `tools/parity.mjs`) | not started | can start now on the fields above, then grow with the reader |
| Derived stats (HP, stamina, damage from attributes) | partial | health and stamina are read from the save; the formulas need the game's param tables |
| Inventory, storage, equipped gear | blocked | save is a serialized object stream, records not located |
| Gems and runes | blocked | the public editor finds them by pattern (80-byte records) |
| Bosses defeated, lanterns lit, areas | blocked | event flags not located |
| Play time, NG+ cycle, location | blocked | not located |
| Item names from the game's own files (`tools/gamefiles.py`) | not started | names live in `dvdroot_ps4/msg` under the game folder; DCX/BND readers already exist in sl2-analyzer |
| Progress inference with "a floor" wording | blocked | needs flags |
| Timeline charts | not started | needs more than six numbers per snapshot to be worth drawing |
| Owner account check | not applicable | a PS4 save is bound to an account id, but the decrypted bbport files carry none |
| Save editing (steam id swap, slot clearing) | not applicable | BB-Recover and BB-Save in the pwsh profile cover safe restore; writing stats is out of scope |

## The one blocker

Everything marked blocked waits on one thing: a reader for the serialized stream (tag words such as `c08002b2`, variable-length records). A raw diff of two snapshots changes 245,000 of 327,680 words because a change early in the file shifts everything after it, so the structure has to be parsed, not diffed. Order of attack: parse the tag/length framing, locate the character block by structure instead of the table pattern, then find the inventory by diffing records between saves where one item was bought or used.
