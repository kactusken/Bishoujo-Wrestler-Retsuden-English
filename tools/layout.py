#!/usr/bin/env python3
"""Screen layout fixes for the longer English text (build step; no text of its own).

  layout.py            list the fixes

Selection bar (heroine and faction lists, $8A:93E0): the red bar under the chosen line is a 14x2
map of tile 1 (packed at $97:89BF, unpacked to $7F:8000) put on BG1 by the row queue `$80:AF10`
(width `$38`, height `$3A`, attributes `$2C00`) at the row's map offset from `$8A:9443`; the
clear routine `$8A:944F` blanks the same 14x2 cells with `$80:AF6C`. "YUKIKO SHINZAKI" and
"Shinjo Regulars" are 15 letters, so both widths become 16 and the map is repacked 16 wide.

Dialogue buffer: a `$3C` string is unpacked whole into `$7E:D342` (`$8C:B450`; the window reads it
through the pointer set at `$8C:AD58`), room for 256 codes. Right after it, `$7E:D542` is the HDMA
table that feeds the window's colour math (channel 1 -> COLDATA): English strings of more than 256
codes overwrote it and the text turned darker for the rest of the scene. The buffer moves to
`$7E:F400` (0x300 bytes, 384 codes; zero in every WRAM dump taken, no writes seen in traces), and
tools/script.py refuses longer strings (MAX_CODES).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kpack  # noqa: E402
import paths  # noqa: E402
import snes  # noqa: E402

BANK = 0xFF            # free bank for this tool's data

BAR_WIDTH = 16
# (address, original bytes, new bytes, what)
PATCHES = [
    (0x8A941C, bytes([0xA9, 0x0E, 0x00]), bytes([0xA9, BAR_WIDTH, 0x00]), 'selection bar width (draw)'),
    (0x8A945C, bytes([0xA9, 0x0E, 0x00]), bytes([0xA9, BAR_WIDTH, 0x00]), 'selection bar width (clear)'),
    (0x8CAD58, bytes([0xA9, 0x42, 0xD3]), bytes([0xA9, 0x00, 0xF4]), 'dialogue buffer (window pointer)'),
    (0x8CB450, bytes([0xA9, 0x42, 0xD3]), bytes([0xA9, 0x00, 0xF4]), 'dialogue buffer (unpack)'),
]
BAR_MAP = (0x8A9401, bytes([0xA0, 0xBF, 0x89, 0xA9, 0x97]))   # LDY #$89BF / LDA #$97: the packed map


def apply(rom):
    """Install the fixes into `rom` (bytearray, expanded). Returns how many places changed."""
    r = snes.Rom(rom)
    n = 0
    for addr, old, new, what in PATCHES:
        o = r.to_file(addr)
        if bytes(rom[o:o + len(old)]) not in (old, new):
            raise SystemExit(f'layout: {what}: ${addr:06X} expected {old.hex()}, found {bytes(rom[o:o + len(old)]).hex()}')
        rom[o:o + len(new)] = new
        n += 1
    addr, old = BAR_MAP
    o = r.to_file(addr)
    if bytes(rom[o:o + len(old)]) != old:
        raise SystemExit(f'layout: selection bar map loader: ${addr:06X} expected {old.hex()}')
    packed = kpack.pack(bytes([0x01, 0x00]) * (BAR_WIDTH * 2))
    at = r.to_file((BANK << 16) | 0x8000)
    rom[at:at + len(packed)] = packed
    rom[o + 1:o + 3] = (0x8000).to_bytes(2, 'little')
    rom[o + 4] = BANK
    return n + 1


def main(argv=None):
    paths.configure(sys.argv[1:] if argv is None else argv)
    for addr, _, _, what in PATCHES:
        print(f'${addr:06X}  {what}')
    print(f'${BAR_MAP[0]:06X}  selection bar map -> ${BANK:02X}:8000')


if __name__ == '__main__':
    main()
