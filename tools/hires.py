#!/usr/bin/env python3
"""Hi-res screen labels: strings drawn one 16x16 cell per code by $8C:AA1B (build step).

  hires.py dump SCREEN             write translation/text/hires_SCREEN.txt from the ROM

On the mode 5 screens (status, ...) a code is one 16x16 tile of a font only that screen loads; in
hi-res such a cell is 8 normal pixels wide, as wide as an English letter of the dialogue. A call
site looks like
  LDA #pos / CLC / ADC $16FC / STA $16FE / ... / LDA #bank / STA $3A / LDA #addr / STA $38 /
  STZ $3C / JSL $8CAA1B
and value strings (logic type, ...) are copied from 16-bit pointer tables into $7E:F1A1 first.

English: the screen's font is rebuilt: the slots in 'keep' (blank, digits, ...) stay, the others
get the letters the English strings use (tools/font8.py, every pixel doubled in width). All
strings of the screen move to STR_BANK, their call sites and tables are repointed, and a label may
move ('col=N' in the @ line; other sites of the string move as far) or be padded with blanks ('width=N'). Strings in 'tables' may be up to 'copy' - 1 letters.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blocks  # noqa: E402
import font8  # noqa: E402
import glyphstr  # noqa: E402
import kpack  # noqa: E402
import paths  # noqa: E402
import snes  # noqa: E402

STR_BANK = 0xF0

SCREENS = {
    # wrestler status screen (info menu, Exhibition X button): font $91:EFD8, 80 slots via DMA
    'status': {
        'font': 0x91EFD8, 'font_bank': 0xF1, 'slots': 0x50, 'str_at': 0x8000,
        'glyphs': (' ー0123456789HPげさびアクシジスタットパベマリルロワン安価回関器技均筋空型撃御攻根殺持出準称身'
                   '性節前速打体値中定度投突飛必標評復平保防本名用略力'),
        'keep': list(range(0x0C)),       # blank, ー, digits 0-9 ($8A:C51D maps digits here)
        'regions': [(0x8AC4B8, 0x8AC565)],  # every string of the screen
        # (pointer table, entries, copy loop's CPX #n, the LDA #bank after the table load)
        'tables': [(0x8AC0FA, 4, 0x8AB9AC, 0x8AB997), (0x8AC102, 3, 0x8AB9F5, 0x8AB9E0)],
        'copy': 8,
        # move list rows (LDA #$0291.. / ADC $16FC): column 17 -> 18, clear of the tab labels
        'patches': [(a + 1, bytes([(0x91 + 0x20 * k + 1) & 0xFF]))
                    for k, a in enumerate(range(0x8ABF71, 0x8AC008, 0x1E))],
    },
    # logic pattern screen and the info menu's box: glyph set $91:DC15, shared with the save/load
    # screens (tools/glyphstr.py 'data'), so the letters take the slots glyphstr leaves free
    'logic': {
        'shared': 'data', 'str_at': 0x9000, 'planes_slot': 5,
        'regions': [(0x8B8983, 0x8B89C0), (0x8BCD1D, 0x8BCD7D)],
        'tables': [(0x8B8704, 4, 0x8B862E, 0x8B8619), (0x8B870C, 3, 0x8B8678, 0x8B8663),
                   (0x8BC3C2, 3, 0x8BC3AA, 0x8BC395), (0x8BC4A5, 8, 0x8BC48D, 0x8BC478)],
        'copy': 8,
        'patches': [(0x8BC462, b'\x17'),    # option grid: right column from cell 24 to 23
                    (0x8B8635, b'\xec'),    # info box: logic type from cell 11 to 12 (hair covers 5)
                    (0x8B867F, b'\xf6')],   # info box: tag style from cell 23 to 22 (Normal clears the frame)
    },
    # stat-up screen (BP spending; not yet seen in play): glyph set $92:9416, shared with the
    # select screens (tools/glyphstr.py 'select')
    'statsup': {
        'shared': 'select', 'str_at': 0xA800, 'planes_slot': 6,
        'regions': [(0x8AFF4B, 0x8AFFC0)],
        'tables': [],
        'copy': 8,
    },
    # World Circuit member selection: font $92:DE21 (64 slots via DMA, one loader)
    'circuit': {
        'font': 0x92DE21, 'font_bank': 0xF9, 'slots': 0x40, 'str_at': 0xB000,
        'glyphs': ' ーー0123456789BDEIPTYikuいさしてめをアクズドニハバメリルワンヶ下革規軍決残子市女消新正合団定日費本命龍',
        'keep': list(range(0x0D)),       # blank, ー, ー, digits
        'regions': [(0x8BB0D1, 0x8BB174)],
        'tables': [],
        'copy': 8,
    },
    # World Circuit rivals (敵データ): font $92:EC3C, $30 slots via DMA ($40+ hold the names, $70+
    # the finishers). A row: assist style, +1, logic style, +7 (now +1), best move type and
    # attack / defense / even (tables of 16-bit pointers drawn without a copy)
    'rivals': {
        'font': 0x92EC3C, 'font_bank': 0xFC, 'slots': 0x30, 'str_at': 0xC000,
        'glyphs': ' ・0123456789アイシスタトパプマワン安関均型撃御攻準打定投突飛標平防',
        'keep': list(range(0x0C)),       # blank, ・, digits
        'regions': [(0x8BD578, 0x8BD5B8)],
        'tables': [(0x8BD523, 3, None, 0x8BD3C0), (0x8BD529, 4, None, 0x8BD3E9),
                   (0x8BD4F9, 10, None, 0x8BD48C)],
        'copy': 8,
        'patches': [(0x8BD406, b'\x01')],   # after the logic style: 7 cells -> 1
    },
    # Open League / Open Tournament: チーム1-8 labels, font $92:E8D8 (24 slots, one loader)
    'league': {
        'font': 0x92E8D8, 'font_bank': 0xF5, 'slots': 0x18, 'str_at': 0xA000,
        'glyphs': ' ー12345678Xでタチボムン値能力',
        'keep': list(range(0x0A)),       # blank, ー, digits 1-8
        'regions': [(0x8EE7B7, 0x8EE7E8)],
        'tables': [(0x8EBF31, 8, None, 0x8EBECA)],
        'copy': 8,
        'shift': 2,                      # letters up to 2 pixels into their cells, off the screen's edge
        'patches': [(0x8EBEB7, b'\x20'),    # labels from cell 2 to 0 ...
                    (0x8EBEDC, b'\x3a')],   # ... and the next row's start: 64 - 6 cells
    },
}

POS = re.compile(rb'\xa9(..)\x18\x6d\xfc\x16\x8d\xfe\x16', re.S)
SITE = re.compile(rb'\xa9(.)\x00\x85\x3a\xa9(..)\x85\x38(?:\x64\x3c|\xa9..\x85\x3c)\x22\x1b\xaa\x8c', re.S)


def to_off(addr):
    return ((addr >> 16) & 0x7F) * 0x8000 + (addr & 0x7FFF)


def to_cpu(off):
    return 0x800000 | ((off // 0x8000) << 16) | 0x8000 | (off % 0x8000)


def strings(data, cfg):
    """[(CPU address, bytes)] of the $FF-ended strings in the screen's regions."""
    out = []
    for a, end in cfg['regions']:
        while a < end:
            o = to_off(a)
            e = data.find(b'\xff', o)
            out.append((a, data[o:e]))
            a += e - o + 1
    return out


