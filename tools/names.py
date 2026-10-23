#!/usr/bin/env python3
"""Names: the names font (packed at $90:8000, 8-bit codes) and the name records (build step).

  names.py stats         letter pairs needed, records that don't fit
  names.py sheet OUT.png the new names font (Pillow)

The game draws wrestler names (speaker labels in the dialogue, the select screens, ...) from a
separate 16x16 font with 8-bit codes, unpacked from $90:8000 into $7F:2000 by the screens that use
it (about 30 loaders, `LDA #$0090 / STA $32` with `LDA #$8000 / STA $30`). Records: 8 codes + $FF
(full and ring names, file 0x7de0a-0x7e3a0) or 4 codes + $FF (short names, 0x7e3a6-0x7e580); code
$00 is a blank glyph and is skipped where names are packed together (speaker labels).

English: two 8-pixel letters (tools/font8.py) per glyph. translation/names.tsv holds the English
for every record (16 or 8 letters). Each name may start one letter to the right when that lets it
share letter pairs with other names (a greedy search, deterministic); the distinct pairs get codes
1.. (at most 254). The new font is packed (tools/kpack.py) into bank NAMES_BANK and every loader
is pointed there.
"""
import collections
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import font8  # noqa: E402
import kpack  # noqa: E402
import paths  # noqa: E402
import snes  # noqa: E402

NAMES_TSV = paths.TRANSLATION / 'names.tsv'
NAMES_BANK = 0xE0            # $E0:8000; the script uses $D1-$DF (tools/hooks.py)
GLYPHS = 256
MAX_CODE = 0xFE              # most screens render names from the whole font ($8C:A89F)
ROSTER_CODE = 0xBF           # the Exhibition / League / Tournament screens copy only the first $C0
                             # glyphs to VRAM ($8E:A5AE, $8C:A99E): pairs of the names they show (real,
                             # ring and short names) get the low codes; higher codes show up as stray
                             # tiles there. Only the ring name choices (0x7e281-) may use $C0-$FE.
# The player's ring name (one of the choices at 0x7e281-) and short name (one of the parts at
# 0x7e4e1-) show on those screens too (Champion Road's Practice Match uses the Exhibition screen),
# so the choices and parts count as roster names.
ROSTER = ((0x7de0a, 0x7e3a1), (0x7e3a6, 0x7e581))
UPPERCASE = True             # mixed case needs ~230 letter pairs, capitals 184: names are drawn in
                             # capitals (translation/names.tsv keeps the readable spelling)
# Short names and ring name parts are never shifted (the roster screens list them in a column).
# Unshifted, the roster screens would need 211 pairs; real names, ring names and the ring name
# choices may start one letter right when that saves a pair, which brings them to at most $BF. (An
# odd-length name has a half-blank glyph either way: at the end unshifted, at the start shifted.)
NO_SHIFT = ((0x7e3a6, 0x7e581),)


def shiftable(off, w, en):
    return len(en) + 1 <= w and not any(a <= off < b for a, b in NO_SHIFT)


def records(path=NAMES_TSV):
    out = []
    up = str.upper if UPPERCASE else str
    for line in path.read_text(encoding='utf-8').splitlines():
        if line.startswith('#') or not line.strip():
            continue
        off, w, jp, en = (line.split('\t') + [''])[:4]
        out.append((int(off, 16), int(w), jp, up(en)))
    return out


def _pairs(e, w, sh):
    s = (' ' * sh + e).ljust(w)
    return [s[i:i + 2] for i in range(0, w, 2)]


def layout(recs, shift=True):
    """Shift (0 or 1) per record minimising distinct letter pairs; returns (shifts, pair list)."""
    names = [(w, e) for _, w, _, e in recs]
    can = [shift and shiftable(o, w, e) for o, w, _, e in recs]
    best = None
    for trial in range(60):
        rnd = random.Random(trial)
        sh = [rnd.randint(0, 1) if c else 0 for c in can]
        for _ in range(10):
            cnt = collections.Counter(p for (w, e), s in zip(names, sh) for p in _pairs(e, w, s) if p != '  ')
            changed = False
            for i, (w, e) in enumerate(names):
                for p in _pairs(e, w, sh[i]):
                    if p != '  ':
                        cnt[p] -= 1
                opts = [0, 1] if can[i] else [0]
                bs = min(opts, key=lambda s: (sum(1 for p in _pairs(e, w, s) if p != '  ' and cnt[p] <= 0), s))
                changed |= bs != sh[i]
                sh[i] = bs
                for p in _pairs(e, w, sh[i]):
                    if p != '  ':
                        cnt[p] += 1
            if not changed:
                break
        used = sorted(p for p, c in cnt.items() if c > 0)
        if best is None or len(used) < len(best[1]):
            best = (sh[:], used)
    return best


