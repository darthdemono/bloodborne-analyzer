"""The file level: size, magic, and finding the character block. Format notes and sources in notes/format.md."""
import re
import struct
from pathlib import Path

SIZE = 0x140000          # userdata0000..0009 are all exactly 1,310,720 bytes; userdata0010 (settings) is 262,144
MAGIC = b"\x41\x00\x00\x00"   # the next four bytes differ between saves, so only these are checked
BLOCK_LEN = 185          # bytes of the character block that are decoded (see notes/format.md)
# 25 records of 16 bytes whose first byte counts 0x41..0x59. The character block sits 636 bytes before the first one.
_TABLE = re.compile(b"".join(re.escape(bytes([0x41 + i])) + b".{15}" for i in range(25)), re.S)
_TABLE_TO_BLOCK = 636


class BloodborneError(Exception):
    """Anything that is not a readable character file. The message says what, and is safe to show."""


def read(path) -> bytes:
    return check(Path(path).read_bytes())


def check(data: bytes) -> bytes:
    if len(data) == 0x40000:
        raise BloodborneError("this is the settings file (userdata0010), not a character")
    if len(data) == SIZE and not any(data):
        return data       # an unused character slot is all zeros: valid, and empty
    if len(data) != SIZE or not data.startswith(MAGIC):
        raise BloodborneError(f"not a decrypted Bloodborne character file ({len(data)} bytes); a PS4 save must be decrypted first")
    return data


def find_block(data: bytes):
    """Offset of the character block, or None when the slot holds no character (the file is a valid empty slot)."""
    m = _TABLE.search(data)
    if not m or m.start() < _TABLE_TO_BLOCK:
        return None
    return m.start() - _TABLE_TO_BLOCK


def u32(data: bytes, off: int) -> int:
    return struct.unpack_from("<I", data, off)[0]
