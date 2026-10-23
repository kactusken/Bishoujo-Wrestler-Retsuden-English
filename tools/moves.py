#!/usr/bin/env python3
"""Move names: the move font (packed at $90:9962, 8-bit codes) and the move records (build step).

  moves.py stats         letter pairs needed, and the layout chosen for each record

105 records of 12 codes + $FF at file 0x7e691. Two ways to draw them:
- the status screen renders records into tiles with $8C:A89F (like the names font);
- the move screens (Learn, Move Difficulty, Finisher) convert the first $80 glyphs into VRAM with
  $8C:A99E (four loaders: `LDA #$0080 / STA $1BEC`, a $2000-byte DMA to VRAM + $0600 words) and
  draw a record's codes as glyph slots + $30 (`LDA #$0030 / STA $3C`, four sites) after the 48
  slots of their label set ($92:8B38). Slots up to $BF are free, so codes must stay below $90.

English: the same letter pairs in capitals as the names (tools/names.py), 24 letters a record.
The move screens' labels (translation/movelabels.tsv) are written in the same pairs. Records
start at their first letter (the lists stay aligned) and may put two spaces between words when
that saves pairs; labels too (a deterministic search). To fit
the pairs, the move screens load the font from slot $18 (whole rows of 8 glyphs; the label set
keeps its first $14 slots: symbols, digits, B, P) up to slot $CF: slots $C0-$C7 hold the
wrestler's name (codes NAME_CODES unused). The name renderer uploads 16 glyphs to $C0-$CF (the
name and 8 stale ones): NAME_HOOK copies the converted pairs of $C8-$CF ($7F:8000 + row) into
the second half of its buffer ($7F:C200) before the upload. Pairs only the labels
use go into label set slots no English string needs (LABEL_SLOTS; repacked into LABEL_BANK).
"""
import collections
import itertools
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import font8  # noqa: E402
import kpack  # noqa: E402
import names  # noqa: E402
import paths  # noqa: E402
import snes  # noqa: E402

MOVES_TSV = paths.TRANSLATION / 'moves.tsv'
LABELS_TSV = paths.TRANSLATION / 'movelabels.tsv'
MOVES_BANK = 0xF2
FONT = 0x909962
SLOT = 0x18                  # first glyph slot of the font on the move screens (was $30)
MAX_CODE = 0xCF - SLOT       # slots $D0+ hold big digits and frames
NAME_CODES = range(0xC0 - SLOT, 0xC8 - SLOT)    # slots $C0-$C7: the wrestler's name
NAME_SITES = [0x8B8E44, 0x8D9675, 0x8DAD13, 0x8DBCF0]     # JSL $8CA89F, the name (16 glyphs)
NAME_HOOK = 0xFDF000
# Letters one pixel right: in hi-res the even columns come from the main screen, which the move
# screens darken by colour math (unaffordable moves turned dark red); the strokes go to the odd ones
SHIFT = 1
LABEL_SET = 0x928B38         # the move screens' label set (2bpp, 48 slots, one loader)
LABEL_BANK = 0xFD
LABEL_SLOTS = [0x14, 0x15, 0x16, 0x17, 0x05, 0x06]     # its ア ォ ギ ッ 《 》: no map shows them
VRAM_LOADERS = [0x8B8A2D, 0x8D927E, 0x8DA91B, 0x8DB8F8]     # LDA #$0080 / STA $1BEC
PARAM_SITES = [0x8B8F86, 0x8B9260, 0x8B9301, 0x8D9B5F]      # LDA #$0030 / STA $3C


def to_off(addr):
    return ((addr >> 16) & 0x7F) * 0x8000 + (addr & 0x7FFF)


def records():
    return names.records(MOVES_TSV)


def labels():
    out = []
    for line in LABELS_TSV.read_text(encoding='utf-8').splitlines():
        if line.startswith('#') or not line.strip():
            continue
        addr, n, jp, en = (line.split('\t') + [''])[:4]
        out.append((int(addr, 16), int(n), jp, en.upper()))
    return out


def _options(e, w, leads=(0, 1)):
    """Layouts of a text in w letters: lead in `leads`, one or two spaces between words."""
    if not e.strip():
        return ['']
    ws = e.split(' ')
    out = []
    for lead in leads:
        for gaps in itertools.product((1, 2), repeat=len(ws) - 1):
            s = ' ' * lead + ws[0] + ''.join(' ' * g + x for g, x in zip(gaps, ws[1:]))
            if len(s) <= w and s not in out:
                out.append(s)
    if not out:
        raise SystemExit(f'moves: {e!r} is longer than {w} letters')
    return out


def _pairs(s):
    s = s + ' ' * (len(s) % 2)
    return [s[i:i + 2] for i in range(0, len(s), 2) if s[i:i + 2] != '  ']


