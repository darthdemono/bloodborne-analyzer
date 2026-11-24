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
| Inventory, storage, key items | done | named from the game's own message files; equipped gear not yet |
| Gems and runes, gem slots | done | shape, effects named from the game, which weapon or armor each is fitted to |
| Equipped gear | done | worn weapons (stored order) and armor |
| Bosses defeated | done | 22 flags read; Father Gascoigne confirmed by a real kill, the other 21 not yet seen |
| Lanterns lit | calibration workflow | `tools/flagdiff.py --add` records a lantern from two snapshots; none calibrated yet |
| Areas, NPC states | blocked | flags not located |
| Play time, deaths, NG cycle | done | play time also exposes restored saves in the history |
| Map position | blocked | the editor reads coordinates by a pattern; not located here |
| Item names from the game's own files (`tools/gamefiles.py`) | done | goods, weapons, armor; origin names and gem effects still to do |
| Progress inference with "a floor" wording | blocked | needs flags |
| Timeline charts | not started | needs more than six numbers per snapshot to be worth drawing |
| Owner account check | not applicable | a PS4 save is bound to an account id, but the decrypted bbport files carry none |
| Save editing (steam id swap, slot clearing) | not applicable | BB-Recover and BB-Save in the pwsh profile cover safe restore; writing stats is out of scope |

## What is left

The stream is read by anchors, not parsed end to end, and that works for everything above. Still open, in order of value: equipped gear and gems (the 60-byte equipment blocks and 40-byte gem records), lanterns and other event flags (find them by diffing snapshots taken around one event, as the boss flags will be confirmed), map position, appearance and origin names, then the browser app and its parity gate.
