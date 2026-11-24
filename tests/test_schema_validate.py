import json
import unittest
from pathlib import Path

from bloodborne import summarize
from bloodborne.validate import validate
from tests.test_saves import make_save

SCHEMA = json.loads(Path(__file__).resolve().parent.parent.joinpath("schema.json").read_text())


def conforms(v, sch) -> bool:
    """The few schema keywords the generator emits: type, required, properties, oneOf."""
    if "oneOf" in sch:
        return any(conforms(v, o) for o in sch["oneOf"])
    t = {"object": dict, "integer": int, "string": str, "boolean": bool}[sch["type"]]
    if not isinstance(v, t):
        return False
    if t is dict:
        return all(k in v for k in sch.get("required", [])) and all(conforms(v[k], p) for k, p in sch.get("properties", {}).items() if k in v)
    return True


class Schema(unittest.TestCase):
    def test_summary_conforms(self):
        self.assertTrue(conforms(summarize(make_save(), "x"), SCHEMA))
        self.assertTrue(conforms(summarize(bytes(0x140000), "x"), SCHEMA))

    def test_schema_matches_the_generator(self):
        import subprocess, sys
        before = Path(__file__).resolve().parent.parent.joinpath("schema.json").read_text()
        subprocess.run([sys.executable, "tools/gen_schema.py"], cwd=Path(__file__).resolve().parent.parent, check=True)
        self.assertEqual(before, Path(__file__).resolve().parent.parent.joinpath("schema.json").read_text(), "schema.json is stale: run tools/gen_schema.py")


class Validate(unittest.TestCase):
    def test_clean_save_has_no_findings(self):
        self.assertEqual(validate(summarize(make_save(), "x")), [])

    def test_level_that_does_not_add_up_is_reported(self):
        d = bytearray(make_save())
        import struct
        from bloodborne import layout
        struct.pack_into("<I", d, layout.find(bytes(d)).username - 23, 99)
        self.assertTrue(any("add up" in f for f in validate(summarize(bytes(d), "x"))))

    def test_stat_out_of_range_is_reported(self):
        self.assertTrue(any("outside" in f for f in validate(summarize(make_save(vig=120), "x"))))


if __name__ == "__main__":
    unittest.main()