def layout(texts):
    """texts: [(text, width, leads)] -> (chosen layouts, sorted pairs), fewest distinct pairs
    (simulated annealing from fixed seeds: the same result every build)."""
    opts = [_options(e, w, leads) for e, w, leads in texts]
    sets = [[set(_pairs(s)) for s in o] for o in opts]
    best = None
    for trial in range(6):
        rnd = random.Random(trial)
        ch = [rnd.randrange(len(o)) for o in opts]
        cnt = collections.Counter(p for i, o in enumerate(sets) for p in o[ch[i]])
        temp = 2.0
        for _ in range(60000):
            i = rnd.randrange(len(opts))
            j = rnd.randrange(len(opts[i]))
            if j == ch[i]:
                continue
            old, new = sets[i][ch[i]], sets[i][j]
            d = sum(1 for p in new - old if cnt[p] == 0) - sum(1 for p in old - new if cnt[p] == 1)
            if d <= 0 or rnd.random() < math.exp(-d / temp):
                for p in old:
                    cnt[p] -= 1
                for p in new:
                    cnt[p] += 1
                ch[i] = j
            temp = max(0.05, temp * 0.9999)
        used = sorted(p for p, c in cnt.items() if c > 0)
        if best is None or len(used) < len(best[1]):
            best = ([o[k] for o, k in zip(opts, ch)], used)
    return best


