#!/usr/bin/env python3
"""Small record fonts of the status screen: hometowns and belts (build step).

  recfont.py sheet NAME OUT.png    the new font (Pillow)

Hometowns: 54 records of 4 codes + $FF at file 0x7e583 over a 16x16 1bpp font ($90:A6B8, the
names font's layout, unpacked by $8C:A89F; one loader). English: every record gets its own glyphs,
the word drawn proportionally in capitals across its 4 glyphs (64 pixels: 9 letters fit).
translation/places.tsv.

Belts: 14 records of 11 codes + $FF at file 0x7ebf2 over a 2bpp font of 64 16x16 glyphs
($90:959B, five loaders) that holds just the belt names' characters. English: one letter per glyph
(tools/font8.py doubled in width, like tools/hires.py). translation/belts.tsv.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import font8  # noqa: E402
import hires  # noqa: E402
import kpack  # noqa: E402
import paths  # noqa: E402
import snes  # noqa: E402

FONTS = {
    'places': {'tsv': 'places.tsv', 'font': 0x90A6B8, 'bank': 0xF3, 'codes': 4, 'kind': 'image'},
    'belts': {'tsv': 'belts.tsv', 'font': 0x90959B, 'bank': 0xF4, 'codes': 11, 'kind': 'letters',
              'glyphs': 64},
}


def records(cfg):
    out = []
    for line in (paths.TRANSLATION / cfg['tsv']).read_text(encoding='utf-8').splitlines():
        if line.startswith('#') or not line.strip():
            continue
        off, jp, en = (line.split('\t') + [''])[:3]
        out.append((int(off, 16), jp, en))
    return out


def widths():
    """Pixel width of each font8 letter (its rightmost set column + 1)."""
    out = {}
    for ch, rows in font8.parse().items():
        out[ch] = max((r.rfind('#') + 1 for r in rows), default=0)
    return out


def image_font(recs, cfg):
    """1bpp 16x16 glyphs (names layout): each record drawn across its own cfg['codes'] glyphs."""
    f8 = font8.glyph_bytes()
    wd = widths()
    glyphs = {bytes(32): 0}               # glyph bytes -> code; 0 is the blank glyph
    recbytes = {}
    width = 16 * cfg['codes']
    for off, jp, en in recs:
        en = en.upper()
        cols = [0] * width                # one 16-bit column mask per pixel column
        x = 0
        for ch in en:
            if ch == ' ':
                x += 4
                continue
            if ch not in font8.CODES:
                raise SystemExit(f'recfont: {en!r}: {ch!r} not in the font')
            g = f8[font8.CODES[ch] * 16:font8.CODES[ch] * 16 + 16]
            for cx in range(wd[ch]):
                if x + cx >= width:
                    raise SystemExit(f'recfont: {en!r} is wider than {width} pixels')
                cols[x + cx] = sum(1 << y for y in range(16) if g[y] & (0x80 >> cx))
            x += wd[ch] + 1
        codes = []
        for k in range(cfg['codes']):
            gb = bytearray(32)
            for t in range(2):            # left and right 8x8 halves, top then bottom
                for y in range(16):
                    b = 0
                    for cx in range(8):
                        if cols[16 * k + 8 * t + cx] >> y & 1:
                            b |= 0x80 >> cx
                    gb[(y // 8) * 16 + t * 8 + y % 8] = b
            gb = bytes(gb)
            if gb not in glyphs:
                glyphs[gb] = len(glyphs)
            codes.append(glyphs[gb])
        recbytes[off] = bytes(codes) + b'\xff'
    if len(glyphs) > 0xFF:
        raise SystemExit(f'recfont: {len(glyphs)} glyphs, at most 255')
    font = bytearray(256 * 32)
    for gb, c in glyphs.items():
        base = (c & ~7) * 32 + (c & 7) * 16
        font[base:base + 16] = gb[:16]
        font[base + 0x80:base + 0x90] = gb[16:]
    return recbytes, bytes(font), len(glyphs)


def letter_font(recs, cfg, data):
    """2bpp font, one doubled letter per 16x16 glyph; returns (records, font bytes, letters)."""
    tiles, _ = kpack.unpack(data, hires.to_off(cfg['font']))
    tiles = bytearray(tiles)
    planes = (True, False)
    for y in range(8):                    # the planes glyph 2 ('A') uses
        p0, p1 = tiles[4 * 16 + 2 * y], tiles[4 * 16 + 2 * y + 1]
        if p0 or p1:
            planes = (bool(p0), bool(p1))
    chars = sorted({c for _, _, en in recs for c in en} - {' '})
    if len(chars) > cfg['glyphs'] - 1:
        raise SystemExit(f'recfont: {len(chars)} letters, {cfg["glyphs"] - 1} glyphs')
    code = {' ': 0}
    code.update({ch: i + 1 for i, ch in enumerate(chars)})
    tiles[:] = bytes(len(tiles))
    for ch, n in code.items():
        if n == 0:
            continue
        base = (n & 7) * 2 + (n >> 3) * 32
        for k, t in zip((0, 1, 16, 17), hires.letter_tiles(ch, planes)):
            tiles[(base + k) * 16:(base + k) * 16 + 16] = t
    recbytes = {}
    for off, jp, en in recs:
        if len(en) > cfg['codes']:
            raise SystemExit(f'recfont: {en!r} is longer than {cfg["codes"]} letters')
        recbytes[off] = bytes(code[c] for c in en.ljust(cfg['codes'])) + b'\xff'
    return recbytes, bytes(tiles), len(chars)


def loaders(data, block):
    """(offset of the low word, offset of the bank byte) for both loader patterns."""
    lo, hi, bank = block & 0xFF, (block >> 8) & 0xFF, block >> 16
    out = []
    for m in re.finditer(re.escape(bytes([0xA0, lo, hi, 0xA9, bank])), data):
        out.append((m.start() + 1, m.start() + 4))
    lda = bytes([0xA9, lo, hi, 0x85, 0x30])
    bk = bytes([0xA9, bank, 0x00, 0x85, 0x32])
    for m in re.finditer(re.escape(lda), data):
        i = m.start()
        if data[i + 5:i + 10] == bk:
            out.append((i + 1, i + 6))
        elif data[i - 5:i] == bk:
            out.append((i + 1, i - 4))
    return out


def build(name, data):
    cfg = FONTS[name]
    recs = records(cfg)
    if cfg['kind'] == 'image':
        return image_font(recs, cfg)
    return letter_font(recs, cfg, data)


def apply(rom, name):
    cfg = FONTS[name]
    data = bytes(rom)
    recbytes, font, n = build(name, data)
    for off, b in recbytes.items():
        if rom[off + cfg['codes']] != 0xFF:
            raise SystemExit(f'recfont {name}: record at {off:#x} is not {cfg["codes"]} codes + $FF')
        rom[off:off + len(b)] = b
    packed = kpack.pack(font)
    r = snes.Rom(rom)
    o = r.to_file((cfg['bank'] << 16) | 0x8000)
    rom[o:o + len(packed)] = packed
    sites = loaders(data, cfg['font'])
    if not sites:
        raise SystemExit(f'recfont {name}: no loader of ${cfg["font"]:06X}')
    for lo, bank in sites:
        rom[lo:lo + 2] = b'\x00\x80'
        rom[bank] = cfg['bank']
    return len(recbytes), n, len(sites)


def main(argv=None):
    argv = paths.configure(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ['sheet'] and len(argv) == 3:
        from PIL import Image
        cfg = FONTS[argv[1]]
        recbytes, font, n = build(argv[1], paths.ROM.read_bytes())
        if cfg['kind'] == 'image':
            recs = sorted(recbytes.items())
            im = Image.new('L', (16 * cfg['codes'], 16 * len(recs)), 40)
            for row, (_, b) in enumerate(recs):
                for k, c in enumerate(b[:-1]):
                    base = (c & ~7) * 32 + (c & 7) * 16
                    for half in range(2):
                        for t in range(2):
                            for y in range(8):
                                v = font[base + half * 0x80 + t * 8 + y]
                                for x in range(8):
                                    if v & (0x80 >> x):
                                        im.putpixel((16 * k + 8 * t + x, 16 * row + 8 * half + y), 255)
            im.resize((im.width * 3, im.height * 3), Image.NEAREST).save(argv[2])
        print(f'{len(recbytes)} records, {n} glyphs')
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
