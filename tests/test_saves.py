import struct
import tempfile
import unittest
from pathlib import Path

from bloodborne import BloodborneError, summarize
from bloodborne.bb import _label
from bloodborne.combine import history, stamp
from bloodborne.container import MAGIC, SIZE

SNAPSHOTS = Path("/mnt/nobara-data/Backup/user/bb-snapshots")


USER = 40000


def slot(kind, id_, amount=1, handle=0x40):
    """One 16-byte inventory record, as the game writes it."""
    if kind == "goods":
        return struct.pack("<BxxxIII", handle, id_ | 0xB0000000, id_ | 0x40000000, amount)
    if kind == "armor":
        return struct.pack("<BxxxIII", handle, 0x90800000 | handle, id_ | 0x10000000, amount)
    return struct.pack("<BxxxIII", handle, 0x80800000 | handle, id_, amount)


def make_save(name="Joy", vig=16, end=13, st=15, skl=9, blt=6, arc=7, echoes=181, insight=1, play_ms=14181860, deaths=12,
              inventory=(), storage=(), keys=(), defeated=(), gems=(), blocks=(), worn_weapons=(), worn_armor=()) -> bytes:
    """A synthetic character file laid out by the same anchors the reader uses: FACE, the inventory 34028 bytes before it,
    the username 469 before that, the aob marker 68545 after the username."""
    d = bytearray(SIZE)
    d[:len(MAGIC)] = MAGIC
    struct.pack_into("<I", d, 8, play_ms)
    inv = USER + 469
    d[inv + 34028:inv + 34032] = b"FACE"
    aob = USER + 68545
    d[aob:aob + 8] = bytes.fromhex("0300000005000100")
    stats = [vig, end, st, skl, blt, arc]
    for off, v in zip((-103, -95, -79, -71, -63, -55), stats):
        struct.pack_into("<I", d, USER + off, v)
    struct.pack_into("<I", d, USER - 23, sum(stats) - 50)
    struct.pack_into("<I", d, USER - 19, echoes)
    struct.pack_into("<I", d, USER - 35, insight)
    for off, v in ((-147, 698), (-143, 698), (-139, 698), (-119, 97), (-115, 97), (-111, 97)):
        struct.pack_into("<I", d, USER + off, v)
    d[USER + 1:USER + 33] = name.encode("utf-16le").ljust(32, b"\0")
    struct.pack_into("<I", d, aob + 360, deaths)
    for region, items in ((inv, inventory), (inv + 34268, storage), (USER + 32201, keys)):
        for k in range(1984 if region != USER + 32201 else 128):
            struct.pack_into("<I", d, region + k * 16 + 8, 0xFFFFFFFF)   # every slot starts empty
        for k, rec in enumerate(items):
            d[region + k * 16:region + k * 16 + 16] = rec
    pos = 84
    for g in gems:                     # (handle, kind 1 gem / 2 rune, shape, effect ids)
        eff = list(g[3]) + [0xFFFFFFFF] * (6 - len(g[3]))
        struct.pack_into("<IIII6I", d, pos, g[0], 0x80010000 | (g[0] & 0xFFFF), g[1], g[2], *eff)
        pos += 40
    for key, ident, slots in blocks:   # slots: five (shape, gem handle)
        struct.pack_into("<IIIII", d, pos, key, ident, 0, 0, 1)
        for i, (shape, gem) in enumerate(list(slots) + [(0x80000000, 0)] * (5 - len(slots))):
            struct.pack_into("<II", d, pos + 20 + 8 * i, shape, gem)
        pos += 60
    for off, handles in ((389, worn_weapons), (421, worn_armor)):
        for i, h in enumerate(handles):
            struct.pack_into("<I", d, USER + off + 4 * i, h)
    from bloodborne.bosses import BOSSES
    for n, flags in BOSSES:
        if n in defeated:
            for off, mask in flags:
                d[aob + off] |= mask
    return bytes(d)


