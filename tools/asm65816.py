#!/usr/bin/env python3
"""A small 65816 assembler for the code hooks (standard library only).

  asm65816.py FILE.asm ORG        print the bytes (hex) assembled at CPU address ORG

assemble(source, org) -> (bytes, {label: address}). Syntax, one instruction per line:
  label:              a label (local to the source)        ; comment
  LDA #$12 / #$1234   immediate: size follows the M/X flags, which REP/SEP in the source track
                      in order (start: .m16/.x16 or .m8/.x8 directives, default 16-bit)
  LDA $12 / $1234 / $7E1234     direct page / absolute / long (by the number of hex digits; force
                      with .b .w .l suffixes on the mnemonic: LDA.l $001234)
  LDA $12,X  $1234,X  $7E1234,X  $1234,Y  ($12) ($12),Y ($12,X) [$12] [$12],Y  $12,S  ($12,S),Y
  BRA label / BEQ label / BRL label / JSR label / JMP label / JSL $8C1234 / JML label
  db $01,$02 / dw $1234,label / dl label    data
Numbers: $hex, decimal, or label (absolute 16-bit / long 24-bit by context); label+N allowed.
"""
import re
import sys

G1 = {'ORA': 0x00, 'AND': 0x20, 'EOR': 0x40, 'ADC': 0x60, 'STA': 0x80, 'LDA': 0xA0, 'CMP': 0xC0, 'SBC': 0xE0}
G1_MODES = {'(dp,x)': 0x01, 'sr,s': 0x03, 'dp': 0x05, '[dp]': 0x07, 'imm': 0x09, 'abs': 0x0D, 'long': 0x0F,
            '(dp),y': 0x11, '(dp)': 0x12, '(sr,s),y': 0x13, 'dp,x': 0x15, '[dp],y': 0x17, 'abs,y': 0x19,
            'abs,x': 0x1D, 'long,x': 0x1F}
OPS = {
    ('LDX', 'imm'): 0xA2, ('LDX', 'dp'): 0xA6, ('LDX', 'abs'): 0xAE, ('LDX', 'dp,y'): 0xB6, ('LDX', 'abs,y'): 0xBE,
    ('LDY', 'imm'): 0xA0, ('LDY', 'dp'): 0xA4, ('LDY', 'abs'): 0xAC, ('LDY', 'dp,x'): 0xB4, ('LDY', 'abs,x'): 0xBC,
    ('STX', 'dp'): 0x86, ('STX', 'abs'): 0x8E, ('STX', 'dp,y'): 0x96,
    ('STY', 'dp'): 0x84, ('STY', 'abs'): 0x8C, ('STY', 'dp,x'): 0x94,
    ('STZ', 'dp'): 0x64, ('STZ', 'abs'): 0x9C, ('STZ', 'dp,x'): 0x74, ('STZ', 'abs,x'): 0x9E,
    ('CPX', 'imm'): 0xE0, ('CPX', 'dp'): 0xE4, ('CPX', 'abs'): 0xEC,
    ('CPY', 'imm'): 0xC0, ('CPY', 'dp'): 0xC4, ('CPY', 'abs'): 0xCC,
    ('BIT', 'imm'): 0x89, ('BIT', 'dp'): 0x24, ('BIT', 'abs'): 0x2C, ('BIT', 'dp,x'): 0x34, ('BIT', 'abs,x'): 0x3C,
    ('INC', 'acc'): 0x1A, ('INC', 'dp'): 0xE6, ('INC', 'abs'): 0xEE, ('INC', 'dp,x'): 0xF6, ('INC', 'abs,x'): 0xFE,
    ('DEC', 'acc'): 0x3A, ('DEC', 'dp'): 0xC6, ('DEC', 'abs'): 0xCE, ('DEC', 'dp,x'): 0xD6, ('DEC', 'abs,x'): 0xDE,
    ('ASL', 'acc'): 0x0A, ('ASL', 'dp'): 0x06, ('ASL', 'abs'): 0x0E,
    ('LSR', 'acc'): 0x4A, ('LSR', 'dp'): 0x46, ('LSR', 'abs'): 0x4E,
    ('ROL', 'acc'): 0x2A, ('ROL', 'dp'): 0x26, ('ROL', 'abs'): 0x2E,
    ('ROR', 'acc'): 0x6A, ('ROR', 'dp'): 0x66, ('ROR', 'abs'): 0x6E,
    ('TSB', 'dp'): 0x04, ('TSB', 'abs'): 0x0C, ('TRB', 'dp'): 0x14, ('TRB', 'abs'): 0x1C,
    ('JMP', 'abs'): 0x4C, ('JMP', 'long'): 0x5C, ('JMP', '(abs)'): 0x6C, ('JMP', '(abs,x)'): 0x7C,
    ('JML', 'long'): 0x5C, ('JSR', 'abs'): 0x20, ('JSR', '(abs,x)'): 0xFC, ('JSL', 'long'): 0x22,
    ('PEA', 'abs'): 0xF4, ('REP', 'imm8'): 0xC2, ('SEP', 'imm8'): 0xE2,
    ('MVN', 'move'): 0x54, ('MVP', 'move'): 0x44,
}
IMPLIED = {'CLC': 0x18, 'SEC': 0x38, 'CLI': 0x58, 'SEI': 0x78, 'CLV': 0xB8, 'CLD': 0xD8, 'SED': 0xF8,
           'INX': 0xE8, 'INY': 0xC8, 'DEX': 0xCA, 'DEY': 0x88, 'TAX': 0xAA, 'TAY': 0xA8, 'TXA': 0x8A,
           'TYA': 0x98, 'TXY': 0x9B, 'TYX': 0xBB, 'TCD': 0x5B, 'TDC': 0x7B, 'TCS': 0x1B, 'TSC': 0x3B,
           'TSX': 0xBA, 'TXS': 0x9A, 'XBA': 0xEB, 'PHA': 0x48, 'PLA': 0x68, 'PHX': 0xDA, 'PLX': 0xFA,
           'PHY': 0x5A, 'PLY': 0x7A, 'PHB': 0x8B, 'PLB': 0xAB, 'PHP': 0x08, 'PLP': 0x28, 'PHK': 0x4B,
           'PHD': 0x0B, 'PLD': 0x2B, 'RTS': 0x60, 'RTL': 0x6B, 'RTI': 0x40, 'NOP': 0xEA, 'XCE': 0xFB,
           'WAI': 0xCB, 'STP': 0xDB}
