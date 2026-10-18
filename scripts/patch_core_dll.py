"""Make the bundled Pengu core.dll read SEXO2's data folder instead of Rose's.

The core.dll inherited from Rose (no public source, so it cannot be rebuilt) builds two
paths from %LOCALAPPDATA% with fixed UTF-16 strings, ``\\Rose`` and ``\\Rose\\config.ini``,
each appended with a constant length (``mov r8d, <len>`` right before
``lea rdx, [rip+<string>]``). This rewrites both strings to ``\\SEXO2`` and lengthens
those constants by one. It refuses to touch the file unless every string is found once,
has room for the longer text, and every reference to it is such a length-and-address
pair; an already patched file is left as it is. The file's Authenticode signature, which
any change invalidates, is removed so the file is plainly unsigned rather than tampered.

    python scripts/patch_core_dll.py "Pengu Loader/core.dll"
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

REPLACEMENTS = (("\\Rose\\config.ini", "\\SEXO2\\config.ini"), ("\\Rose", "\\SEXO2"))


class PatchError(Exception):
    pass


def _sections(data: bytes) -> list[tuple[bytes, int, int, int, int]]:
    """(name, virtual address, virtual size, raw offset, raw size) of each section."""
    if len(data) < 0x40 or data[:2] != b"MZ":
        raise PatchError("not a PE file")
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe : pe + 4] != b"PE\0\0":
        raise PatchError("not a PE file")
    count = struct.unpack_from("<H", data, pe + 6)[0]
    optional_size = struct.unpack_from("<H", data, pe + 20)[0]
    table = pe + 24 + optional_size
    result = []
    for index in range(count):
        name, vsize, vaddr, rsize, roff = struct.unpack_from("<8sIIII", data, table + 40 * index)
        result.append((name.rstrip(b"\0"), vaddr, vsize, roff, rsize))
    return result


def _rva(sections, offset: int) -> int:
    for _name, vaddr, _vsize, roff, rsize in sections:
        if roff <= offset < roff + rsize:
            return offset - roff + vaddr
    raise PatchError(f"offset {offset:#x} is in no section")


def _rip_references(data: bytes, sections, target_rva: int) -> list[int]:
    """File offsets of every ``lea r64, [rip+disp32]`` that points at ``target_rva``."""
    found = []
    for name, vaddr, _vsize, roff, rsize in sections:
        if not name.startswith(b".text"):
            continue
        for offset in range(roff, roff + rsize - 7):
            if data[offset] in (0x48, 0x4C) and data[offset + 1] == 0x8D and data[offset + 2] & 0xC7 == 0x05:
                disp = struct.unpack_from("<i", data, offset + 3)[0]
                if offset - roff + vaddr + 7 + disp == target_rva:
                    found.append(offset)
    return found


def _strip_signature(out: bytearray) -> None:
    """Drop the certificate table (data directory 4), stored at the end of the file."""
    pe = struct.unpack_from("<I", out, 0x3C)[0]
    magic = struct.unpack_from("<H", out, pe + 24)[0]
    directory = pe + 24 + (112 if magic == 0x20B else 96) + 4 * 8
    offset, size = struct.unpack_from("<II", out, directory)
    if not size:
        return
    if offset + size != len(out):
        raise PatchError("signature is not at the end of the file")
    struct.pack_into("<II", out, directory, 0, 0)
    del out[offset:]


def patch(data: bytes) -> bytes:
    if all(new.encode("utf-16-le") + b"\0\0" in data for _old, new in REPLACEMENTS):
        return data  # already patched
    sections = _sections(data)
    out = bytearray(data)
    for old, new in REPLACEMENTS:
        needle = old.encode("utf-16-le") + b"\0\0"
        # "\Rose" also starts "\Rose\config.ini": only whole strings count
        starts = [i for i in range(len(data)) if data.startswith(needle, i)]
        if len(starts) != 1:
            raise PatchError(f"{old!r} found {len(starts)} times, expected once")
        start = starts[0]
        replacement = new.encode("utf-16-le") + b"\0\0"
        room = data[start + len(needle) : start + len(replacement)]
        if room != b"\0" * len(room):
            raise PatchError(f"no room after {old!r} for {new!r}")
        references = _rip_references(data, sections, _rva(sections, start))
        if not references:
            raise PatchError(f"{old!r} is not referenced")
        for lea in references:
            mov = lea - 6
            if data[mov : mov + 2] != b"\x41\xb8" or struct.unpack_from("<I", data, mov + 2)[0] != len(old):
                raise PatchError(f"reference at {lea:#x} to {old!r} is not preceded by mov r8d, {len(old)}")
            struct.pack_into("<I", out, mov + 2, len(new))
        out[start : start + len(replacement)] = replacement
    _strip_signature(out)
    return bytes(out)


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    path = Path(sys.argv[1])
    data = path.read_bytes()
    try:
        patched = patch(data)
    except PatchError as error:
        print(f"core.dll not patched: {error}")
        return 1
    if patched == data:
        print("core.dll already reads %LOCALAPPDATA%\\SEXO2")
        return 0
    path.write_bytes(patched)
    changed = sum(1 for a, b in zip(data, patched) if a != b)
    print(f"core.dll now reads %LOCALAPPDATA%\\SEXO2 ({changed} bytes changed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
