import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests.test_saves import make_save, slot

ROOT = Path(__file__).resolve().parent.parent
NODE = shutil.which("node")


@unittest.skipUnless(NODE, "node is not installed")
class Web(unittest.TestCase):
    def test_python_and_javascript_readers_agree_on_synthetic_saves(self):
        """The parity gate itself, on saves built with items, gems, bosses and a restore, so it is exercised without real saves."""
        with tempfile.TemporaryDirectory() as t:
            saves = (("BB_2026-01-01_10-00-00", dict(play_ms=3_600_000, deaths=3)),
                     ("BB_2026-01-02_10-00-00", dict(play_ms=7_200_000, deaths=5, defeated=("Cleric Beast",), inventory=[slot("weapon", 5000100, 1, 0x51), slot("goods", 1000, 20, 0x41), slot("armor", 60000, 1, 0x55)],
                                                      gems=[(0xC0800041, 1, 1, [126301])], blocks=[(0x80800051, 5000100, [(1, 0xC0800041)])], worn_weapons=[0x80800051], worn_armor=[0x90800055])),
                     ("BB_2026-01-03_10-00-00", dict(play_ms=3_700_000, deaths=3)))
            for name, kw in saves:
                d = Path(t, name, "SPRJ0005")
                d.mkdir(parents=True)
                (d / "userdata0000").write_bytes(make_save(**kw))
            r = subprocess.run([NODE, "tools/parity.mjs", t], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("parity OK", r.stdout)

    def test_the_markdown_viewer_escapes_html(self):
        r = subprocess.run([NODE, "--input-type=module", "-e", "import { mdToHtml } from './app/mdview.js'; console.log(mdToHtml('# a <b>\\n\\n**x** <script>alert(1)</script>'))"], cwd=ROOT, capture_output=True, text=True)
        self.assertNotIn("<script>", r.stdout)
        self.assertIn("&lt;script&gt;", r.stdout)
        self.assertIn("<strong>x</strong>", r.stdout)


if __name__ == "__main__":
    unittest.main()
