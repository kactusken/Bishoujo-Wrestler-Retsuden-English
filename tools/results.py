#!/usr/bin/env python3
"""Match results on the card list (League / Tournament / shows): time and finishing hold (build step).

The card list loads a small 8x8 font ($92:CDF7, one loader; tile = code) to BG3 tile $100, which
$8C:AA01 draws (`$3C` = $100): space, '.', 'ー', digits 0-9 (codes 0-$0C), a
few capitals and kana. A result reads "13分 9秒" (digits, then the one-code strings $8C:A10C 分
and $8C:A10E 秒) over the finishing hold: 37 records of 8 codes + $FF at $8C:9FB4.. (pointer
table $8C:96A2, read at $8C:95B7).

English: capitals A-Z, '-' and '.' get codes from $0D (a 5x7 font of this tool's own), 分 becomes
'm' and 秒 's'; the holds are rewritten in place (translation/finishes.tsv, 8 letters, centred).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kpack  # noqa: E402
import paths  # noqa: E402
import snes  # noqa: E402

TABLE = 0x8C96A2
COUNT = 37
MINUTE, SECOND = 0x8CA10C, 0x8CA10E
SMALL = 0x92CDF7             # the small font
SMALL_BANK = 0xFB
FINISHES = paths.TRANSLATION / 'finishes.tsv'

FONT = {
    'A': ['.###.', '#...#', '#...#', '#####', '#...#', '#...#', '#...#'],
    'B': ['####.', '#...#', '#...#', '####.', '#...#', '#...#', '####.'],
    'C': ['.###.', '#...#', '#....', '#....', '#....', '#...#', '.###.'],
    'D': ['####.', '#...#', '#...#', '#...#', '#...#', '#...#', '####.'],
    'E': ['#####', '#....', '#....', '####.', '#....', '#....', '#####'],
    'F': ['#####', '#....', '#....', '####.', '#....', '#....', '#....'],
    'G': ['.###.', '#...#', '#....', '#.###', '#...#', '#...#', '.####'],
    'H': ['#...#', '#...#', '#...#', '#####', '#...#', '#...#', '#...#'],
    'I': ['.###.', '..#..', '..#..', '..#..', '..#..', '..#..', '.###.'],
    'J': ['..###', '...#.', '...#.', '...#.', '#..#.', '#..#.', '.##..'],
    'K': ['#...#', '#..#.', '#.#..', '##...', '#.#..', '#..#.', '#...#'],
    'L': ['#....', '#....', '#....', '#....', '#....', '#....', '#####'],
    'M': ['#...#', '##.##', '#.#.#', '#.#.#', '#...#', '#...#', '#...#'],
    'N': ['#...#', '##..#', '#.#.#', '#..##', '#...#', '#...#', '#...#'],
    'O': ['.###.', '#...#', '#...#', '#...#', '#...#', '#...#', '.###.'],
    'P': ['####.', '#...#', '#...#', '####.', '#....', '#....', '#....'],
    'Q': ['.###.', '#...#', '#...#', '#...#', '#.#.#', '#..#.', '.##.#'],
    'R': ['####.', '#...#', '#...#', '####.', '#.#..', '#..#.', '#...#'],
    'S': ['.####', '#....', '#....', '.###.', '....#', '....#', '####.'],
    'T': ['#####', '..#..', '..#..', '..#..', '..#..', '..#..', '..#..'],
    'U': ['#...#', '#...#', '#...#', '#...#', '#...#', '#...#', '.###.'],
    'V': ['#...#', '#...#', '#...#', '#...#', '#...#', '.#.#.', '..#..'],
    'W': ['#...#', '#...#', '#...#', '#.#.#', '#.#.#', '##.##', '#...#'],
    'X': ['#...#', '#...#', '.#.#.', '..#..', '.#.#.', '#...#', '#...#'],
    'Y': ['#...#', '#...#', '.#.#.', '..#..', '..#..', '..#..', '..#..'],
    'Z': ['#####', '....#', '...#.', '..#..', '.#...', '#....', '#####'],
    '-': ['.....', '.....', '.....', '.###.', '.....', '.....', '.....'],
    'm': ['.....', '.....', '##.#.', '#.#.#', '#.#.#', '#.#.#', '#.#.#'],
    's': ['.....', '.....', '.###.', '#....', '.##..', '...#.', '###..'],
}
KEEP = {' ': 0x00, '.': 0x01, **{str(i): 0x03 + i for i in range(10)}}
CODES = dict(KEEP)
CODES.update({ch: 0x0D + i for i, ch in enumerate(FONT)})


def to_off(addr):
    return ((addr >> 16) & 0x7F) * 0x8000 + (addr & 0x7FFF)


def finishes():
    out = []
    for line in FINISHES.read_text(encoding='utf-8').splitlines():
        if line.startswith('#') or not line.strip():
            continue
        jp, en = (line.split('\t') + [''])[:2]
        out.append((jp, en.upper()))
    if len(out) != COUNT:
        raise SystemExit(f'results: {len(out)} holds in {FINISHES.name}, expected {COUNT}')
    return out


def encode(text):
    bad = set(text) - set(CODES)
    if bad:
        raise SystemExit(f'results: {text!r}: {"".join(sorted(bad))} not in the small font')
    return bytes(CODES[c] for c in text)


def apply(rom):
    data = bytes(rom)
    r = snes.Rom(rom)
    tiles, _ = kpack.unpack(data, to_off(SMALL))
    tiles = bytearray(tiles)
    t0 = 0x03 * 16                               # the planes the digit 0 uses
    planes = (any(tiles[t0 + 2 * y] for y in range(8)), any(tiles[t0 + 2 * y + 1] for y in range(8)))
    for ch, rows in FONT.items():
        o = CODES[ch] * 16
        for y in range(8):
            b = 0
            if 0 < y:
                for x, c in enumerate(rows[y - 1] if y - 1 < len(rows) else ''):
                    if c == '#':
                        b |= 0x80 >> (x + 1)
            tiles[o + 2 * y] = b if planes[0] else 0
            tiles[o + 2 * y + 1] = b if planes[1] else 0
    packed = kpack.pack(bytes(tiles))
    to = r.to_file(SMALL_BANK << 16 | 0x8000)
    rom[to:to + len(packed)] = packed
    pat = bytes([0xA0, SMALL & 0xFF, (SMALL >> 8) & 0xFF, 0xA9, SMALL >> 16])
    i = data.find(pat)
    if i < 0:
        raise SystemExit('results: no loader of the small font')
    rom[i + 1:i + 3] = b'\x00\x80'
    rom[i + 4] = SMALL_BANK
    t = to_off(TABLE)
    for k, (jp, en) in enumerate(finishes()):
        a = 0x8C0000 | data[t + 2 + 2 * k] | data[t + 3 + 2 * k] << 8
        o = to_off(a)
        if data[o + 8] != 0xFF or len(en) > 8:
            raise SystemExit(f'results: {en!r} at ${a:06X}: 8 letters at most')
        rom[o:o + 8] = encode(en.center(8))
    for a, ch in ((MINUTE, 'm'), (SECOND, 's')):
        o = to_off(a)
        rom[o] = CODES[ch]
    return COUNT


def main(argv=None):
    sys.exit(__doc__)


if __name__ == '__main__':
    main()
