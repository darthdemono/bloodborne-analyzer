# Bloodborne decrypted save format

What is known, how it was checked, and what is not read yet.

## Files

`<savedata>/1/<CUSA id>/SPRJ0005/` holds `userdata0000` to `userdata0009` (one character each, 1,310,720 bytes) and `userdata0010` (settings, 262,144 bytes), plus `backup0000` / `backup0010` written by the game before each save. On this machine: `~/.local/share/bbport/user/savedata/1/CUSA00900/SPRJ0005/`. A real PS4 save is encrypted and must be decrypted first (Save Wizard, a jailbroken console); bbport and shadPS4 store it decrypted.

An unused slot is all zeros. The file starts `41 00 00 00`; the next four bytes differ between saves, so only the first four are checked.

## The character block (decoded)

Located by a table of 25 records, 16 bytes each, whose first byte counts 0x41 to 0x59. The block starts 636 bytes before the first record and the decoded part is 185 bytes. Offsets inside it:

| Offset | Size | Field |
|---|---|---|
| 8 | u32 | health (also at 16 and 24, which do not always match) |
| 32 | u32 | stamina (also at 40 and 48) |
| 48 | u8 | vigor |
| 56 | u8 | endurance |
| 72 | u8 | strength |
| 80 | u8 | skill |
| 88 | u8 | bloodtinge |
| 96 | u8 | arcane |
| 116 | u32 | insight |
| 128 | u32 | level |
| 132 | u32 | Blood Echoes carried |
| last 33 | ASCII, zero padded | character name |

**Check that holds on every real save:** level = vigor + endurance + strength + skill + bloodtinge + arcane - 50. Six snapshots, level 10 to 16, all agree.

## Sources

The table-and-offset layout is from the public editor `rakesh37187/BBSaveEditor` (`process_save_file.py`, `user.py`), read as documentation only; no code was copied. Every offset was then re-checked against this machine's own snapshots, which is why the table above lists only fields that moved sensibly across them. The reference says its author "used some weird method to find certain memory places": the table anchor is a heuristic, not a parsed header.

## Not read yet

The file is a serialized object stream (tags such as `c08002b2`), not a flat struct. Still undecoded, in rough order of value: play time, inventory and storage, weapons and armor, gems (the reference finds them by pattern, 80-byte records, effect ids that need the game's message tables for names), boss and lantern flags, NG+ cycle, current location. The names must come from the game's own message files (`dvdroot_ps4/msg` under the game folder), never from a hand-typed table. `integrity.decodedBytes` in the summary says honestly how little is read: 185 of 1,310,720 bytes today.