class Synthetic(unittest.TestCase):
    def test_character_block(self):
        c = summarize(make_save(), "x")["character"]
        self.assertEqual((c["name"], c["level"], c["levelFromStats"], c["bloodEchoes"], c["insight"]), ("Joy", 16, 16, 181, 1))
        self.assertEqual(c["stats"], {"vigor": 16, "endurance": 13, "strength": 15, "skill": 9, "bloodtinge": 6, "arcane": 7})

    def test_empty_slot_is_valid(self):
        self.assertTrue(summarize(bytes(SIZE), "z")["empty"])

    def test_wrong_files_are_refused(self):
        with self.assertRaises(BloodborneError):
            summarize(b"x" * 100)
        with self.assertRaises(BloodborneError):
            summarize(bytes(0x40000))          # userdata0010, the settings file

    def test_history_folds_copies_and_flags_a_drop(self):
        with tempfile.TemporaryDirectory() as t:
            for name, kw in (("BB_2026-01-01_10-00-00", {}), ("BB_2026-01-02_10-00-00", {}), ("BB_2026-01-03_10-00-00", {"vig": 12})):
                p = Path(t, name, "SPRJ0005")
                p.mkdir(parents=True)
                (p / "userdata0000").write_bytes(make_save(**kw))
            h = history([t])
            self.assertEqual(len(h["snapshots"]), 2)           # the first two files are byte-identical
            self.assertEqual(h["snapshots"][0]["copies"], 2)
            self.assertTrue(any("vigor dropped" in n for n in h["notes"]))

    def test_stamp_reads_the_snapshot_folder_name(self):
        self.assertEqual(stamp(Path("BB_2026-11-24_12-45-04/SPRJ0005/userdata0000")).isoformat(), "2026-11-24T12:45:04")


class Gear(unittest.TestCase):
    def build(self):
        axe, pistol, cap = slot("weapon", 5000100, 1, 0x51), slot("weapon", 14000000, 1, 0x52), slot("armor", 60000, 1, 0x55)
        key = lambda r: struct.unpack_from("<I", r, 4)[0]
        return make_save(inventory=[axe, pistol, cap],
                         gems=[(0xC0800041, 1, 1, [126301]), (0xC0800042, 2, 1, [])],
                         blocks=[(key(axe), 5000100, [(1, 0xC0800041), (0x80000000, 0)]), (key(pistol), 14000000, [(0x80000000, 0)])],
                         worn_weapons=[key(pistol), key(axe)], worn_armor=[key(cap)])

    def test_gems_and_runes(self):
        g = summarize(self.build(), "x")["gems"]
        self.assertEqual([x["type"] for x in g], ["gem", "rune"])
        self.assertEqual((g[0]["shape"], g[0]["effects"][0]["id"]), ("Radial", 126301))

    def test_gem_slots_and_where_a_gem_is_fitted(self):
        s = summarize(self.build(), "x")
        axe = s["inventory"]["weapons"][0]
        self.assertEqual([x["shape"] for x in axe["gemSlots"]][:2], ["Radial", "Closed"])
        self.assertEqual(axe["gemSlots"][0]["gem"], 0xC0800041)
        self.assertEqual(s["gems"][0]["fittedTo"], _label(axe))      # the gem knows which weapon it sits in
        self.assertIsNone(s["gems"][1]["fittedTo"])                  # the rune is loose

    def test_worn_items_are_matched_to_the_inventory_by_handle(self):
        s = summarize(self.build(), "x")
        weapons, armor = {w["id"]: w for w in s["inventory"]["weapons"]}, s["inventory"]["armor"]
        eq = s["equipped"]
        self.assertEqual(eq["weapons"][:2], [_label(weapons[14000000]), _label(weapons[5000000])])   # pistol first, axe second
        self.assertEqual(eq["weapons"][2:], [None, None])                                            # unmatched handles stay empty
        self.assertEqual(eq["armor"][0], _label(armor[0]))
        self.assertEqual(eq["armor"][1:], [None, None, None])


class Lanterns(unittest.TestCase):
    def test_a_calibrated_bit_reads_lit_and_an_uncalibrated_lantern_is_not_reported(self):
        from bloodborne import lanterns, layout
        d = bytearray(make_save())
        lay = layout.find(bytes(d))
        d[lay.aob + 5000] |= 0x20
        table = [{"name": "Central Yharnam", "offset": 5000, "mask": 0x20}, {"name": "Cathedral Ward", "offset": 5001, "mask": 0x04}]
        r = lanterns.read(bytes(d), lay, table)
        self.assertEqual((r["calibrated"], r["lit"]), (2, ["Central Yharnam"]))

    def test_flagdiff_add_refuses_anything_but_one_clean_bit(self):
        import subprocess, sys, tempfile
        with tempfile.TemporaryDirectory() as t:
            a, b = Path(t, "a"), Path(t, "b")
            from bloodborne import layout
            d = bytearray(make_save())
            lay = layout.find(bytes(d))
            a.write_bytes(bytes(d))
            d[lay.aob + 5000] |= 0x60            # two bits at once: not one lantern
            b.write_bytes(bytes(d))
            r = subprocess.run([sys.executable, "tools/flagdiff.py", str(a), str(b), "--add", "X"], capture_output=True, text=True, cwd=Path(__file__).resolve().parent.parent)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("not one clean bit", r.stderr + r.stdout)