BRANCH = {'BRA': 0x80, 'BEQ': 0xF0, 'BNE': 0xD0, 'BCC': 0x90, 'BCS': 0xB0, 'BPL': 0x10, 'BMI': 0x30,
          'BVC': 0x50, 'BVS': 0x70}
SIZES = {'imm8': 1, 'dp': 1, 'dp,x': 1, 'dp,y': 1, '(dp)': 1, '(dp),y': 1, '(dp,x)': 1, '[dp]': 1, '[dp],y': 1,
         'sr,s': 1, '(sr,s),y': 1, 'abs': 2, 'abs,x': 2, 'abs,y': 2, '(abs)': 2, '(abs,x)': 2,
         'long': 3, 'long,x': 3, 'acc': 0, 'move': 2}


class AsmError(Exception):
    pass


def parse_num(s, labels, pass2):
    s = s.strip()
    m = re.fullmatch(r'([A-Za-z_.][\w.]*)\s*([+-]\s*(?:\$[0-9A-Fa-f]+|\d+))?', s)
    if m and not re.fullmatch(r'\$[0-9A-Fa-f]+', s):
        if m.group(1) not in labels:
            if pass2:
                raise AsmError(f'unknown label {m.group(1)}')
            return 0, 99
        v = labels[m.group(1)]
        if m.group(2):
            v += parse_num(m.group(2).replace(' ', '').lstrip('+'), labels, pass2)[0] * (-1 if m.group(2).strip()[0] == '-' else 1)
        return v, 99
    if s.startswith('$'):
        return int(s[1:], 16), len(s) - 1
    if s.startswith('-'):
        return -int(s[1:], 0), 0
    return int(s, 0), 0


def assemble(source, org, m16=True, x16=True):
    labels = {}
    for pass2 in (False, True):
        out = bytearray()
        pc = org
        m, x = m16, x16
        for n, raw in enumerate(source.splitlines(), 1):
            line = raw.split(';')[0].strip()
            try:
                while True:
                    lm = re.match(r'([A-Za-z_][\w.]*):\s*', line)
                    if not lm:
                        break
                    if not pass2:
                        labels[lm.group(1)] = pc
                    line = line[lm.end():]
                if not line:
                    continue
                if line in ('.m16', '.m8', '.x16', '.x8'):
                    if line[1] == 'm':
                        m = line == '.m16'
                    else:
                        x = line == '.x16'
                    continue
                mn, _, arg = line.partition(' ')
                arg = arg.strip()
                mn = mn.upper()
                force = None
                if '.' in mn:
                    mn, force = mn.split('.')
                    force = force.lower()
                code = assemble_one(mn, arg, force, pc, m, x, labels, pass2)
                if mn == 'REP':
                    v = parse_num(arg.lstrip('#'), labels, pass2)[0]
                    m, x = (True if v & 0x20 else m), (True if v & 0x10 else x)
                elif mn == 'SEP':
                    v = parse_num(arg.lstrip('#'), labels, pass2)[0]
                    m, x = (False if v & 0x20 else m), (False if v & 0x10 else x)
                out += code
                pc += len(code)
            except (AsmError, ValueError) as e:
                raise AsmError(f'line {n}: {raw.strip()}: {e}')
    return bytes(out), labels


