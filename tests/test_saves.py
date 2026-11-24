import struct
import tempfile
import unittest
from pathlib import Path

from bloodborne import BloodborneError, summarize
from bloodborne.combine import history, stamp
from bloodborne.container import MAGIC, SIZE

SNAPSHOTS = Path("/mnt/nobara-data/Backup/user/bb-snapshots")


def make_save(name="Joy", vig=16, end=13, st=15, skl=9, blt=6, arc=7, echoes=181, insight=1) -> bytes:
    """A synthetic character file: magic, the 25-record id table, and a block 636 bytes before it."""
    d = bytearray(SIZE)
    d[:len(MAGIC)] = MAGIC
    table = 40000
    for i in range(25):
        d[table + i * 16] = 0x41 + i
    b = table - 636
    stats = [vig, end, st, skl, blt, arc]
    for o, v in zip((48, 56, 72, 80, 88, 96), stats):
        d[b + o] = v
    struct.pack_into("<I", d, b + 128, sum(stats) - 50)
    struct.pack_into("<I", d, b + 132, echoes)
    struct.pack_into("<I", d, b + 116, insight)
    struct.pack_into("<I", d, b + 8, 698)
    struct.pack_into("<I", d, b + 32, 97)
    raw = name.encode().ljust(33, b"\0")
    d[b + 185 - 33:b + 185] = raw
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


@unittest.skipUnless(SNAPSHOTS.exists(), "no real snapshots on this machine")
class RealSaves(unittest.TestCase):
    def test_every_real_snapshot_reads_and_the_stats_add_up_to_the_level(self):
        n = 0
        for f in SNAPSHOTS.rglob("userdata0000"):
            s = summarize(f)
            if not s["empty"]:
                c = s["character"]
                self.assertEqual(c["level"], c["levelFromStats"], f)
                n += 1
        self.assertGreater(n, 0)


if __name__ == "__main__":
    unittest.main()
