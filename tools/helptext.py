#!/usr/bin/env python3
"""Glyph-index messages: short help texts drawn from a screen's own tile set (build step).

  helptext.py dump        the Japanese messages -> translation/text/<set>.txt (keeps EN lines)

The schedule screen ("今週のよてい") shows a 2-line help text for the selected item. Messages are
8-bit glyph indices ($FE line break, $FF end) reached through a table of 16-bit pointers in bank
$83 ($84:EA90 LDA $83F01A,X); glyph n is the 2x2 tiles (n & 7) * 2 + (n >> 3) * 32 (+1, +16, +17)
of the screen's BG3 tile set (packed at $B4:CA38, entry 2 of the 24-bit table at $89:8200), drawn
by $80:BC43 at $84:EAC4 (cursor + 2). Line 1 starts at column 8, line 2 at column 9.

English: one 8x16 letter per code, like the dialogue. A code b is one half of a glyph slot: tile
b + (b & $F0) (top) and +$10 (bottom); the hook TileH replaces the JSL at $84:EAC4 and moves the
cursor by 1. The letters are drawn into the halves of the glyph slots the Japanese messages used
(nothing else on the screen uses them); code 0 is the blank slot 0 (space). The messages and their
pointer table move to bank MSG_BANK (and the places that load a message by its address,
`LDY #addr / LDA #$0083 / STY $30 / STA $32`, are pointed there); the tile set is repacked into
TILES_BANK. Lines are padded to full width: the game redraws only as many cells as the text has.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import asm65816  # noqa: E402
import blocks  # noqa: E402
import font8  # noqa: E402
import kpack  # noqa: E402
import paths  # noqa: E402
import snes  # noqa: E402

SETS = {
    'schedule_help': {
        'table': 0x1F01A, 'count': 28, 'bank': 0x83,
        'tiles_ptr': 0x48206,                      # 24-bit pointer to the packed tile set
        'table_read': 0x84EA90,                    # LDA $83F01A,X
        'bank_load': 0x84EA96,                     # LDA #$0083
        'tile_call': 0x84EAC4,                     # JSL $80BC43
        'widths': (22, 21),                        # letters: line 1 from column 8, line 2 from 9
    },
}
MSG_BANK = 0xE1
TILES_BANK = 0xE2
HOOK_ADDR = 0xD09400

# Glyph table of the schedule tile set, read from VRAM and checked by eye (see docs/TECHNICAL.md).
JP = ('　。？ー（）１２３４ＨＰあいえか' 'がけげこさしすせつでとのはびぶま' 'りるれをんアグシスダットニパプュ'
      'ラリレワン下化回覚関器技強筋空撃' '御攻更行合根殺散試実取受習昇上寝' '身性整節選速打体鍛調定度投得難白'
      '発飛必復変防遊予用力練')

HOOK = '''
.m16
.x16
TileH:                  ; replaces JSL $80BC43 in a glyph-message drawer: A = code b
  PHA
  AND #$00F0
  CLC
  ADC 1,S               ; tile = b + (b & $F0): one half of glyph slot b >> 1
  PLX
  LDY $16FE
  ORA $17FC
  STA $0080
  JSL $8094C9
  TYA
  CLC
  ADC #$0020
  TAY
  LDA $0080
  CLC
  ADC #$0010
  JSL $8094C9
  INC $16FE
  RTL
'''


def to_off(addr):
    return ((addr >> 16) & 0x7F) * 0x8000 + (addr & 0x7FFF)


def direct_loads(data, cfg, lo, hi):
    """{message address: [file offsets of LDY #addr / LDA #bank / STY $30 / STA $32]}."""
    out = {}
    pat = bytes([0xA9, cfg['bank'], 0x00])
    i = data.find(pat)
    while i != -1:
        # either STY $30 / STA $32 right after, or a BRA to a shared STY $30 / STA $32 (the
        # schedule's return from the Practice Match / Move Difficulty / Finisher screens)
        if data[i - 3] == 0xA0 and (data[i + 3:i + 7] == bytes([0x84, 0x30, 0x85, 0x32]) or data[i + 3] == 0x80):
            a = data[i - 2] | data[i - 1] << 8
            if lo <= a < hi:
                out.setdefault(a, []).append(i - 3)
        i = data.find(pat, i + 1)
    return out


def indexed_reads(data, cfg):
    """[(file offset, table index)] of LDA $83:table+2n,X / STA $30 / LDA #$0083 / STA $32: places that
    read part of the message table directly (the drill type lines and "Choose N more")."""
    out = []
    end = (cfg['table'] & 0x7FFF) + 2 * cfg['count']
    i = data.find(bytes([0x85, 0x30, 0xA9, cfg['bank'], 0x00, 0x85, 0x32]))
    while i != -1:
        if data[i - 4] == 0xBF and data[i - 1] == cfg['bank']:
            a = (data[i - 3] | data[i - 2] << 8) & 0x7FFF
            if (cfg['table'] & 0x7FFF) <= a < end and (a - (cfg['table'] & 0x7FFF)) % 2 == 0:
                out.append((i - 4, (a - (cfg['table'] & 0x7FFF)) // 2))
        i = data.find(bytes([0x85, 0x30, 0xA9, cfg['bank'], 0x00, 0x85, 0x32]), i + 1)
    return out


def messages(data, cfg):
    """[(id, file offset, bytes)]: the table's entries ('00'..) and messages only loaded directly
    by address ('dXXXX')."""
    out = []
    starts = []
    for i in range(cfg['count']):
        a = data[cfg['table'] + 2 * i] | data[cfg['table'] + 2 * i + 1] << 8
        starts.append((f'{i:02d}', a))
    known = {a for _, a in starts}
    lo, hi = min(known), 0x8000 | (cfg['table'] & 0x7FFF)
    for a in sorted(direct_loads(data, cfg, lo, hi)):
        if a not in known:
            starts.append((f'd{a:04X}', a))
    for ident, a in starts:
        p = to_off((cfg['bank'] << 16) | a)
        q = p
        while data[q] != 0xFF:
            q += 1
        out.append((ident, p, data[p:q]))
    return out


def decode(b):
    return [''.join(JP[x] if x < len(JP) else '{%02X}' % x for x in line).rstrip('　')
            for line in b.split(b'\xfe')]


def dump(name):
    data = paths.ROM.read_bytes()
    cfg = SETS[name]
    path = paths.TRANSLATION / 'text' / f'{name}.txt'
    old = blocks.BlockFile(path) if path.exists() else None
    lines = [f'# {name}: help texts (tools/helptext.py). Line 1 up to {cfg["widths"][0]} letters, line 2 up to'
             f' {cfg["widths"][1]}; an empty line stays empty.', '']
    msgs = messages(data, cfg)
    for ident, p, b in msgs:
        lines.append(f'@ {ident} at={p:#x}')
        lines += ['JP ' + s for s in decode(b)]
        ob = old.get(ident) if old else None
        if ob:
            lines += ['EN ' + s for s in ob.english]
        lines.append('')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join(lines), encoding='utf-8', newline='\n')
    print(f'{paths.show(path)}: {len(msgs)} messages')


def apply(rom, name):
    """Install the English messages of set `name` into `rom` (bytearray, expanded)."""
    cfg = SETS[name]
    data = bytes(rom)
    msgs = messages(data, cfg)
    bf = blocks.BlockFile(paths.TRANSLATION / 'text' / f'{name}.txt')
    en = {b.id: b.english for b in bf.blocks}
    slots = sorted({x for _, _, b in msgs for x in b if x not in (0, 0xFE)})
    cells = [c for n in slots for c in (2 * n, 2 * n + 1) if c not in (0xFE, 0xFF)]
    chars = sorted({ch for lines in en.values() for s in lines for ch in s} - {' '})
    bad = set(chars) - set(font8.CODES)
    if bad:
        raise SystemExit(f'{name}: characters not in the font: {"".join(sorted(bad))}')
    if len(chars) > len(cells):
        raise SystemExit(f'{name}: {len(chars)} letters, {len(cells)} cells')
    code = {' ': 0}
    code.update({ch: cells[i] for i, ch in enumerate(chars)})
    # the tile set: letters into their cells (2bpp, colour 1)
    r = snes.Rom(rom)
    ptr = cfg['tiles_ptr']
    src = rom[ptr] | rom[ptr + 1] << 8 | rom[ptr + 2] << 16
    tiles, _ = kpack.unpack(data, to_off(src))
    tiles = bytearray(tiles)
    f8 = font8.glyph_bytes()
    for ch, b in code.items():
        if b == 0:
            continue
        t = b + (b & 0xF0)
        g = f8[font8.CODES[ch] * 16:font8.CODES[ch] * 16 + 16]
        for half in range(2):
            o = (t + 16 * half) * 16
            for y in range(8):
                tiles[o + 2 * y] = g[half * 8 + y]
                tiles[o + 2 * y + 1] = 0
    packed = kpack.pack(bytes(tiles))
    to = r.to_file((TILES_BANK << 16) | 0x8000)
    rom[to:to + len(packed)] = packed
    rom[ptr:ptr + 3] = bytes([0x00, 0x80, TILES_BANK])
    # messages and their table
    mo = r.to_file((MSG_BANK << 16) | 0x8000)
    table_at = 0x8000
    pos = 0x8000 + 2 * cfg['count']
    newaddr = {}
    for ident, p, b in msgs:
        lines = en.get(ident)
        if not lines:
            raise SystemExit(f'{name} @{ident}: no English')
        for k, s in enumerate(lines):
            if len(s) > cfg['widths'][min(k, 1)]:
                raise SystemExit(f'{name} @{ident}: line {k + 1} is {len(s)} letters (max {cfg["widths"][min(k, 1)]})')
        # full width: the game redraws only as many cells as the new text has
        # (an empty line stays empty: the line already on screen is kept, as in the original)
        padded = [s.ljust(cfg['widths'][min(k, 1)]) if s else '' for k, s in enumerate(lines)]
        body = b'\xfe'.join(bytes(code[c] for c in s) for s in padded) + b'\xff'
        rom[mo + pos - 0x8000:mo + pos - 0x8000 + len(body)] = body
        if not ident.startswith('d'):
            i = int(ident)
            rom[mo + 2 * i:mo + 2 * i + 2] = bytes([pos & 0xFF, pos >> 8])
        newaddr[0x8000 | (p & 0x7FFF)] = pos
        pos += len(body)
    n_direct = 0
    for a, sites in direct_loads(data, cfg, 0x8000, 0x10000).items():
        if a in newaddr:
            for i in sites:
                rom[i + 1:i + 3] = bytes([newaddr[a] & 0xFF, newaddr[a] >> 8])
                rom[i + 4] = MSG_BANK
                n_direct += 1
    for i, n in indexed_reads(data, cfg):
        if i == to_off(cfg['table_read']):
            continue
        t = table_at + 2 * n
        rom[i + 1:i + 4] = bytes([t & 0xFF, t >> 8, MSG_BANK])
        rom[i + 7] = MSG_BANK
        n_direct += 1
    hook, labels = asm65816.assemble(HOOK, HOOK_ADDR)
    ho = r.to_file(HOOK_ADDR)
    rom[ho:ho + len(hook)] = hook
    for addr, old, new in ((cfg['table_read'], bytes([0xBF, cfg['table'] & 0xFF, 0xF0, 0x83]),
                            bytes([0xBF, table_at & 0xFF, table_at >> 8, MSG_BANK])),
                           (cfg['bank_load'], bytes([0xA9, 0x83, 0x00]), bytes([0xA9, MSG_BANK, 0x00])),
                           (cfg['tile_call'], bytes([0x22, 0x43, 0xBC, 0x80]),
                            bytes([0x22, labels['TileH'] & 0xFF, (labels['TileH'] >> 8) & 0xFF, labels['TileH'] >> 16]))):
        o = r.to_file(addr)
        if bytes(rom[o:o + len(old)]) not in (old, new):
            raise SystemExit(f'{name}: ${addr:06X} expected {old.hex()}, found {bytes(rom[o:o + len(old)]).hex()}')
        rom[o:o + len(new)] = new
    return len(msgs), len(chars), n_direct


def main(argv=None):
    argv = paths.configure(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ['dump']:
        for name in SETS:
            dump(name)
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