class Reader(unittest.TestCase):
    def test_header_and_character_extras(self):
        s = summarize(make_save(play_ms=14334210, deaths=12), "x")
        self.assertEqual(s["header"]["playtime"], "3:58:54")
        self.assertEqual((s["character"]["deaths"], s["character"]["health"]["base"], s["character"]["newGameCycle"]), (12, 698, 0))

    def test_inventory_slots_decode_by_type(self):
        inv = [slot("goods", 1000, 20, 0x41), slot("armor", 60000, 1, 0x42), slot("weapon", 5000100, 1, 0x43),
               slot("weapon", 5010200, 1, 0x44), slot("weapon", 5020000, 1, 0x45)]
        s = summarize(make_save(inventory=inv, storage=[slot("goods", 900, 58)], keys=[slot("goods", 4312)]), "x")
        self.assertEqual((s["inventory"]["goods"][0]["id"], s["inventory"]["goods"][0]["amount"]), (1000, 20))
        self.assertEqual(s["inventory"]["armor"][0]["id"], 60000)
        w = s["inventory"]["weapons"]
        self.assertEqual((w[0]["id"], w[0]["level"], w[0]["imprint"]), (5000000, 1, None))
        self.assertEqual((w[1]["id"], w[1]["level"], w[1]["imprint"]), (5000000, 2, "Uncanny"))
        self.assertEqual((w[2]["id"], w[2]["level"], w[2]["imprint"]), (5000000, 0, "Lost"))
        self.assertEqual(s["storage"]["goods"][0]["amount"], 58)
        self.assertEqual(s["keyItems"]["goods"][0]["id"], 4312)

    def test_empty_slots_are_not_items(self):
        s = summarize(make_save(), "x")
        self.assertEqual(sum(len(v) for g in ("inventory", "storage", "keyItems") for v in s[g].values()), 0)

    def test_boss_flags(self):
        self.assertEqual(summarize(make_save(), "x")["bosses"]["defeated"], [])
        self.assertEqual(summarize(make_save(defeated=("Cleric Beast", "Micolash")), "x")["bosses"]["defeated"], ["Cleric Beast", "Micolash"])

    def test_names_come_from_the_game_tables_when_generated(self):
        from bloodborne.bb import names
        if not names():
            self.skipTest("db_bb/names.json not generated here")
        s = summarize(make_save(inventory=[slot("goods", 1000, 20)]), "x")
        self.assertEqual(s["inventory"]["goods"][0]["name"], "Blood Vial")

    def test_history_reports_a_restore_and_new_gear_and_boss_kills(self):
        with tempfile.TemporaryDirectory() as t:
            saves = (("BB_2026-01-01_10-00-00", dict(play_ms=3_600_000, deaths=3)),
                     ("BB_2026-01-02_10-00-00", dict(play_ms=7_200_000, deaths=5, inventory=[slot("weapon", 5000000)], defeated=("Cleric Beast",))),
                     ("BB_2026-01-03_10-00-00", dict(play_ms=3_700_000, deaths=3)))
            for name, kw in saves:
                p = Path(t, name, "SPRJ0005")
                p.mkdir(parents=True)
                (p / "userdata0000").write_bytes(make_save(**kw))
            h = history([t])
            self.assertTrue(any("play time went back" in n for n in h["notes"]))
            self.assertTrue(any("no longer defeated" in n for n in h["notes"]))
            self.assertEqual(h["changes"][0]["bossesDefeated"], ["Cleric Beast"])


@unittest.skipUnless(SNAPSHOTS.exists(), "no real snapshots on this machine")
class RealSaves(unittest.TestCase):
    def test_every_real_snapshot_reads_and_the_stats_add_up_to_the_level(self):
        n = 0
        for f in SNAPSHOTS.rglob("userdata0000"):
            s = summarize(f)
            if not s["empty"]:
                c = s["character"]
                self.assertEqual(c["level"], c["levelFromStats"], f)
                for grp in ("inventory", "storage", "keyItems"):
                    self.assertEqual(s[grp]["other"], [], f"{grp} holds a record the reader cannot classify in {f}")
                n += 1
        self.assertGreater(n, 0)


if __name__ == "__main__":
    unittest.main()
