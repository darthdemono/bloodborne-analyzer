import struct
import tempfile
import unittest
from pathlib import Path

from bloodborne import BloodborneError, summarize
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
              inventory=(), storage=(), keys=(), defeated=()) -> bytes:
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
