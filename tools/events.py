#!/usr/bin/env python3
"""Event scripts: disassembler, and a test image that wins every World Circuit stop (research).

  events.py dis START END          list the opcodes from START to END (CPU addresses, hex)
  events.py listing ENTRY... OUT   every opcode reachable from the entries (gotos, ifs, calls and
                                   jumps followed), in address order with labels, and the English
                                   of each `say` from translation/script
  events.py wctest [IMAGE] OUT     copy IMAGE (default: the English build) with every World Circuit
                                   stop won without Training or matches - for viewing the stop
                                   scenes and the ending; never for a release
  events.py crtest [IMAGE] OUT     copy IMAGE with Champion Road's rating gates open, series and their
                                   matches skipped, results read from WRAM (CR_RESULTS, one byte each,
                                   in order, 0 = won); with CR_AUTO set, choices too (CR_CHOICES) -
                                   to reach any ending in minutes; never for a release

The interpreter is $8D:C452 (pointer $7E:F221, bank $7E:F223; opcode table $8D:C60F, even
opcodes $00-$74). Variables vNN are bytes at $7E:F225 + NN. A screen opcode ("run") starts a
task and resumes the script when it ends. Lengths and meanings are read from the handlers;
opNN names are opcodes not identified yet (their length is known).

World Circuit ($93:B6AF): the president's briefing ($88:F37D), team choice ($8B:9CE5), then 13
stops, each: op5E n (the stop's card), $93:B886 (the belt and the rival's taunt, by v17), Training
($8B:B174; the list's top button ends it), the matches ($8E:94D0), the tally ($8C:8ADD -> v11: 0 when
the main singles and one more match are won), the remark of v17 ($93:BACE). v11 = 0 goes on
($93:BD04 sets v17 = v09 first), anything else returns to Training for the same stop. After stop 13:
the president ($88:F3A6), the team's records ($8D:EB01) and the staff roll ($84:FB15, "ENDING NO."
shows v3F, which only Champion Road sets).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

LEN = {0x00: 3, 0x02: 6, 0x04: 4, 0x06: 1, 0x08: 3, 0x0A: 3, 0x0C: 3, 0x0E: 3, 0x10: 3, 0x12: 3,
       0x14: 3, 0x16: 3, 0x18: 3, 0x1A: 3, 0x1C: 1, 0x1E: 3, 0x20: 1, 0x22: 1, 0x24: 2, 0x26: 1,
       0x28: 1, 0x2A: 1, 0x2C: 3, 0x2E: 3, 0x30: 3, 0x32: 2, 0x34: 2, 0x36: 1, 0x38: 3, 0x3A: 3,
       0x3C: 5, 0x3E: 2, 0x40: 1, 0x42: 2, 0x44: 2, 0x46: 4, 0x48: 2, 0x4A: 4, 0x4C: 4, 0x4E: 1,
       0x50: 2, 0x52: 2, 0x54: 2, 0x56: 3, 0x58: 2, 0x5A: 2, 0x5C: 2, 0x5E: 2, 0x60: 1, 0x62: 1,
       0x64: 1, 0x66: 2, 0x68: 1, 0x6A: 2, 0x6C: 1, 0x6E: 2, 0x70: 1, 0x72: 1, 0x74: 1}
NAME = {0x00: 'goto', 0x02: 'if', 0x04: 'call', 0x06: 'ret', 0x08: 'set', 0x0A: 'set', 0x0C: 'add',
        0x0E: 'add', 0x10: 'sub', 0x12: 'sub', 0x14: 'and', 0x16: 'and', 0x18: 'or', 0x1A: 'or',
        0x1C: 'end', 0x1E: 'op1E', 0x20: 'run 8B:8000', 0x22: 'training', 0x24: 'op24',
        0x26: 'op26', 0x28: 'run 8C:8643', 0x2A: 'menu 8A:A8EE', 0x2C: 'card+', 0x2E: 'card2+',
        0x30: 'card3+', 0x32: 'op32', 0x34: 'op34', 0x36: 'run 8C:AB40', 0x38: 'fade-in',
        0x3A: 'fade-out', 0x3C: 'say', 0x3E: 'op3E', 0x40: 'op40', 0x42: 'op42', 0x44: 'scene',
        0x46: 'jump', 0x48: 'op48', 0x4A: 'op4A', 0x4C: 'op4C', 0x4E: 'run 8C:DD5B', 0x50: 'wait',
        0x52: 'op52', 0x54: 'op54', 0x56: 'op56', 0x58: 'op58', 0x5A: 'music', 0x5C: 'sound',
        0x5E: 'stop', 0x60: 'matches', 0x62: 'tally', 0x64: 'op64', 0x66: 'op66', 0x68: 'belt',
        0x6A: 'op6A', 0x6C: 'op6C', 0x6E: 'op6E', 0x70: 'staff roll', 0x72: 'records',
        0x74: 'team choice'}
BY_VAR = {0x08, 0x0C, 0x10, 0x14, 0x18}          # second operand is a variable
CMP = {0: '!=', 2: '==', 4: '<=', 6: '>=', 8: '<', 10: '>'}
CIRCUIT_STOP = bytes.fromhex('22606202110000')  # training, matches, tally, if v11 != 0
OP_TABLE = 0x8DC60F
RATING_STEP = 0x8DC49F          # LDA $1BF0 (rating / 10) before STA $7EF237 (v12), 8-bit A
CR_HOOKS = 0x8DEE70             # free space in bank $8D
CR_CHOICES, CR_CHOICE_N = 0x7E5E00, 0x7E5E40
CR_RESULTS, CR_RESULT_N = 0x7E5E80, 0x7E5E41
CR_AUTO = 0x7E5E42              # non-zero: choices come from CR_CHOICES instead of the menu


def to_off(addr):
    return ((addr >> 16) & 0x7F) * 0x8000 + (addr & 0x7FFF)


def decode(data, addr):
    """(length, text) of the opcode at addr, or None for a byte that is no opcode."""
    o = to_off(addr)
    op = data[o]
    if op not in LEN:
        return None
    n = LEN[op]
    if op == 0x4C and data[o + 1] & 3 == 2:
        n = 6
    b = data[o:o + n]
    bank = addr & 0xFF0000
    if op == 0x00:
        t = f'goto ${bank | b[1] | b[2] << 8:06X}'
    elif op == 0x02:
        rhs = f'v{b[3]:02X}' if b[2] & 0x10 else f'#{b[3]}'
        t = f'if v{b[1]:02X} {CMP.get(b[2] & 0xF, "?")} {rhs} goto ${bank | b[4] | b[5] << 8:06X}'
    elif op in (0x04, 0x46, 0x4A):
        t = f'{NAME[op]} ${b[3] << 16 | b[1] | b[2] << 8:06X}'
    elif 0x08 <= op <= 0x1A:
        t = f'{NAME[op]} v{b[1]:02X}, ' + (f'v{b[2]:02X}' if op in BY_VAR else f'#{b[2]}')
    elif op == 0x3C:
        t = f'say ${b[3] << 16 | b[1] | b[2] << 8:06X} face {b[4]}'
    else:
        t = NAME[op] + (' ' + b[1:].hex() if n > 1 else '')
    return n, t


def dis(data, start, end):
    a = start
    while a < end:
        x = decode(data, a)
        if x is None:
            print(f'${a:06X}  {data[to_off(a)]:02X}           ??')
            a += 1
            continue
        n, t = x
        print(f'${a:06X}  {data[to_off(a):to_off(a) + n].hex():12s} {t}')
        a += n


def targets(data, addr):
    """(next address or None, branch targets) of the opcode at addr."""
    o = to_off(addr)
    op = data[o]
    n = decode(data, addr)[0]
    b = data[o:o + n]
    bank = addr & 0xFF0000
    if op == 0x00:
        return None, [bank | b[1] | b[2] << 8]
    if op == 0x02:
        return addr + n, [bank | b[4] | b[5] << 8]
    if op == 0x04:
        return addr + n, [b[3] << 16 | b[1] | b[2] << 8]
    if op == 0x46:
        return None, [b[3] << 16 | b[1] | b[2] << 8]
    if op in (0x06, 0x1C):
        return None, []
    return addr + n, []


def english():
    """{file offset: English lines} of the dialogue strings."""
    import re
    out = {}
    for f in sorted(paths.SCRIPT.glob('bank_*.txt')):
        for block in re.split(r'\n(?=@ )', f.read_text(encoding='utf-8')):
            m = re.match(r'@ ([0-9a-fA-F]+)', block)
            if m:
                out[int(m.group(1), 16)] = [ln[3:] for ln in block.splitlines() if ln.startswith('EN ')]
    return out


def listing(data, entries):
    seen, todo, labels = {}, list(entries), set(entries)
    while todo:
        a = todo.pop()
        while a is not None and a not in seen:
            if decode(data, a) is None:
                seen[a] = None
                break
            seen[a] = decode(data, a)
            a, tg = targets(data, a)
            for t in tg:
                labels.add(t)
                todo.append(t)
    en = english()
    lines = []
    prev_end = None
    for a in sorted(seen):
        if prev_end is not None and a != prev_end:
            lines.append('')
        if a in labels:
            lines.append(f'L{a:06X}:')
        x = seen[a]
        if x is None:
            lines.append(f'  ${a:06X}  ?? {data[to_off(a)]:02X}')
            prev_end = a + 1
            continue
        n, t = x
        if t.startswith('say'):
            s = int(t.split()[1][1:], 16)
            text = ' '.join(en.get(to_off(s), ['(no entry)'])).replace('{p}', '').replace('{w}', '')
            t += '  | ' + text
        lines.append(f'  ${a:06X}  {t}')
        prev_end = a + n
    return '\n'.join(lines) + '\n'


def wctest(data):
    """Each stop: `goto` past Training, matches and tally, and the result test never fails."""
    out = bytearray(data)
    n = 0
    i = out.find(CIRCUIT_STOP)
    while i >= 0:
        nxt = 0x8000 | (i + 3) & 0x7FFF
        out[i:i + 3] = bytes([0x00, nxt & 0xFF, nxt >> 8])
        out[i + 5:i + 7] = b'\x02\xff'           # if v11 == 255 (never)
        n += 1
        i = out.find(CIRCUIT_STOP, i + 1)
    if n != 13:
        raise SystemExit(f'events: {n} World Circuit stops found, expected 13')
    return out


def crtest(data):
    """Champion Road test image: v12 (rating / 10) is always 255; op20 (the weekly schedule) and
    op26 (the card's match processing) are skipped; op28 (series results) sets v11 from the next CR_RESULTS byte (0 = won); op48 (a choice)
    shows its menu, or with CR_AUTO set takes v10 from the next CR_CHOICES byte."""
    import asm65816
    src = f"""
op20:   LDA.l $7EF221
        CLC
        ADC #$0001
        STA.l $7EF221
        JMP $C452
op28:   SEP #$30
        LDA.l ${CR_RESULT_N:06X}
        TAX
        INC A
        STA.l ${CR_RESULT_N:06X}
        LDA.l ${CR_RESULTS:06X},X
        STA.l $7EF236
        REP #$30
        LDA.l $7EF221
        CLC
        ADC #$0001
        STA.l $7EF221
        JMP $C452
op48:   LDA.l ${CR_AUTO:06X}
        AND #$00FF
        BNE auto
        JMP $CE52
auto:   SEP #$30
        LDA.l ${CR_CHOICE_N:06X}
        TAX
        INC A
        STA.l ${CR_CHOICE_N:06X}
        LDA.l ${CR_CHOICES:06X},X
        STA.l $7EF235
        REP #$30
        LDA.l $7EF221
        CLC
        ADC #$0002
        STA.l $7EF221
        JMP $C452
"""
    code, labels = asm65816.assemble(src, CR_HOOKS)
    out = bytearray(data)
    o = to_off(CR_HOOKS)
    if any(b != 0xFF for b in out[o:o + len(code)]):
        raise SystemExit('events: the hook space in bank $8D is not free')
    out[o:o + len(code)] = code
    for op, hook in ((0x20, 'op20'), (0x26, 'op20'), (0x28, 'op28'), (0x48, 'op48')):
        t = to_off(OP_TABLE) + op
        out[t:t + 2] = (labels[hook] & 0xFFFF).to_bytes(2, 'little')
    r = to_off(RATING_STEP)
    if out[r:r + 3] != b'\xad\xf0\x1b':
        raise SystemExit('events: unexpected code at the rating step')
    out[r:r + 3] = b'\xa9\xff\xea'                # LDA #$FF / NOP
    return out


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ['dis'] and len(argv) == 3:
        dis(paths.ROM.read_bytes(), int(argv[1], 16), int(argv[2], 16))
    elif argv[:1] == ['listing'] and len(argv) >= 3:
        Path(argv[-1]).write_text(listing(paths.ROM.read_bytes(), [int(a, 16) for a in argv[1:-1]]),
                                  encoding='utf-8')
    elif argv[:1] == ['crtest'] and len(argv) in (2, 3):
        src = Path(argv[1]) if len(argv) == 3 else paths.BUILD / f'{paths.GAME_FILE} (English){paths.ROM.suffix}'
        Path(argv[-1]).write_bytes(crtest(src.read_bytes()))
        print(f'{argv[-1]}: Champion Road test image (rating gates open, series skipped; not for release)')
    elif argv[:1] == ['wctest'] and len(argv) in (2, 3):
        src = Path(argv[1]) if len(argv) == 3 else paths.BUILD / f'{paths.GAME_FILE} (English){paths.ROM.suffix}'
        Path(argv[-1]).write_bytes(wctest(src.read_bytes()))
        print(f'{argv[-1]}: every World Circuit stop is won (test image, not for release)')
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
