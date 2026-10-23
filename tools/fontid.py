#!/usr/bin/env python3
"""Identify the glyphs of a 16x16 font whose characters are in JIS X 0208 order (Pillow, numpy).

  fontid.py FONT.bin OUT.tsv [--first N] [--count N]

FONT.bin is the game's 1bpp font layout (glyph c at (c & ~7) * 32 + (c & 7) * 16, bottom half
+0x80). Every glyph is compared with every JIS X 0208 character drawn by a Japanese TrueType font;
a dynamic programme then picks the best strictly increasing assignment (the game's fonts hold the
characters they use in JIS order). OUT.tsv: code, character, score (0-1; below ~0.5 check by eye).
Glyphs that match nothing well get '?' (e.g. two-letter glyphs like 'Yu').
"""
import argparse
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

TTF = '/mnt/c/Windows/Fonts/BIZ-UDGothicR.ttc'
FONTS = '/mnt/c/Windows/Fonts/'
RENDERS = [(FONTS + 'BIZ-UDGothicR.ttc', 14), (FONTS + 'BIZ-UDGothicR.ttc', 16), (FONTS + 'BIZ-UDGothicB.ttc', 15),
           (FONTS + 'YuGothM.ttc', 15), (FONTS + 'BIZ-UDMinchoM.ttc', 15)]


def jis_chars():
    out = []
    for hi in list(range(0x81, 0xa0)) + list(range(0xe0, 0xeb)):
        for lo in range(0x40, 0xfd):
            if lo == 0x7f:
                continue
            try:
                ch = bytes([hi, lo]).decode('shift_jis')
            except UnicodeDecodeError:
                continue
            out.append(ch)
    return out


def glyph(font, c):
    base = (c & ~7) * 32 + (c & 7) * 16
    a = np.zeros((16, 16), np.float32)
    for half in range(2):
        for t in range(2):
            for r in range(8):
                b = font[base + half * 0x80 + t * 8 + r]
                for x in range(8):
                    a[half * 8 + r, t * 8 + x] = (b >> (7 - x)) & 1
    return a


def feat(a):
    im = Image.fromarray((a * 255).astype(np.uint8)).resize((32, 32), Image.BILINEAR)
    im = im.filter(ImageFilter.GaussianBlur(1.6))
    v = np.asarray(im, np.float32).ravel()
    v = v - v.mean()
    n = np.linalg.norm(v)
    return v / n if n else v


def render(ch, f):
    im = Image.new('L', (16, 16), 0)
    d = ImageDraw.Draw(im)
    d.text((8, 8), ch, font=f, fill=255, anchor='mm')
    return np.asarray(im, np.float32) / 255


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('font')
    ap.add_argument('out')
    ap.add_argument('--first', type=lambda s: int(s, 0), default=0)
    ap.add_argument('--count', type=lambda s: int(s, 0))
    a = ap.parse_args(argv)
    data = open(a.font, 'rb').read()
    n = a.count or len(data) // 32
    codes = [c for c in range(a.first, a.first + n)]
    gl = [glyph(data, c) for c in codes]
    keep = [i for i, g in enumerate(gl) if 0 < g.sum() < 200]   # blanks and solid blocks skipped
    G = np.stack([feat(gl[i]) for i in keep])
    chars = jis_chars()
    S = None
    for ttf, size in RENDERS:
        f = ImageFont.truetype(ttf, size)
        J = np.stack([feat(render(ch, f)) for ch in chars])
        s1 = G @ J.T                                # cosine similarity, glyphs x chars
        S = s1 if S is None else np.maximum(S, s1)
    skip = 0.2                                     # score for leaving a glyph unidentified
    ng, nj = S.shape
    best = np.full((ng + 1, nj + 1), -1e9, np.float32)
    best[0, :] = 0
    back = np.zeros((ng + 1, nj + 1), np.int8)      # 1 = matched at j-1, 2 = carried from j-1, 3 = skip
    for i in range(1, ng + 1):
        row = best[i - 1]
        m = np.full(nj + 1, -1e9, np.float32)
        m[1:] = row[:-1] + S[i - 1]
        sk = row + skip
        cur = np.maximum(m, sk)
        how = np.where(m >= sk, 1, 3).astype(np.int8)
        # carry: best[i][j] = max(cur[j], best[i][j-1])
        acc = np.maximum.accumulate(cur)
        carried = acc > cur
        how[carried] = 2
        best[i] = acc
        back[i] = how
    res = {}
    i, j = ng, nj
    while i > 0:
        h = back[i, j]
        if h == 2:
            j -= 1
        elif h == 1:
            res[keep[i - 1]] = (chars[j - 1], float(S[i - 1, j - 1]))
            i -= 1
            j -= 1
        else:
            res[keep[i - 1]] = ('?', float(S[i - 1].max()))
            i -= 1
    with open(a.out, 'w', encoding='utf-8') as fo:
        for k, c in enumerate(codes):
            ch, sc = res.get(k, (' ' if gl[k].sum() == 0 else '■', 1.0))
            fo.write(f'{c:03X}\t{ch}\t{sc:.2f}\n')
    low = [(codes[k], v) for k, v in res.items() if v[1] < 0.5]
    print(f'{a.out}: {len(codes)} glyphs, {len(low)} below 0.5')


if __name__ == '__main__':
    main()