def sites(data, addr):
    """[(site offset, {'bank': off, 'addr': off, 'pos': off or None})] of AA1B calls on addr."""
    out = []
    for m in SITE.finditer(data):
        a = m.group(2)[0] | m.group(2)[1] << 8
        if (m.group(1)[0] << 16 | a) != addr:
            continue
        w0 = max(0, m.start() - 24)
        pm = list(POS.finditer(data, w0, m.start()))
        out.append((m.start(), {'bank': m.start() + 1, 'addr': m.start() + 6,
                                'pos': pm[-1].start() + 1 if pm else None}))
    return out


def text_path(name):
    return paths.TRANSLATION / 'text' / f'hires_{name}.txt'


def decode(b, glyphs):
    return ''.join(glyphs[x] if x < len(glyphs) else '{%02X}' % x for x in b)


def dump(name):
    data = paths.ROM.read_bytes()
    cfg = SCREENS[name]
    tab = {}
    for t, n, _, _ in cfg['tables']:
        for i in range(n):
            o = to_off(t) + 2 * i
            tab[(t & 0xFF0000) | data[o] | data[o + 1] << 8] = f'table={t:06X}'
    lines = [f'# hires_{name}: one letter per cell (tools/hires.py). "col=N" moves a label (32 cells a row).', '']
    for a, b in strings(data, cfg):
        s = sites(data, a)
        meta = tab.get(a) or ('sites=' + ','.join(f'{to_cpu(o):06X}' for o, _ in s))
        if s and s[0][1]['pos'] is not None:
            p = data[s[0][1]['pos']] | data[s[0][1]['pos'] + 1] << 8
            meta += f' row={p // 32} col={p % 32}'
        g = glyphstr.SETS[cfg['shared']]['glyphs'] if 'shared' in cfg else cfg['glyphs']
        lines += [f'@ {a:06X} {meta}', 'JP ' + decode(b, g), '']
    text_path(name).write_text('\n'.join(lines), encoding='utf-8', newline='\n')
    print(paths.show(text_path(name)))


