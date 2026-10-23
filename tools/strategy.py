#!/usr/bin/env python3
"""The match strategy icons: 大技 間合 忍耐 必殺 返し 一撃 場外 フォール (build step).

  strategy.py preview OUT.png      the eight icons, original and English, drawn in palette 3 (Pillow)

In a match, A/X/Y/B pick one of the four strategies set on the Logic screen, and a 32x16 icon on
BG2 shows it (palette 3, map at row 24, cell 17). Its tiles are one block packed at $B0:DCFE
(49 tiles, VRAM tiles $CF-$FF; one loader). Each icon is a record of 8 map words at $B9:9932
(4x2 cells, $0C00 | tile - $CF; $8C adds $2000 and $CF): icons share the bracket tiles and some
others, so the records are rewritten with the new tiles.

English: three-letter forms in 5x8 bold letters, light on the upper half and mid below with a
dark drop shadow, in each icon's own colour; the grey brackets stay (the left one a pixel further
left, to fit), and Finish keeps its pink flame. The block is repacked into ICON_BANK.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kpack  # noqa: E402
import paths  # noqa: E402
import snes  # noqa: E402

TILES = 0xB0DCFE
RECORDS = 0xB99932
COUNT = 8
FIRST_TILE = 0xCF
MAX_TILES = 0x100 - FIRST_TILE      # tiles from $100 on hold other art
ICON_BANK = 0xFE

# record order: (word, colour ramp)
WORDS = [('BIG', 'gold'), ('RNG', 'pink'), ('END', 'green'), ('FIN', 'gold'),
         ('CTR', 'green'), ('KO', 'gold'), ('OUT', 'pink'), ('PIN', 'green')]
FLAME = 3                           # 必殺: its pink flame (rows 0-8) stays
FLAME_INK = {1, 2, 7}
# (shadow, light, mid) of palette 3
RAMPS = {'gold': (0xC, 0xF, 0xE), 'pink': (0x1, 0x7, 0x2), 'green': (0x8, 0xB, 0xA)}
BRACKET_INK = {3, 4, 5, 6}
TEXT_X = (5, 24)                    # columns between the brackets (end exclusive)

BOLD = {
    'B': ['####.', '##.##', '##.##', '####.', '##.##', '##.##', '##.##', '####.'],
    'C': ['.####', '##...', '##...', '##...', '##...', '##...', '##...', '.####'],
    'D': ['####.', '##.##', '##.##', '##.##', '##.##', '##.##', '##.##', '####.'],
    'E': ['#####', '##...', '##...', '####.', '##...', '##...', '##...', '#####'],
    'F': ['#####', '##...', '##...', '####.', '##...', '##...', '##...', '##...'],
    'G': ['.####', '##...', '##...', '##...', '##.##', '##.##', '##.##', '.####'],
    'I': ['##', '##', '##', '##', '##', '##', '##', '##'],
    'K': ['##.##', '##.##', '####.', '###..', '####.', '##.##', '##.##', '##.##'],
    'N': ['##..##', '###.##', '###.##', '##.###', '##.###', '##..##', '##..##', '##..##'],
    'O': ['.###.', '##.##', '##.##', '##.##', '##.##', '##.##', '##.##', '.###.'],
    'P': ['####.', '##.##', '##.##', '####.', '##...', '##...', '##...', '##...'],
    'R': ['####.', '##.##', '##.##', '####.', '###..', '##.##', '##.##', '##.##'],
    'T': ['######', '..##..', '..##..', '..##..', '..##..', '..##..', '..##..', '..##..'],
    'U': ['##.##', '##.##', '##.##', '##.##', '##.##', '##.##', '##.##', '.###.'],
}


def to_off(addr):
    return ((addr >> 16) & 0x7F) * 0x8000 + (addr & 0x7FFF)


def tile_px(tiles, t, hf=False, vf=False):
    b = tiles[t * 32:t * 32 + 32]
    out = [[0] * 8 for _ in range(8)]
    for y in range(8):
        for x in range(8):
            c = 0
            for p in range(4):
                c |= ((b[(p // 2) * 16 + 2 * y + (p & 1)] >> (7 - x)) & 1) << p
            out[7 - y if vf else y][7 - x if hf else x] = c
    return out


def px_tile(px):
    b = bytearray(32)
    for y in range(8):
        for x in range(8):
            for p in range(4):
                if px[y][x] >> p & 1:
                    b[(p // 2) * 16 + 2 * y + (p & 1)] |= 0x80 >> x
    return bytes(b)


def records(data):
    o = to_off(RECORDS)
    return [[data[o + 16 * k + 2 * i] | data[o + 16 * k + 2 * i + 1] << 8 for i in range(8)]
            for k in range(COUNT)]


def icon_px(tiles, rec):
    img = [[0] * 32 for _ in range(16)]
    for i, e in enumerate(rec):
        p = tile_px(tiles, e & 0x3FF, e & 0x4000, e & 0x8000)
        for y in range(8):
            img[(i // 4) * 8 + y][(i % 4) * 8:(i % 4) * 8 + 8] = p[y]
    return img


def text_mask(word):
    cols = []
    for i, ch in enumerate(word):
        g = BOLD[ch]
        if i:
            cols.append([0] * 8)
        cols += [[1 if g[y][x] == '#' else 0 for y in range(8)] for x in range(len(g[0]))]
    return {(x, y) for x, col in enumerate(cols) for y, v in enumerate(col) if v}, len(cols)


def draw(orig, k):
    """Icon k in English: brackets from 大技 (the left one moved a pixel left), text, flame."""
    base = orig[0]
    img = [[0] * 32 for _ in range(16)]
    for y in range(16):
        for x in range(32):
            c = base[y][x]
            if c in BRACKET_INK:
                if x < 8:
                    img[y][x - 1] = c
                elif x >= 24:
                    img[y][x] = c
    if k == FLAME:
        for y in range(9):
            for x in range(32):
                if orig[FLAME][y][x] in FLAME_INK:
                    img[y][x] = orig[FLAME][y][x]
    word, ramp = WORDS[k]
    shadow, light, mid = RAMPS[ramp]
    pts, w = text_mask(word)
    room = TEXT_X[1] - TEXT_X[0]
    if w + 1 > room:
        raise SystemExit(f'strategy: {word!r} is {w + 1} pixels with its shadow, {room} fit')
    if w + 1 <= 16:                 # clear of the bracket tiles: they stay shared
        ox = 8 + (16 - w - 1) // 2
    else:
        ox = TEXT_X[0] + (room - w - 1) // 2
    oy = 5 if k == FLAME else 4
    for x, y in pts:
        for dx, dy in ((1, 0), (0, 1), (1, 1)):
            if (x + dx, y + dy) not in pts:
                img[oy + y + dy][ox + x + dx] = shadow
    for x, y in pts:
        img[oy + y][ox + x] = light if y < 4 else mid
    return img


def build(data):
    tiles, _ = kpack.unpack(data, to_off(TILES))
    recs = records(data)
    orig = [icon_px(tiles, rec) for rec in recs]
    new = [draw(orig, k) for k in range(COUNT)]
    out, index, recs_out = [], {}, []
    for img in new:
        rec = []
        for i in range(8):
            px = [img[(i // 4) * 8 + y][(i % 4) * 8:(i % 4) * 8 + 8] for y in range(8)]
            b = px_tile(px)
            if b not in index:
                index[b] = len(out)
                out.append(b)
            rec.append(0x0C00 | index[b])
        recs_out.append(rec)
    if len(out) > MAX_TILES:
        raise SystemExit(f'strategy: {len(out)} tiles, {MAX_TILES} fit')
    out += [bytes(32)] * (MAX_TILES - len(out))     # the original block's size
    return b''.join(out), recs_out, orig, new


def apply(rom):
    data = bytes(rom)
    tiles, recs, _, _ = build(data)
    r = snes.Rom(rom)
    packed = kpack.pack(tiles)
    o = r.to_file(ICON_BANK << 16 | 0x8000)
    rom[o:o + len(packed)] = packed
    pat = bytes([0xA0, TILES & 0xFF, (TILES >> 8) & 0xFF, 0xA9, TILES >> 16])
    i = data.find(pat)
    if i < 0 or data.find(pat, i + 1) >= 0:
        raise SystemExit('strategy: expected one loader of the icon tiles')
    rom[i + 1:i + 3] = b'\x00\x80'
    rom[i + 4] = ICON_BANK
    o = to_off(RECORDS)
    for k, rec in enumerate(recs):
        for j, e in enumerate(rec):
            rom[o + 16 * k + 2 * j:o + 16 * k + 2 * j + 2] = e.to_bytes(2, 'little')
    return len({e & 0x3FF for rec in recs for e in rec})


# palette 3 in a match (CGRAM $30-$3F)
PALETTE = [(65, 65, 90), (139, 49, 82), (238, 57, 115), (82, 82, 82), (123, 123, 123),
           (172, 172, 172), (213, 213, 213), (255, 106, 156), (74, 106, 90), (90, 156, 131),
           (115, 197, 180), (180, 230, 213), (123, 90, 82), (148, 131, 65), (213, 164, 98),
           (255, 205, 139)]


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ['preview'] and len(argv) == 2:
        from PIL import Image
        _, _, orig, new = build(paths.ROM.read_bytes())
        out = Image.new('RGB', (2 * 36, COUNT * 20), (255, 255, 255))
        for k in range(COUNT):
            for c, img in enumerate((orig[k], new[k])):
                for y in range(16):
                    for x in range(32):
                        out.putpixel((c * 36 + x, k * 20 + y), PALETTE[img[y][x]])
        out.resize((out.width * 4, out.height * 4), Image.NEAREST).save(argv[1])
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
