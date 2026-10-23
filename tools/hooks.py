#!/usr/bin/env python3
"""The English dialogue renderer: ROM expansion, the 8x16 font and two code hooks (build step).

  hooks.py show          print the assembled hook code and the patch list

The game draws a dialogue page (docs/TECHNICAL.md "Text") by collecting the page's glyph codes at
$7E:F1A1, drawing up to 64 16x16 glyphs into $7F:C000 ($8C:ADA2 JSL $8C:A924) - 8 glyphs per
0x200-byte row of tiles, top halves in the first 0x100 bytes - and then, code by code, writing a
2x2-tile map entry at the cursor $16FE ($8C:AF17 JSL $80:BC43; tile = $89:8000 table, cursor += 2).

English uses one 8x16 cell per letter instead: cell k is tile 0x200 + k + (k & 0x70) (top) and
+0x10 (bottom), so the same 4 KB buffer holds 128 cells; the cursor advances by 1 per letter.
  Collect8 ($8C:AD87): the page's codes go to $7E:F1A1 as bytes, at most 120 - as 16-bit words
          (the original) an English page overruns the list into the event script pointer at
          $7E:F221 and the scene jumps to a wrong place (seen: the intro ended after 2 profiles).
  Render8 ($8C:ADA2): draw 120 cells from the codes at $7E:F1A1 (font8 codes) into $7F:C000.
  Tile8   ($8C:AF17): map cell A-$80 at the cursor, cursor += 1.
The window clears and the line starts move from column 6 to column 2 (width 26 -> 30 columns), so
a line holds 30 letters. Name codes ({s1}, {n1}, {player}) still use the game's 16x16 path.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import asm65816  # noqa: E402
import font8  # noqa: E402
import snes  # noqa: E402

ROM_SIZE = 0x400000          # 32 Mbit: banks $D0-$FF become free space for the English
FONT_ADDR = 0xD08000         # 128 codes x 16 bytes
CODE_ADDR = 0xD09000
SCRIPT_FIRST_BANK = 0xD1     # tools/script.py packs the English script from here
CELLS = 120

SOURCE = f'''
.m16
.x16
Render8:                ; replaces JSL $8CA924 at $8C:ADA2 (M/X 16-bit)
  PHB
  PHP
  REP #$30
  PHX
  PHY
  SEP #$20
  LDA #$7F
  PHA
  PLB
  REP #$20
  LDX #$0000
r_cell:
  PHX
  TXA                   ; X = 2k: buffer offset = (k & $70) << 5 | (k & $0F) << 4
  AND #$001E
  ASL A
  ASL A
  ASL A
  STA $3A
  TXA
  AND #$00E0
  ASL A
  ASL A
  ASL A
  ASL A
  ORA $3A
  TAY
  TXA
  LSR A
  TAX
  LDA $7EF1A1,X         ; byte codes (Collect8)
  AND #$007F
  ASL A
  ASL A
  ASL A
  ASL A
  TAX                   ; font offset
  LDA.l {FONT_ADDR:#08x},X
  AND #$00FF
  STA $C000,Y
  INX
  INY
  INY
  LDA.l {FONT_ADDR:#08x},X
  AND #$00FF
  STA $C000,Y
  INX
  INY
  INY
  LDA.l {FONT_ADDR:#08x},X
  AND #$00FF
  STA $C000,Y
  INX
  INY
  INY
  LDA.l {FONT_ADDR:#08x},X
  AND #$00FF
  STA $C000,Y
  INX
  INY
  INY
  LDA.l {FONT_ADDR:#08x},X
  AND #$00FF
  STA $C000,Y
  INX
  INY
  INY
  LDA.l {FONT_ADDR:#08x},X
  AND #$00FF
  STA $C000,Y
  INX
  INY
  INY
  LDA.l {FONT_ADDR:#08x},X
  AND #$00FF
  STA $C000,Y
  INX
  INY
  INY
  LDA.l {FONT_ADDR:#08x},X
  AND #$00FF
  STA $C000,Y
  INX
  INY
  INY
  TYA
  CLC
  ADC #$00F0
  TAY
  LDA.l {FONT_ADDR:#08x},X
  AND #$00FF
  STA $C000,Y
  INX
  INY
  INY
  LDA.l {FONT_ADDR:#08x},X
  AND #$00FF
  STA $C000,Y
  INX
  INY
  INY
  LDA.l {FONT_ADDR:#08x},X
  AND #$00FF
  STA $C000,Y
  INX
  INY
  INY
  LDA.l {FONT_ADDR:#08x},X
  AND #$00FF
  STA $C000,Y
  INX
  INY
  INY
  LDA.l {FONT_ADDR:#08x},X
  AND #$00FF
  STA $C000,Y
  INX
  INY
  INY
  LDA.l {FONT_ADDR:#08x},X
  AND #$00FF
  STA $C000,Y
  INX
  INY
  INY
  LDA.l {FONT_ADDR:#08x},X
  AND #$00FF
  STA $C000,Y
  INX
  INY
  INY
  LDA.l {FONT_ADDR:#08x},X
  AND #$00FF
  STA $C000,Y
  INX
  INY
  INY
  PLX
  INX
  INX
  CPX #{2 * CELLS:#06x}
  BEQ r_done
  JMP r_cell
r_done:
  PLY
  PLX
  PLP
  PLB
  RTL

Collect8:               ; replaces JSR $B42C / REP #$20 at $8C:AD87 (dialogue only): the page's
  LDY #$0000            ; codes -> $7E:F1A1 as bytes, at most 120 (the game's B42C stores words,
  LDX #$0000            ; and is shared with screens that keep the 16x16 renderer)
c_loop:
  LDA [$44],Y
  CMP #$03FF
  BEQ c_end
  CMP #$03E0
  BPL c_skip
  CPX #$0078
  BCS c_skip
  SEP #$20
  STA $7EF1A1,X
  REP #$20
  INX
c_skip:
  INY
  INY
  LDA [$44],Y
  CMP #$03E0
  BEQ c_end
  BRA c_loop
c_end:
  REP #$20
  RTL

Tile8:                  ; replaces JSL $80BC43 at $8C:AF17: A = $80 + cell
  SEC
  SBC #$0080
  PHA
  AND #$0070
  CLC
  ADC 1,S
  ADC #$0200
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
'''.replace('{FONT_ADDR:#08x}', f'${FONT_ADDR:06X}').replace('{2 * CELLS:#06x}', f'${2 * CELLS:04X}')


def assemble():
    code, labels = asm65816.assemble(SOURCE, CODE_ADDR)
    return code, labels


def jsl(addr):
    return bytes([0x22, addr & 0xFF, (addr >> 8) & 0xFF, addr >> 16])


def patches(labels):
    """(CPU address, original bytes, new bytes, what)."""
    p = [
        (0x8CADA2, jsl(0x8CA924), jsl(labels['Render8']), 'draw the page as 8x16 letter cells'),
        (0x8CAF17, jsl(0x80BC43), jsl(labels['Tile8']), 'map one letter cell, cursor + 1'),
        (0x8CAD87, bytes.fromhex('202cb4c220'), jsl(labels['Collect8']) + b'\xea',
         'page codes as bytes: the word list overran the event pointer at $7E:F221'),
        (0x8CB857, bytes.fromhex('202cb4a94000'), jsl(labels['Collect8']) + b'\xea\xea',
         'profiles: page codes as bytes'),
        (0x8CB86A, jsl(0x8CA924), jsl(labels['Render8']), 'profiles: 8x16 letter cells'),
        (0x8CB942, jsl(0x80BC43), jsl(labels['Tile8']), 'profiles: map one letter cell'),
        (0x8CAFBE, bytes.fromhex('4602860 2c602 0603'.replace(' ', '')), bytes.fromhex('42028202c2020203'),
         'line starts: column 6 -> 2'),
        (0x8CAFCE, bytes.fromhex('a94602'), bytes.fromhex('a94202'), 'first line: column 6 -> 2'),
    ]
    for width_at, start_at in ((0x8CAD0D, 0x8CAD1A), (0x8CAD62, 0x8CAD6F), (0x8CAFD9, 0x8CAFE6), (0x8CBD49, 0x8CBD56)):
        p.append((width_at, bytes.fromhex('a91a00'), bytes.fromhex('a91e00'), 'window clear: 26 -> 30 columns'))
        p.append((start_at, bytes.fromhex('a94602'), bytes.fromhex('a94202'), 'window clear: from column 2'))
    return p


def apply(rom):
    """Expand the ROM (bytearray, headerless) and install the font, the code and the patches."""
    r = snes.Rom(rom)
    if len(r.data) < ROM_SIZE:
        r.expand(ROM_SIZE)
    data = r.data
    font = font8.glyph_bytes()
    font = font + bytes(128 * 16 - len(font))
    fo = r.to_file(FONT_ADDR)
    data[fo:fo + len(font)] = font
    code, labels = assemble()
    co = r.to_file(CODE_ADDR)
    data[co:co + len(code)] = code
    for addr, old, new, what in patches(labels):
        o = r.to_file(addr)
        if bytes(data[o:o + len(old)]) not in (old, new):
            raise SystemExit(f'hooks: ${addr:06X} ({what}): expected {old.hex()}, found {bytes(data[o:o + len(old)]).hex()}')
        data[o:o + len(new)] = new
    return data


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] != ['show']:
        sys.exit(__doc__)
    code, labels = assemble()
    print(f'code at ${CODE_ADDR:06X}: {len(code)} bytes')
    print(code.hex(' '))
    for k, v in labels.items():
        print(f'  {k} ${v:06X}')
    for addr, old, new, what in patches(labels):
        print(f'${addr:06X} {old.hex()} -> {new.hex()}  {what}')


if __name__ == '__main__':
    main()
