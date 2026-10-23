#!/usr/bin/env python3
"""Schedule screen art: the title 今週のよてい! and the stat labels (build step).

  schedart.py preview OUT.png      the edited areas, drawn with the screen's palettes (Pillow)

The schedule screen's BG2 is a 4bpp tile set packed at $CA:8000 (256 tiles, one loader) and a
32x32 map packed at $B9:99B2 (words; the loader adds the priority bit). The background is a
checker of tiles 1/2/3: map word [[1, 2], [$C002, 3]][row & 1][col & 1] ($C000: flipped both ways).

English: an area is rebuilt from the checker, the new text is drawn over it, and its cells get
tiles of their own (the area's old tiles first, then tiles the map doesn't use). Both blocks are
repacked into ART_BANK and their loaders repointed.
- Title (cells 2-21, rows 0-3, palette 2): font8 letters at twice the size, two-tone strokes
  (light, and dark on the lower and right edges) in blue, red and green in turn, outlined in
  light grey, like the original.
- Stat labels under the six bars (row 26, cells 15-26, palette 0) and the attack/defence types
  between the bars (cells 9-10, rows 22-26): a 3x5 pixel font, colour 10.
- The faint 攻 / 防 behind the bars: the bar pattern is rebuilt and ATK / DEF drawn instead.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import font8  # noqa: E402
import kpack  # noqa: E402
import paths  # noqa: E402
import snes  # noqa: E402

TILES = 0xCA8000
MAP = 0xB999B2
ART_BANK = 0xF7               # tiles at $F7:8000, map after them

TITLE = 'Weekly Plan!'
TITLE_AREA = (2, 0, 20, 4)    # col, row, width, height (cells)
TITLE_COLOURS = [(13, 9), (8, 7), (6, 5)]       # (light, dark) of palette 2: blue, red, green
OUTLINE = 14
STATS = ['STR', 'DEX', 'STA', 'REC', 'SPD', 'GUT']   # 筋 器 体 回 速 根
STATS_AREA = (15, 26, 12, 1)
STATS_COLOUR = 10
TYPES = ['THR', 'HLD', 'POW', 'HIT', 'AIR']          # 投 極 パ 打 飛, one a row
TYPES_AREA = (9, 22, 2, 5)
# the faint 攻 / 防 behind the attack and defence bars: (area, palette, word)
MARKS = [((5, 22, 4, 5), 3, 'ATK'), ((11, 22, 4, 5), 4, 'DEF')]
MARK_INK = {5, 6, 13, 14, 15}          # the kanji's colours there; the rest is the bar pattern
MARK_FILL, MARK_EDGE = 6, 5

TINY = {   # 3x5 capitals
    'A': ['.#.', '#.#', '###', '#.#', '#.#'], 'C': ['.##', '#..', '#..', '#..', '.##'],
    'D': ['##.', '#.#', '#.#', '#.#', '##.'], 'E': ['###', '#..', '##.', '#..', '###'],
    'G': ['.##', '#..', '#.#', '#.#', '.##'], 'H': ['#.#', '#.#', '###', '#.#', '#.#'],
    'I': ['###', '.#.', '.#.', '.#.', '###'], 'K': ['#.#', '#.#', '##.', '#.#', '#.#'],
    'L': ['#..', '#..', '#..', '#..', '###'], 'O': ['.#.', '#.#', '#.#', '#.#', '.#.'],
    'P': ['##.', '#.#', '##.', '#..', '#..'], 'R': ['##.', '#.#', '##.', '#.#', '#.#'],
    'S': ['.##', '#..', '.#.', '..#', '##.'], 'T': ['###', '.#.', '.#.', '.#.', '.#.'],
    'U': ['#.#', '#.#', '#.#', '#.#', '###'], 'W': ['#.#', '#.#', '#.#', '###', '#.#'],
    'X': ['#.#', '#.#', '.#.', '#.#', '#.#'], 'F': ['###', '#..', '##.', '#..', '#..'],
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


CHECKER = [[0x0001, 0x0002], [0xC002, 0x0003]]


def checker(tiles, area):
    """Pixels (rows of colour indices) of the plain background under an area."""
    c0, r0, w, h = area
    img = [[0] * (8 * w) for _ in range(8 * h)]
    for r in range(h):
        for c in range(w):
            e = CHECKER[(r0 + r) & 1][(c0 + c) & 1]
            p = tile_px(tiles, e & 0x3FF, e & 0x4000, e & 0x8000)
            for y in range(8):
                img[8 * r + y][8 * c:8 * c + 8] = p[y]
    return img


def draw_title(img):
    f8 = font8.glyph_bytes()
    rows = font8.parse()
    width = {ch: max((r.rfind('#') + 1 for r in g), default=0) for ch, g in rows.items()}
    stroke = {}                           # (x, y) -> letter index
    x = 0
    for i, ch in enumerate(TITLE):
        if ch == ' ':
            x += 8
            continue
        g = f8[font8.CODES[ch] * 16:font8.CODES[ch] * 16 + 16]
        for y in range(16):
            for cx in range(8):
                if g[y] & (0x80 >> cx):
                    for dy in range(2):
                        for dx in range(2):
                            stroke[(x + 2 * cx + dx, 2 * y + dy)] = i
        x += 2 * width[ch] + 2
    total = x - 2
    w, h = len(img[0]), len(img)
    ox = (w - total) // 2
    ys = [y for _, y in stroke]
    oy = (h - (max(ys) - min(ys) + 1)) // 2 - min(ys)
    pts = {(px + ox, py + oy): i for (px, py), i in stroke.items()}
    if not all(0 < px < w - 1 and 0 < py < h - 1 for px, py in pts):
        raise SystemExit(f'schedart: {TITLE!r} does not fit the title area')
    for (px, py), i in pts.items():
        light, dark = TITLE_COLOURS[i % len(TITLE_COLOURS)]
        edge = (px + 1, py) not in pts or (px, py + 1) not in pts
        img[py][px] = dark if edge else light
    for (px, py) in pts:
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                q = (px + dx, py + dy)
                if q not in pts:
                    img[q[1]][q[0]] = OUTLINE


def draw_stats(img):
    for k, word in enumerate(STATS):
        x0 = 16 * k + (16 - (4 * len(word) - 1)) // 2
        for i, ch in enumerate(word):
            for y, row in enumerate(TINY[ch]):
                for x, c in enumerate(row):
                    if c == '#':
                        img[1 + y][x0 + 4 * i + x] = STATS_COLOUR


def draw_tiny(img, word, x0, y0, colour):
    for i, ch in enumerate(word):
        for y, row in enumerate(TINY[ch]):
            for x, c in enumerate(row):
                if c == '#':
                    img[y0 + y][x0 + 4 * i + x] = colour


def draw_types(img):
    for k, word in enumerate(TYPES):
        draw_tiny(img, word, (16 - (4 * len(word) - 1)) // 2, 8 * k + 1, STATS_COLOUR)


def area_px(tiles, mp, area):
    c0, r0, w, h = area
    img = [[0] * (8 * w) for _ in range(8 * h)]
    for r in range(h):
        for c in range(w):
            i = 2 * ((r0 + r) * 32 + c0 + c)
            e = mp[i] | mp[i + 1] << 8
            p = tile_px(tiles, e & 0x3FF, e & 0x4000, e & 0x8000)
            for y in range(8):
                img[8 * r + y][8 * c:8 * c + 8] = p[y]
    return img


def draw_mark(img, word):
    """Rebuild the bar pattern (a majority of the 8-row bands, ink left out), then the word."""
    h, w = len(img), len(img[0])
    clean = [[0] * w for _ in range(8)]
    for y in range(8):
        for x in range(w):
            votes = [img[b + y][x] for b in range(0, h, 8) if img[b + y][x] not in MARK_INK]
            clean[y][x] = max(set(votes), key=votes.count) if votes else img[y][x]
    for y in range(h):
        img[y][:] = clean[y % 8]
    f8 = font8.glyph_bytes()
    pts = set()
    x = 0
    for ch in word:
        g = f8[font8.CODES[ch] * 16:font8.CODES[ch] * 16 + 16]
        for gy in range(16):
            for cx in range(8):
                if g[gy] & (0x80 >> cx):
                    for dy in range(2):
                        pts |= {(x + cx, 2 * gy + dy), (x + cx + 1, 2 * gy + dy)}
        x += 9
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    ox = (w - (max(xs) - min(xs) + 1)) // 2 - min(xs)
    oy = (h - (max(ys) - min(ys) + 1)) // 2 - min(ys)
    for px, py in pts:
        edge = (px + 1, py) not in pts or (px, py + 1) not in pts
        img[py + oy][px + ox] = MARK_EDGE if edge else MARK_FILL


def build(data):
    tiles, _ = kpack.unpack(data, to_off(TILES))
    tiles = bytearray(tiles)
    mp, _ = kpack.unpack(data, to_off(MAP))
    mp = bytearray(mp)
    used = {(mp[2 * i] | mp[2 * i + 1] << 8) & 0x3FF for i in range(len(mp) // 2)}
    free = [t for t in range(len(tiles) // 32) if t not in used and t]
    jobs = []
    title = checker(tiles, TITLE_AREA)
    draw_title(title)
    jobs.append((TITLE_AREA, title, 2))
    stats = checker(tiles, STATS_AREA)
    draw_stats(stats)
    jobs.append((STATS_AREA, stats, 0))
    types = checker(tiles, TYPES_AREA)
    draw_types(types)
    jobs.append((TYPES_AREA, types, 0))
    for area, pal, word in MARKS:
        img = area_px(tiles, mp, area)
        draw_mark(img, word)
        jobs.append((area, img, pal))
    for (c0, r0, w, h), img, pal in jobs:
        own = []
        for r in range(h):
            for c in range(w):
                e = mp[2 * ((r0 + r) * 32 + c0 + c)] | mp[2 * ((r0 + r) * 32 + c0 + c) + 1] << 8
                if e & 0x3FF not in (1, 2, 3) and e & 0x3FF not in own:
                    own.append(e & 0x3FF)
        pool = own + free
        for r in range(h):
            for c in range(w):
                px = [img[8 * r + y][8 * c:8 * c + 8] for y in range(8)]
                b = px_tile(px)
                e = CHECKER[(r0 + r) & 1][(c0 + c) & 1]
                if px == tile_px(tiles, e & 0x3FF, e & 0x4000, e & 0x8000):
                    i = 2 * ((r0 + r) * 32 + c0 + c)
                    mp[i:i + 2] = e.to_bytes(2, 'little')
                    continue
                else:
                    if not pool:
                        raise SystemExit('schedart: out of free tiles')
                    t, p = pool.pop(0), pal
                    if t in free:
                        free.remove(t)
                    tiles[t * 32:t * 32 + 32] = b
                i = 2 * ((r0 + r) * 32 + c0 + c)
                mp[i:i + 2] = (t | p << 10).to_bytes(2, 'little')
    return bytes(tiles), bytes(mp), jobs


def apply(rom):
    data = bytes(rom)
    tiles, mp, _ = build(data)
    r = snes.Rom(rom)
    pt, pm = kpack.pack(tiles), kpack.pack(mp)
    o = r.to_file((ART_BANK << 16) | 0x8000)
    rom[o:o + len(pt)] = pt
    rom[o + len(pt):o + len(pt) + len(pm)] = pm
    mp_addr = 0x8000 + len(pt)
    n = 0
    for blk, new in ((TILES, 0x8000), (MAP, mp_addr)):
        pat = bytes([0xA0, blk & 0xFF, (blk >> 8) & 0xFF, 0xA9, blk >> 16])
        i = data.find(pat)
        while i != -1:
            rom[i + 1:i + 3] = new.to_bytes(2, 'little')
            rom[i + 4] = ART_BANK
            n += 1
            i = data.find(pat, i + 1)
    if n < 2:
        raise SystemExit(f'schedart: {n} loaders found, expected the tile set and the map')
    return n


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ['preview'] and len(argv) == 2:
        from PIL import Image
        _, _, jobs = build(paths.ROM.read_bytes())
        pal = {0: [(216, 216, 216), (216, 216, 216), (96, 96, 112), (184, 184, 200), (72, 72, 88),
                   (120, 32, 40), (128, 88, 144), (200, 104, 120), (120, 168, 104), (88, 120, 72),
                   (48, 40, 48), (184, 160, 152), (176, 128, 112), (120, 80, 64), (72, 48, 40),
                   (96, 72, 56)],
               2: [(0, 0, 0), (48, 160, 24), (72, 72, 72), (88, 88, 88), (104, 104, 104),
                   (72, 160, 56), (96, 192, 80), (160, 56, 72), (208, 64, 80), (72, 56, 160),
                   (48, 40, 48), (184, 160, 152), (176, 128, 112), (96, 88, 224), (184, 184, 184),
                   (216, 216, 216)]}
        ims = []
        for _, img, p in jobs:
            im = Image.new('RGB', (len(img[0]), len(img)))
            for y, row in enumerate(img):
                for x, c in enumerate(row):
                    im.putpixel((x, y), pal[p][c])
            ims.append(im.resize((im.width * 4, im.height * 4), Image.NEAREST))
        out = Image.new('RGB', (max(i.width for i in ims), sum(i.height + 8 for i in ims)))
        y = 0
        for im in ims:
            out.paste(im, (0, y))
            y += im.height + 8
        out.save(argv[1])
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