def assemble_one(mn, arg, force, pc, m, x, labels, pass2):
    if mn in ('DB', 'DW', 'DL'):
        w = {'DB': 1, 'DW': 2, 'DL': 3}[mn]
        b = bytearray()
        for a in arg.split(','):
            v = parse_num(a, labels, pass2)[0]
            b += (v & ((1 << (8 * w)) - 1)).to_bytes(w, 'little')
        return bytes(b)
    if mn in IMPLIED and not arg:
        return bytes([IMPLIED[mn]])
    if mn in BRANCH or mn == 'BRL':
        t = parse_num(arg, labels, pass2)[0]
        if mn == 'BRL':
            d = t - (pc + 3)
            if pass2 and not -32768 <= d <= 32767:
                raise AsmError('BRL out of range')
            return bytes([0x82]) + (d & 0xFFFF).to_bytes(2, 'little')
        d = t - (pc + 2)
        if pass2 and not -128 <= d <= 127:
            raise AsmError(f'branch out of range ({d})')
        return bytes([BRANCH[mn], d & 0xFF])
    if mn in ('MVN', 'MVP'):
        a, b = arg.split(',')
        return bytes([OPS[(mn, 'move')], parse_num(a, labels, pass2)[0] & 0xFF, parse_num(b, labels, pass2)[0] & 0xFF])
    mode, val = mode_of(mn, arg, force, labels, pass2)
    if mode == 'imm':
        if mn in ('REP', 'SEP'):
            return bytes([OPS[(mn, 'imm8')], val & 0xFF])
        size = 2 if ((mn in ('LDX', 'LDY', 'CPX', 'CPY') and x) or (mn not in ('LDX', 'LDY', 'CPX', 'CPY') and m)) else 1
        op = G1[mn] + G1_MODES['imm'] if mn in G1 else OPS[(mn, 'imm')]
        return bytes([op]) + (val & ((1 << (8 * size)) - 1)).to_bytes(size, 'little')
    if mn in G1:
        if mode not in G1_MODES or (mn == 'STA' and mode == 'imm'):
            raise AsmError(f'{mn} has no mode {mode}')
        op = G1[mn] + G1_MODES[mode]
    else:
        if mn == 'JMP' and mode == 'long':
            pass
        if (mn, mode) not in OPS:
            # JSR/JMP to a label: absolute
            if mode == 'long' and (mn, 'abs') in OPS and mn in ('JSR', 'JMP') and force != 'l':
                mode = 'abs'
            elif mode == 'abs' and (mn, 'long') in OPS and mn in ('JSL', 'JML'):
                mode = 'long'
            if (mn, mode) not in OPS:
                raise AsmError(f'{mn} has no mode {mode}')
        op = OPS[(mn, mode)]
    size = SIZES[mode]
    return bytes([op]) + (val & ((1 << (8 * size)) - 1)).to_bytes(size, 'little') if size else bytes([op])


def mode_of(mn, arg, force, labels, pass2):
    a = arg.replace(' ', '')
    if a == '' or a.upper() == 'A':
        return 'acc', 0
    if a.startswith('#'):
        return 'imm', parse_num(a[1:], labels, pass2)[0]
    low = a.lower()
    pats = [(r'\((.+),s\),y', '(sr,s),y'), (r'\[(.+)\],y', '[dp],y'), (r'\[(.+)\]', '[dp]'), (r'\((.+),x\)', '(?,x)'),
            (r'\((.+)\),y', '(dp),y'), (r'\((.+)\)', '(?)'), (r'(.+),s', 'sr,s'), (r'(.+),x', '?,x'), (r'(.+),y', '?,y'),
            (r'(.+)', '?')]
    for pat, mode in pats:
        mm = re.fullmatch(pat, low)
        if mm:
            inner = a[mm.start(1):mm.end(1)]
            v, digits = parse_num(inner, labels, pass2)
            if '?' not in mode:
                return mode, v
            if force == 'b':
                w = 'dp'
            elif force == 'w':
                w = 'abs'
            elif force == 'l':
                w = 'long'
            elif digits == 99:   # a label: long for JSL/JML, else absolute
                w = 'long' if mn in ('JSL', 'JML') else 'abs'
            elif digits <= 2:
                w = 'dp'
            elif digits <= 4:
                w = 'abs'
            else:
                w = 'long'
            if mode == '(?,x)':
                return ('(abs,x)' if mn in ('JMP', 'JSR') else '(dp,x)'), v
            if mode == '(?)':
                return ('(abs)' if mn == 'JMP' else '(dp)'), v
            return mode.replace('?', w), v
    raise AsmError(f'bad operand {arg}')


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        sys.exit(__doc__)
    code, labels = assemble(open(argv[0]).read(), int(argv[1], 0))
    print(code.hex(' '))
    for k, v in labels.items():
        print(f'{k} = ${v:06X}')


if __name__ == '__main__':
    main()