def build():
    recs = records()
    labs = labels()
    texts = [(e, w, (0,)) for _, w, _, e in recs] + [(e, 2 * n, (0,)) for _, n, _, e in labs]
    for e, _, _ in texts:
        bad = set(e) - set(font8.CODES)
        if bad:
            raise SystemExit(f'moves: {e!r}: characters not in the font {bad}')
    ch, used = layout(texts)
    in_recs = {p for s in ch[:len(recs)] for p in _pairs(s)}
    label_only = [p for p in used if p not in in_recs][:len(LABEL_SLOTS)]
    slot_of = dict(zip(label_only, LABEL_SLOTS))
    used = [p for p in used if p not in slot_of]
    codes = [c for c in range(1, MAX_CODE + 1) if c not in NAME_CODES]
    if len(used) > len(codes):
        raise SystemExit(f'moves: {len(used)} letter pairs, the move screens hold {len(codes)}')
    code = {'  ': 0}
    code.update({p: c for p, c in zip(used, codes)})

    def pairs_of(s, n):
        s = s.ljust(2 * n)
        return [s[i:i + 2] for i in range(0, 2 * n, 2)]
    recbytes = {off: bytes(code[p] for p in pairs_of(s, w // 2)) + b'\xff' for (off, w, _, _), s in zip(recs, ch)}
    labbytes = {a: bytes(slot_of[p] if p in slot_of else code[p] + SLOT if p != '  ' else 0
                         for p in pairs_of(s, n)) + b'\xff'
                for (a, n, _, _), s in zip(labs, ch[len(recs):])}
    f8 = font8.glyph_bytes()
    font = bytearray(names.GLYPHS * 32)
    for p, c in code.items():
        base = (c & ~7) * 32 + (c & 7) * 16
        for t, letter in enumerate(p):
            g = f8[font8.CODES[letter] * 16:font8.CODES[letter] * 16 + 16]
            for r in range(8):
                font[base + t * 8 + r] = g[r] >> SHIFT
                font[base + 0x80 + t * 8 + r] = g[8 + r] >> SHIFT
    return recbytes, labbytes, bytes(font), used, ch, slot_of


def label_set(data, slot_of):
    """The label set with the label-only pairs in their slots (colour 1, like its digits)."""
    tiles = bytearray(kpack.unpack(data, to_off(LABEL_SET))[0])
    f8 = font8.glyph_bytes()
    for p, n in slot_of.items():
        t0 = (n >> 3) * 32 + (n & 7) * 2
        for half, letter in enumerate(p):
            g = f8[font8.CODES[letter] * 16:font8.CODES[letter] * 16 + 16]
            for k, rows in ((0, g[:8]), (16, g[8:])):
                t = t0 + half + k
                tiles[t * 16:t * 16 + 16] = b''.join(bytes([r >> SHIFT, 0]) for r in rows)
    for n in LABEL_SLOTS:
        if n not in slot_of.values():                   # unused: blank
            t0 = (n >> 3) * 32 + (n & 7) * 2
            for t in (t0, t0 + 1, t0 + 16, t0 + 17):
                tiles[t * 16:t * 16 + 16] = bytes(16)
    return kpack.pack(bytes(tiles))


def loaders(data):
    """File offsets of each `LDA #$9962 / STA $30` that has an `LDA #$0090 / STA $32` next to it."""
    lo = bytes([0xA9, FONT & 0xFF, (FONT >> 8) & 0xFF, 0x85, 0x30])
    bank = bytes([0xA9, FONT >> 16, 0x00, 0x85, 0x32])
    out = []
    i = data.find(lo)
    while i != -1:
        if data[i + 5:i + 10] == bank:
            out.append((i, i + 5))
        elif data[i - 5:i] == bank:
            out.append((i, i - 5))
        i = data.find(lo, i + 1)
    return out


def apply(rom):
    data = bytes(rom)
    recbytes, labbytes, font, used, _, slot_of = build()
    for off, b in recbytes.items():
        if rom[off + 12] != 0xFF:
            raise SystemExit(f'moves: record at {off:#x} is not a 13-byte record')
        rom[off:off + 13] = b
    for a, b in labbytes.items():
        o = to_off(a)
        if rom[o + len(b) - 1] != 0xFF:
            raise SystemExit(f'moves: label ${a:06X} is not {len(b) - 1} codes')
        rom[o:o + len(b)] = b
    packed = kpack.pack(font)
    r = snes.Rom(rom)
    o = r.to_file((MOVES_BANK << 16) | 0x8000)
    rom[o:o + len(packed)] = packed
    packed = label_set(data, slot_of)
    o = r.to_file((LABEL_BANK << 16) | 0x8000)
    rom[o:o + len(packed)] = packed
    ls = data.find(bytes([0xA0, LABEL_SET & 0xFF, (LABEL_SET >> 8) & 0xFF, 0xA9, LABEL_SET >> 16]))
    if ls < 0:
        raise SystemExit('moves: no loader of the label set')
    rom[ls + 1:ls + 3] = b'\x00\x80'
    rom[ls + 4] = LABEL_BANK
    row = 0x8000 + ((0xC8 - SLOT) >> 3) * 0x200          # converted pairs of slots $C8-$CF
    hook = (b'\x22\x9f\xa8\x8c'                         # JSL $8CA89F: render the name
            b'\x08\xc2\x30\x8b'                         # PHP / REP #$30 / PHB
            + b'\xa2' + row.to_bytes(2, 'little')        # LDX #row
            + b'\xa0\x00\xc2\xa9\xff\x01'                 # LDY #$C200 / LDA #$01FF
            b'\x54\x7f\x7f\xab\x28\x6b')                 # MVN $7F,$7F / PLB / PLP / RTL
    o = r.to_file(NAME_HOOK)
    rom[o:o + len(hook)] = hook
    for a in NAME_SITES:
        o = to_off(a)
        if data[o:o + 4] != b'\x22\x9f\xa8\x8c' or data[o - 5:o - 2] != b'\x10\x00\x8d':
            raise SystemExit(f'moves: unexpected code at the name render ${a:06X}')
        rom[o + 1:o + 4] = NAME_HOOK.to_bytes(3, 'little')
    sites = loaders(data)
    for lo, bank in sites:
        rom[lo + 1:lo + 3] = b'\x00\x80'
        rom[bank + 1] = MOVES_BANK
    # move screens: the font from slot SLOT, MAX_CODE + 1 glyphs
    n = MAX_CODE + 1
    for a in VRAM_LOADERS:
        o = to_off(a)
        dma = data.find(b'\xa0\x00\x20\x8c\x05\x43', o, o + 40)     # LDY #$2000 / STY $4305
        dest = data.find(b'\x69\x00\x06\x8d\x16\x21', o, o + 60)    # ADC #$0600 / STA $2116
        if data[o:o + 6] != b'\xa9\x80\x00\x8d\xec\x1b' or dma < 0 or dest < 0:
            raise SystemExit(f'moves: unexpected code at the loader ${a:06X}')
        rom[o + 1] = n
        rom[dma + 1:dma + 3] = (n * 64).to_bytes(2, 'little')
        rom[dest + 1:dest + 3] = (SLOT * 32).to_bytes(2, 'little')
    for a in PARAM_SITES:
        o = to_off(a)
        if data[o:o + 5] != b'\xa9\x30\x00\x85\x3c':
            raise SystemExit(f'moves: unexpected code at ${a:06X}')
        rom[o + 1] = SLOT
    return len(recbytes), len(used), len(sites)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ['stats']:
        recbytes, labbytes, font, used, ch, slot_of = build()
        print(f'{len(recbytes)} records, {len(labbytes)} labels, {len(used)} letter pairs '
              f'(at most {MAX_CODE - len(NAME_CODES)}) + {len(slot_of)} in the label set, '
              f'packed font {len(kpack.pack(font))} bytes')
        for s in ch:
            if s.strip():
                print(repr(s))
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
