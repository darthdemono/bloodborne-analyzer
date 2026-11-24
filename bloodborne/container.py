"""The file level: size, magic, and finding the character block. Format notes and sources in notes/format.md."""
import struct
from pathlib import Path

SIZE = 0x140000          # userdata0000..0009 are all exactly 1,310,720 bytes; userdata0010 (settings) is 262,144
MAGIC = b"\x41\x00\x00\x00"   # the next four bytes differ between saves, so only these are checked


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


def u32(data: bytes, off: int) -> int:
    return struct.unpack_from("<I", data, off)[0]
