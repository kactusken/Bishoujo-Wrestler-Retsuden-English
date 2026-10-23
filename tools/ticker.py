#!/usr/bin/env python3
"""Match commentary ticker and the winner's quote (build step).

  ticker.py dump        write translation/text/ticker.txt and winner.txt from the ROM

Both are 8-bit glyph strings ($FF end) over a BG3 font of 16x16 glyphs that the match screen and
the winner screen load whole (the ticker font has ~200 glyphs, names at $C8+; the winner font ~190).
- Commentary: 16-bit pointers at $89:EAAD (bank $89, set at $81:F4AD), read at $81:F4D7 and
  $81:F560; $81:F5D5 copies a string to $7E:F1A1 and expands $E0 (the wrestler on the move), $E1
  (her partner) and $E3 (her opponent) into name glyphs ($C8+); $81:F58A draws one glyph every 8
  frames into a scrolling BG3 row (map word $5E60 + column, one 16x16 cell per code).
- Winner's quote: five tables of 16 pointers at $89:CD8B/CDAB/CDCB/CDEB/CE0B (by wrestler and
  result, $84:BF9E.. and $84:C0C7..), typed by $81:F685 from [$40] (bank set by `LDA #$0089` at
  $84:BFB1 / $84:C0D4): $FE line break, $FF end.

English: the strings are font8 codes (a leading or trailing space of the original is added) (tools/font8.py) in TEXT_BANK with new pointer tables. Two
hooks draw a cell of two 8-pixel letters each time the game draws a glyph: the letters are
rendered into a glyph slot of their own (ticker: a ring of 32 slots by map column; quote: a slot
per cell) and the slot's 64 bytes go to VRAM through the game's word queue ($80:94C9). Name
glyphs in the ticker are drawn as before (they hold two letters already).
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import asm65816  # noqa: E402
import blocks  # noqa: E402
import font8  # noqa: E402
import paths  # noqa: E402
import snes  # noqa: E402

TEXT_BANK = 0xFA
CODE_ADDR = 0xD0A000
FONT8 = 0xD08000

TICKER_TABLE = 0x89EAAD
TICKER_FIRST = 0x89D9DE      # the empty string; strings run to $89:EAAC
TICKER_READS = [0x81F4D7, 0x81F560]       # LDA $89EAAD,X
TICKER_BANK = 0x81F4AD                     # LDA #$0089 / STA $42 / LDA #$D9DE
QUOTE_TABLES = [0x89CD8B, 0x89CDAB, 0x89CDCB, 0x89CDEB, 0x89CE0B]
QUOTE_READS = [0x84BF9E, 0x84BFA4, 0x84BFAA, 0x84C0C7, 0x84C0CD]
QUOTE_BANKS = [0x84BFB1, 0x84C0D4]         # LDA #$0089 / STA $0042,Y
TICK_SITE = 0x81F5AA         # PHA / LDX $44 / ... / JSL $8094C9  -> JSL TickCell / BRA $F5BF
TYPE_SITE = 0x81F6BB         # LDA [$40] ... JSL $8094C9 / INC $46  -> JSL TypeCell / BRA $F6D1

CODES = {'{E0}': 0xE0, '{E1}': 0xE1, '{E3}': 0xE3}
TICKER_MAX = 110             # letters (the buffer at $7E:F1A1 holds 128 codes with the names)
QUOTE_WIDTH = 22             # letters a line (11 cells)

# ticker font, glyph = slot (identified against the dialogue font)
TICKER_GLYPHS = (' 、・?!ー1235' + '89DFST' + 'ぁあいうえおかがきぎくけげこさしすずせそぞただちっつてでとどなにねのはばひふぶまみむめもよらりるれろわをん'
                 'ァアィイウェエォオカガキギクグケコゴサザシジスズセソタダチッテデトドナニネノハバパヒビピフブプペホボポマミムャュョラリルレロワン'
                 '快外間顔気逆強恐撃決血見固後攻高合豪込殺事取手首重掌上場心震勢切折素早相足体叩弾底天転電投逃頭動突入脳爆抜飛怖返抱方面雷落烈裂腕卍炸腱')
QUOTE_GLYPHS = (' 、。・?!ーKMOeあいうぇえぉかがきぎくぐけげこごさしじすずせぜそぞただちっつてでとどなにねのはばほまみめもゃやょよらりるれろわをん'
                'ァアイウェォオカガキクグケコセタダチットナニヌネノハパフプヘホマミメヤヨラリルレロワン'
                '悪威意違一何加果過回界楽頑気技強興苦恵結見減言呼合込今座残子思私試事次実者弱手習出勝小信世性戦然相足続大知張調直追努度倒当闘日入敗必負物聞変方本味娘来力練')

HOOK = '''
.m16
.x16
TickCell:               ; at $81:F5AA: A = map word address of the next ticker cell
  PHA
  LDX $44
  LDA $7EF1A1,X
  AND #$00FF
  CMP #$00C8
  BCC tc_text
  ASL A                 ; a name glyph: drawn as before
  TAX
  LDA $898000,X
  PLY
  JSL $8094C9
  RTL
tc_text:
  PHA                   ; left letter
  LDA $7EF1A2,X
  AND #$00FF
  CMP #$00C8
  BCC tc_two
  LDA #$0000            ; a name or the end follows: a space on the right
  BRA tc_have
tc_two:
  INC $44               ; two letters used (the caller adds the other one)
tc_have:
  TAY
  PLX
  LDA 1,S
  AND #$001F
  CLC
  ADC #$0040            ; slots $40-$5F, one per map column
  JSL DrawPair
  PLY
  JSL $8094C9
  RTL

TypeCell:               ; at $81:F6BB: the next cell of the quote at [$40], map address $46
  LDA [$40]
  AND #$00FF
  PHA                   ; left letter
  LDY #$0001
  LDA [$40],Y
  AND #$00FF
  CMP #$00FE
  BCC ty_two
  LDA #$0000            ; a line break or the end follows: a space on the right
  BRA ty_have
ty_two:
  INC $40
ty_have:
  PHA                   ; right letter
  LDA $46               ; slot $40 + (row & 3) * 16 + (column & 15)
  AND #$0060
  LSR A
  STA $38
  LDA $46
  AND #$000F
  CLC
  ADC $38
  ADC #$0040
  PLY
  PLX
  PHX
  PHY
  JSL DrawPair
  ORA #$2000
  LDY $46
  JSL $8094C9
  INC $46
  PLA
  ORA 1,S               ; X <> 0 unless both are spaces (the caller's typing sound)
  TAX
  PLA
  RTL

DrawPair:               ; A = glyph slot, X = left letter, Y = right letter -> A = tile number
  PHY
  PHX
  PHA
  AND #$0007
  ASL A
  STA $38
  LDA 1,S
  AND #$00F8
  ASL A
  ASL A
  CLC
  ADC $38
  STA $38               ; tile number: (slot & 7) * 2 + (slot >> 3) * 32
  ASL A
  ASL A
  ASL A
  CLC
  ADC #$4000
  STA $3A               ; its VRAM word address (BG3 characters at $4000)
  LDA 3,S
  JSR Letter
  LDA $3A
  CLC
  ADC #$0008
  STA $3A
  LDA 5,S
  JSR Letter
  PLA
  PLA
  PLA
  LDA $38
  RTL

Letter:                 ; A = font8 code: 16 rows to the tile at $3A and the one below it
  AND #$00FF
  ASL A
  ASL A
  ASL A
  ASL A
  TAX
  CLC
  ADC #$0010
  PHA
  LDY $3A
le_row:
  LDA FONT8,X
  AND #$00FF
  JSL $8094C9
  INY
  INX
  TXA
  AND #$000F
  CMP #$0008
  BNE le_next
  TYA
  CLC
  ADC #$0078            ; rows 8-15 go to the tile 16 further on
  TAY
le_next:
  TXA
  CMP 1,S
  BNE le_row
  PLA
  RTS
'''.replace('FONT8', '$%06X' % FONT8)


def to_off(addr):
    return ((addr >> 16) & 0x7F) * 0x8000 + (addr & 0x7FFF)


def decode(b, glyphs):
    out = ''
    for x in b:
        if x == 0xFE:
            out += '/'
        elif x in CODES.values():
            out += '{%02X}' % x
        else:
            out += glyphs[x] if x < len(glyphs) else '{%02X}' % x
    return out


def string(data, addr):
    o = to_off(addr)
    return data[o:data.find(b'\xff', o)]


def ticker_entries(data):
    """Pointers of the commentary table (it ends where the pointers leave the string area)."""
    o = to_off(TICKER_TABLE)
    out = []
    while True:
        p = data[o] | data[o + 1] << 8
        if not (TICKER_FIRST & 0xFFFF) <= p < (TICKER_TABLE & 0xFFFF):
            return out
        out.append(0x890000 | p)
        o += 2


def quote_entries(data):
    return [0x890000 | data[to_off(t) + 2 * i] | data[to_off(t) + 2 * i + 1] << 8
            for t in QUOTE_TABLES for i in range(16)]


def dump():
    data = paths.ROM.read_bytes()
    tk = ticker_entries(data)
    lines = ['# Match commentary (tools/ticker.py): one line of English per string, at most '
             f'{TICKER_MAX} letters.',
             '# {E0} = the wrestler making the move, {E3} = her opponent, {E1} = her tag partner',
             '# (each prints a short name, up to 8 letters). "idx" = the table entries using the string.', '']
    seen = {}
    for i, a in enumerate(tk):
        seen.setdefault(a, []).append(i)
    for a in sorted(seen):
        lines += [f'@ {a:06X} idx={",".join(map(str, seen[a]))}', 'JP ' + decode(string(data, a), TICKER_GLYPHS), '']
    (paths.TRANSLATION / 'text' / 'ticker.txt').write_text('\n'.join(lines), encoding='utf-8', newline='\n')
    qs = quote_entries(data)
    lines = [f'# Winner\'s quotes (tools/ticker.py): one EN line per line on screen, at most {QUOTE_WIDTH} '
             'letters a line,', '# at most 4 lines. "idx" = table * 16 + wrestler type.', '']
    seen = {}
    for i, a in enumerate(qs):
        seen.setdefault(a, []).append(i)
    for a in sorted(seen):
        jp = decode(string(data, a), QUOTE_GLYPHS).split('/')
        lines += [f'@ {a:06X} idx={",".join(map(str, seen[a]))}'] + ['JP ' + j for j in jp] + ['']
    (paths.TRANSLATION / 'text' / 'winner.txt').write_text('\n'.join(lines), encoding='utf-8', newline='\n')
    print(f'{len(tk)} commentary entries, {len(qs)} quote entries')


def encode(text, what):
    out = bytearray()
    i = 0
    while i < len(text):
        m = re.match(r'\{E[013]\}', text[i:])
        if m:
            out.append(CODES[m.group(0)])
            i += len(m.group(0))
            continue
        ch = text[i]
        if ch not in font8.CODES:
            raise SystemExit(f'ticker: {what}: {ch!r} is not in the font')
        out.append(font8.CODES[ch])
        i += 1
    return bytes(out)


def texts(name, data, entries, multi):
    """{address: encoded string} for every string the entries use."""
    bf = blocks.BlockFile(paths.TRANSLATION / 'text' / f'{name}.txt')
    en = {int(b.id, 16): b.english for b in bf.blocks}
    out = {}
    for a in sorted(set(entries)):
        lines = en.get(a)
        if not lines:
            if string(data, a).strip(b'\x00'):
                raise SystemExit(f'ticker: {name} @{a:06X} has no English')
            lines = ['']
        if multi:
            if len(lines) > 4 or any(len(l) > QUOTE_WIDTH for l in lines):
                raise SystemExit(f'ticker: {name} @{a:06X}: more than 4 lines or {QUOTE_WIDTH} letters')
            out[a] = b'\xfe'.join(encode(l, f'{name} @{a:06X}') for l in lines) + b'\xff'
        else:
            jp = string(data, a)          # the original's spaces separate it from the next string
            text = ' '.join(lines).strip()
            text = ' ' * (jp[:1] == b'\x00') + text + ' ' * (jp[-1:] == b'\x00')
            b = encode(text, f'{name} @{a:06X}')
            if len(b) > TICKER_MAX:
                raise SystemExit(f'ticker: {name} @{a:06X}: {len(b)} letters, at most {TICKER_MAX}')
            out[a] = b + b'\xff'
    return out


def apply(rom):
    data = bytes(rom)
    r = snes.Rom(rom)
    hook, labels = asm65816.assemble(HOOK, CODE_ADDR)
    o = r.to_file(CODE_ADDR)
    rom[o:o + len(hook)] = hook
    base = r.to_file(TEXT_BANK << 16 | 0x8000)
    pos = 0x8000

    def put(b):
        nonlocal pos
        rom[base + pos - 0x8000:base + pos - 0x8000 + len(b)] = b
        pos += len(b)
        return pos - len(b)
    n = 0
    for name, entries, multi in (('ticker', ticker_entries(data), False), ('winner', quote_entries(data), True)):
        new = {a: put(b) for a, b in texts(name, data, entries, multi).items()}
        n += len(new)
        tab = pos
        for a in entries:
            put(new[a].to_bytes(2, 'little'))
        if name == 'ticker':
            for site in TICKER_READS:
                so = to_off(site)
                if data[so:so + 4] != b'\xbf\xad\xea\x89':
                    raise SystemExit(f'ticker: unexpected code at ${site:06X}')
                rom[so + 1:so + 4] = (TEXT_BANK << 16 | tab).to_bytes(3, 'little')
            so = to_off(TICKER_BANK)
            if data[so:so + 8] != b'\xa9\x89\x00\x85\x42\xa9\xde\xd9':
                raise SystemExit('ticker: unexpected code at the bank setup')
            rom[so + 1] = TEXT_BANK
            rom[so + 6:so + 8] = new[TICKER_FIRST].to_bytes(2, 'little')
        else:
            for k, site in enumerate(QUOTE_READS):
                so = to_off(site)
                t = data[so + 1] | data[so + 2] << 8 | data[so + 3] << 16
                if data[so] != 0xBF or t not in QUOTE_TABLES:
                    raise SystemExit(f'ticker: unexpected code at ${site:06X}')
                rom[so + 1:so + 4] = (TEXT_BANK << 16 | tab + 32 * QUOTE_TABLES.index(t)).to_bytes(3, 'little')
            for site in QUOTE_BANKS:
                so = to_off(site)
                if data[so:so + 3] != b'\xa9\x89\x00':
                    raise SystemExit(f'ticker: unexpected code at ${site:06X}')
                rom[so + 1] = TEXT_BANK
    for site, label, back in ((TICK_SITE, 'TickCell', 0x81F5BF), (TYPE_SITE, 'TypeCell', 0x81F6D1)):
        so = to_off(site)
        rom[so:so + 4] = b'\x22' + labels[label].to_bytes(3, 'little')
        rom[so + 4:so + 6] = bytes([0x80, back - (site + 6)])
    return n


def main(argv=None):
    argv = paths.configure(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ['dump']:
        dump()
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