def letter_tiles(ch, planes, shift=0):
    """The four 2bpp tiles (top-left, top-right, bottom-left, bottom-right) of a doubled letter."""
    f8 = font8.glyph_bytes()
    g = f8[font8.CODES[ch] * 16:font8.CODES[ch] * 16 + 16]
    used = max((8 - (b & -b).bit_length() + 1 for b in g if b), default=0)   # rightmost column + 1
    shift = min(shift, 8 - used)          # moved right, but never out of the cell
    tiles = [bytearray(16) for _ in range(4)]
    for y in range(16):
        w = 0
        for x in range(8):
            if g[y] & (0x80 >> x):
                w |= 0xC000 >> (2 * (x + shift))
        for half in range(2):
            b = (w >> (8 * (1 - half))) & 0xFF
            t = tiles[(y // 8) * 2 + half]
            t[2 * (y % 8)] = b if planes[0] else 0
            t[2 * (y % 8) + 1] = b if planes[1] else 0
    return tiles


def apply(rom, name):
    cfg = SCREENS[name]
    path = text_path(name)
    if not path.exists():
        return 0, 0
    data = bytes(rom)
    bf = blocks.BlockFile(path)
    todo = {int(b.id, 16): b for b in bf.blocks}
    if not any(b.english for b in todo.values()):
        return 0, 0
    shared = cfg.get('shared')
    if shared:                           # full slots whose two cells glyphstr left free
        left = set(glyphstr.LEFT.get(shared, []))
        free = [n for n in range(0x7F) if 2 * n in left and 2 * n + 1 in left]
        tb = (glyphstr.SETS[shared]['tiles_bank'] << 16) | 0x8000
        keep = set(range(256)) - set(free)
    else:
        keep = set(cfg['keep'])
        free = [n for n in range(cfg['slots']) if n not in keep]
        tb = cfg['font']
    tables = {}
    for t, cnt, _, _ in cfg['tables']:
        for i in range(cnt):
            o = to_off(t) + 2 * i
            tables[(t & 0xFF0000) | data[o] | data[o + 1] << 8] = t
    # every string's text: English, or the JP text when only kept glyphs are used
    texts = {}
    for a, b in strings(data, cfg):
        blk = todo.get(a)
        if blk and blk.english:
            texts[a] = ' '.join(blk.english)
            w = re.search(r'\bwidth=(\d+)', blk.meta)
            if w:                        # padded: the next string follows at the cursor
                if len(texts[a]) > int(w.group(1)):
                    raise SystemExit(f'hires_{name} @{a:06X}: more than {w.group(1)} letters')
                texts[a] = texts[a].ljust(int(w.group(1)))
        elif set(b) <= keep:
            texts[a] = b
        elif sites(data, a) or a in tables:
            raise SystemExit(f'hires_{name} @{a:06X}: needs English (its glyphs are replaced)')
    kept = {} if shared else {cfg['glyphs'][n]: n for n in keep if n and n < len(cfg['glyphs'])}
    chars = sorted({c for t in texts.values() if isinstance(t, str) for c in t} - {' '} - set(kept))
    bad = set(chars) - set(font8.CODES)
    if bad:
        raise SystemExit(f'hires_{name}: characters not in the font: {"".join(sorted(bad))}')
    if len(chars) > len(free):
        raise SystemExit(f'hires_{name}: {len(chars)} letters, {len(free)} free slots')
    code = {' ': 0}
    code.update({ch: free[i] for i, ch in enumerate(chars)})
    letters = dict(code)                 # the glyphs to draw
    code.update(kept)                    # digits etc. the font already has
    # font
    r = snes.Rom(rom)
    tiles, _ = kpack.unpack(bytes(rom) if shared else data, r.to_file(tb) if shared else to_off(tb))
    tiles = bytearray(tiles)
    planes = (True, False)
    ps = cfg.get('planes_slot', 2)       # the colour of the glyphs: the planes a digit 0 uses
    pt = (ps & 7) * 2 + (ps >> 3) * 32
    for y in range(8):
        p0, p1 = tiles[pt * 16 + 2 * y], tiles[pt * 16 + 2 * y + 1]
        if p0 or p1:
            planes = (bool(p0), bool(p1))
    if not shared:
        for n in free:
            base = (n & 7) * 2 + (n >> 3) * 32
            for k in (0, 1, 16, 17):
                tiles[(base + k) * 16:(base + k) * 16 + 16] = bytes(16)
    for ch, n in letters.items():
        if n == 0:
            continue
        base = (n & 7) * 2 + (n >> 3) * 32
        for k, t in zip((0, 1, 16, 17), letter_tiles(ch, planes, cfg.get('shift', 0))):
            tiles[(base + k) * 16:(base + k) * 16 + 16] = t
    packed = kpack.pack(bytes(tiles))
    if shared:
        fo = r.to_file(tb)
        rom[fo:fo + len(packed)] = packed
    else:
        fo = r.to_file((cfg['font_bank'] << 16) | 0x8000)
        rom[fo:fo + len(packed)] = packed
        fb = cfg['font']
        pat = bytes([0xA0, fb & 0xFF, (fb >> 8) & 0xFF, 0xA9, fb >> 16])
        loaders = [m.start() for m in re.finditer(re.escape(pat), data)]
        if not loaders:
            raise SystemExit(f'hires_{name}: no loader of ${fb:06X}')
        for i in loaders:
            rom[i + 1:i + 3] = bytes([0x00, 0x80])
            rom[i + 4] = cfg['font_bank']
    for a, b in cfg.get('patches', []):
        rom[to_off(a):to_off(a) + len(b)] = b
    # strings
    base = r.to_file((STR_BANK << 16) | 0x8000)
    pos = cfg['str_at']
    new = {}
    for a, t in texts.items():
        body = (bytes(code[c] for c in t) if isinstance(t, str) else bytes(t)) + b'\xff'
        rom[base + pos - 0x8000:base + pos - 0x8000 + len(body)] = body
        new[a] = (pos, len(body) - 1)
        pos += len(body)
    if pos > cfg['str_at'] + 0x1000:
        raise SystemExit(f'hires_{name}: strings overrun their 4 KB area')
    nsites = 0
    for a, (p, n) in new.items():
        blk = todo.get(a)
        col = re.search(r'\bcol=(\d+)', blk.meta) if blk else None
        shift = None                    # col= names the first site's column; the others move as far
        for _, at in sites(data, a):
            rom[at['addr']:at['addr'] + 2] = p.to_bytes(2, 'little')
            rom[at['bank']] = STR_BANK
            if col and at['pos'] is not None:
                old = data[at['pos']] | data[at['pos'] + 1] << 8
                if shift is None:
                    shift = int(col.group(1)) - (old & 31)
                rom[at['pos']:at['pos'] + 2] = ((old & ~31) | ((old & 31) + shift) & 31).to_bytes(2, 'little')
            nsites += 1
    if cfg['tables'] and cfg['copy'] % 2:
        raise SystemExit(f'hires_{name}: copy must be even (the loops copy words)')
    for t, cnt, cpx, ldab in cfg['tables']:
        to = to_off(t)
        if (cpx and data[to_off(cpx)] != 0xE0) or data[to_off(ldab)] != 0xA9 or data[to_off(ldab) + 1] != t >> 16:
            raise SystemExit(f'hires_{name}: table ${t:06X}: unexpected code')
        for i in range(cnt):
            a = (t & 0xFF0000) | data[to + 2 * i] | data[to + 2 * i + 1] << 8
            p, n = new[a]
            if cpx and n >= cfg['copy']:
                raise SystemExit(f'hires_{name} @{a:06X}: {n} letters, at most {cfg["copy"] - 1}')
            rom[to + 2 * i:to + 2 * i + 2] = p.to_bytes(2, 'little')
            nsites += 1
        if cpx:
            rom[to_off(cpx) + 1:to_off(cpx) + 3] = cfg['copy'].to_bytes(2, 'little')
        rom[to_off(ldab) + 1] = STR_BANK
    return len(texts), nsites


def main(argv=None):
    argv = paths.configure(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ['dump'] and len(argv) == 2:
        dump(argv[1])
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
