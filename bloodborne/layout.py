"""The anchors, and every fixed distance from them. All of this is verified on real saves; sources in notes/format.md.

The file is a serialized stream, so nothing sits at a fixed absolute offset (except the first 12 bytes). Everything is a
distance from one anchor: the ASCII tag FACE (the appearance block) after 0xF000. From it: the inventory start, then the
username, then everything else.
"""
from dataclasses import dataclass

FACE_AFTER = 0xF000
INV_TO_USER = 469                # the username sits 469 bytes before the inventory
INV_TO_STORAGE = 34268
USER_TO_KEY = 32201
USER_TO_AOB = 68545              # 03 00 00 00 05 00 01 00 marks the start of the flag area
INV_SLOTS = 1983                 # the inventory has 1983 slots of 16 bytes; the key-item list starts 4 bytes after its end
STORAGE_SLOTS = 1984             # storage has 1984 (the full-storage glitch research)
KEY_SLOTS = 128                  # 2048 bytes of key items; the 156 bytes after them are counters, not slots
SLOT = 16
AOB = bytes.fromhex("0300000005000100")


@dataclass(frozen=True)
class Layout:
    face: int
    inventory: int
    username: int
    storage: int
    key: int
    aob: int


def find(data: bytes):
    """The Layout, or None for an empty slot (or a file whose anchors do not line up)."""
    face = data.find(b"FACE", FACE_AFTER)
    if face < 0:
        return None
    inv = face - 34028               # the appearance block starts at face + 4, and is 34028 + 4 past the inventory start
    user = inv - INV_TO_USER
    aob = user + USER_TO_AOB
    if user < 0 or data[aob:aob + 8] != AOB:   # the aob check is what makes a wrong anchor loud, not silent
        return None
    return Layout(face, inv, user, inv + INV_TO_STORAGE, user + USER_TO_KEY, aob)