def build(recs, max_code=MAX_CODE, shift=False, what='names'):
    """(record bytes {offset: bytes}, font bytes 0x2000 = 256 glyphs, pairs)."""
    for off, w, jp, en in recs:
        if len(en) > w:
            raise SystemExit(f'{what}: {en!r} at {off:#x} is longer than {w} letters')
        bad = set(en) - set(font8.CODES)
        if bad:
            raise SystemExit(f'{what}: {en!r}: characters not in the font {bad}')
    if what == 'names':
        # minimise the pairs of the roster screens' names first; the rest are not shifted
        on = [any(a <= off < b for a, b in ROSTER) for off, _, _, _ in recs]
        sub_shifts, _ = layout([r for r, o in zip(recs, on) if o], True)
        it = iter(sub_shifts)
        shifts = [next(it) if o else 0 for o in on]
        used = sorted({p for (off, w, jp, en), sh in zip(recs, shifts) for p in _pairs(en, w, sh) if p != '  '})
    else:
        shifts, used = layout(recs, shift)
    if len(used) > max_code:
        raise SystemExit(f'{what}: {len(used)} letter pairs, codes 1-${max_code:02X} hold {max_code}')
    low = {p for (off, w, jp, en), sh in zip(recs, shifts) if what == 'names'
           and any(a <= off < b for a, b in ROSTER) for p in _pairs(en, w, sh) if p != '  '}
    if len(low) > ROSTER_CODE:
        raise SystemExit(f'{what}: the roster names need {len(low)} letter pairs, codes 1-${ROSTER_CODE:02X}')
    used = sorted(used, key=lambda p: p not in low)
    code = {'  ': 0}
    code.update({p: i + 1 for i, p in enumerate(used)})
    out = {}
    for (off, w, jp, en), sh in zip(recs, shifts):
        out[off] = bytes(code[p] for p in _pairs(en, w, sh)) + b'\xff'
    f8 = font8.glyph_bytes()
    font = bytearray(GLYPHS * 32)
    for p, c in code.items():
        base = (c & ~7) * 32 + (c & 7) * 16
        for t, ch in enumerate(p):
            g = f8[font8.CODES[ch] * 16:font8.CODES[ch] * 16 + 16]
            for r in range(8):
                font[base + t * 8 + r] = g[r]
                font[base + 0x80 + t * 8 + r] = g[8 + r]
    return out, bytes(font), used


def loaders(data):
    """File offsets of the bank byte in every `LDA #$0090 / STA $32` that loads the names font."""
    out = []
    i = data.find(b'\xa9\x90\x00\x85\x32')
    while i != -1:
        if b'\xa9\x00\x80\x85\x30' in data[i - 12:i + 17]:
            out.append(i + 1)
        i = data.find(b'\xa9\x90\x00\x85\x32', i + 1)
    return out


def apply(rom):
    """Install the English names into `rom` (bytearray, expanded)."""
    recs = records()
    recbytes, font, used = build(recs)
    for off, b in recbytes.items():
        n = 9 if len(b) == 9 else 5
        if rom[off + n - 1] != 0xFF and not (rom[off:off + n - 1].count(0) == n - 1):
            raise SystemExit(f'names: record at {off:#x} is not a {n}-byte record')
        rom[off:off + len(b)] = b
    packed = kpack.pack(font)
    r = snes.Rom(rom)
    o = r.to_file((NAMES_BANK << 16) | 0x8000)
    if any(rom[o:o + len(packed)]) and set(rom[o:o + len(packed)]) != {0xFF}:
        raise SystemExit(f'names: bank ${NAMES_BANK:02X} is not free')
    rom[o:o + len(packed)] = packed
    sites = loaders(bytes(rom))
    for s in sites:
        rom[s] = NAMES_BANK
    return len(recbytes), len(used), len(sites), len(packed)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    recs = records()
    if argv[:1] == ['stats']:
        recbytes, font, used = build(recs)
        print(f'{len(recs)} records, {len(used)} letter pairs, packed font {len(kpack.pack(font))} bytes')
    elif argv[:1] == ['sheet'] and len(argv) == 2:
        from PIL import Image
        _, font, used = build(recs)
        im = Image.new('L', (16 * 16, 16 * 16), 40)
        for c in range(GLYPHS):
            base = (c & ~7) * 32 + (c & 7) * 16
            for half in range(2):
                for t in range(2):
                    for y in range(8):
                        b = font[base + half * 0x80 + t * 8 + y]
                        for x in range(8):
                            if b & (0x80 >> x):
                                im.putpixel(((c % 16) * 16 + t * 8 + x, (c // 16) * 16 + half * 8 + y), 255)
        im.resize((im.width * 3, im.height * 3), Image.NEAREST).save(argv[1])
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
