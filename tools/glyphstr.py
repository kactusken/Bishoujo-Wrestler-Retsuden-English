#!/usr/bin/env python3
"""Glyph strings: menu and window texts drawn from a screen's own glyph set (build step).

  glyphstr.py scan                 every string call site the scanner understands -> stdout
  glyphstr.py dump SET ADDR...     add strings (CPU addresses, hex) to translation/text/menu_SET.txt

Most menu texts are 8-bit glyph indices ending in $FF, drawn by $8C:A9E7 (index + $3C ->
$80:BC43: 2x2 tiles from the $89:8000 table, cursor + 2). A call site looks like
  LDA #pos / CLC / ADC $16FC / STA $16FE / ... / LDA #bank / STA $3A / LDA #addr / STA $38 /
  STZ $3C (or LDA #n / STA $3C) / JSL $8CA9E7
The glyphs come from a packed 2bpp tile set loaded to BG3 tile 0 for a family of screens (SETS).

English, per set: the strings listed in translation/text/menu_SET.txt are converted, the others
keep working in Japanese. The letters (tools/font8.py) are drawn into the halves of glyph slots
that no string of the set left in Japanese uses (code b = tile b + (b & $F0), bottom +$10); the converted strings
move to bank STR_BANK (2 KB per set, 'str_at'), and their call sites point there and call TextH (a copy of $8C:A9E7 that
draws one 8-pixel cell per code). Strings are padded to their width so a shorter text replaces
a longer one completely. The tile set is repacked into its own bank and its loader repointed.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import asm65816  # noqa: E402
import blocks  # noqa: E402
import font8  # noqa: E402
import kpack  # noqa: E402
import paths  # noqa: E402
import snes  # noqa: E402

ROUTINE = 0x8CA9E7
STR_BANK = 0xE3
HOOK_ADDR = 0xD09600

SETS = {
    # character select, faction select, records: glyph set $92:9416 (loader $8B:D7F6)
    'select': {
        'block': 0x929416, 'tiles_bank': 0xE4, 'str_at': 0x8000, 'hires': 'statsup',
        # the System menu (Save / Load / Back to Title)
        'tables': [(0x8CF752, [1, 2, 3], 0x8CF70B, 0x8CF71B)],
        # drawn by $8C:AA1B (one tile per code) with this set: status screen labels
        'protect': [0x8AFF9F, 0x8AFFA3, 0x8AFFA7, 0x8AFFAB] + list(range(0x8AFF4B, 0x8AFF9C, 6)) +
                   [0x8AFF87, 0x8AFF8B, 0x8AFF8F, 0x8AFF93, 0x8AFF97, 0x8AFF9B],
        'glyphs': ('　。・ーー％０１２３４５６７８９ＢＨＰＸいげさしすてにびるをイグ'
                   'セタトドニパフブボメラリルレロワン下価回関器規筋軍撃決御公攻根算'
                   '子主手所女勝新人性成正績節選速属打体団値通定度投能敗反飛評復防戻用要乱率力'),
    },
    # ring name, new game / load / save: glyph set $91:DC15 (loader $8B:D752)
    'data': {
        'block': 0x91DC15, 'tiles_bank': 0xE5, 'str_at': 0x8800, 'hires': 'logic',
        'tables': [(0x8A9DFF, [0, 1, 2, 3, 4, 5], 0x8A9D2D, 0x8A9D37)],     # promotion short names
        # drawn by $8C:AA1B with this set: logic pattern screen labels
        'protect': [0x8B8983, 0x8B8987, 0x8B898C, 0x8BCD1D, 0x8BCD26, 0x8BCD2C, 0x8BCD32, 0x8BCD38,
                    0x8BCD3E, 0x8BCD4C, 0x8BCD52, 0x8BCD5C, 0x8BCD66, 0x8BCD70, 0x8BCD57, 0x8BCD61,
                    0x8BCD6B, 0x8BCD75],
        'reserve': [0x0F, 0x10, 0x1B, 0x1C],     # Ａ Ｂ Ｘ Ｙ: the option grid's buttons, drawn by code
        'glyphs': ('　。・：ー０１２３４５６７８９ＡＢＣＥＦＧＩＭＮＳＵＷＸＹあいが'
                   'さしせてでまりをんアォオクグシジスセタッデトドネパフブプマムョリ'
                   'ルロワン安一下価外間気技均型撃攻合最殺子終準女場常新戦選耐大第択値通定突日忍必標評平返'),
    },
    # match card, title match results: glyph set $97:D6CC (loader $8B:D848)
    'match': {
        'block': 0x97D6CC, 'tiles_bank': 0xE6, 'str_at': 0x9000,
        'tables': [(0x8DEA88, [0, 1, 2, 3, 4, 5], 0x8DE9B0, 0x8DE9B8),      # tournament names
                   (0x8E9985, list(range(1, 12)), 0x8E990A, 0x8E9911)],     # faction names
        'glyphs': ('　。ー０１２３４５６７８９ＡＣＤＥＦＩＮＯＲＳＵＷＸＹｉｋｕがし'
                   'たまアイオカクグスズタッテトドナニハバボマメラリルワンヶ維衛鋭王'
                   '確革規軍決権合子市試若取手女勝新人世正精戦選組代奪谷団値超日能防本命優予利率龍力'),
    },
    # options: glyph set $97:E9F0 (loader $8B:D89A)
    'options': {
        'block': 0x97E9F0, 'tiles_bank': 0xE7, 'str_at': 0x9800,
        'tables': [(0x8EF1B9, [0, 1, 2], 0x8EF1AB, 0x8EF1B3)],              # difficulty
        'glyphs': '　ー０１２３４５６７８９いうおそつはふやイオクジスセッテドノハマミメモュラルレ',
    },
    # show card list header (promotion or faction name): glyph set $92:C421, one loader
    'card': {
        'block': 0x92C421, 'tiles_bank': 0xF8, 'str_at': 0xA000,
        'tables': [(0x8C93CC, list(range(1, 9)), 0x8C935B, 0x8C9362),     # promotions, League...
                   (0x8C93DE, list(range(1, 9)), 0x8C9396, 0x8C939D)],    # factions
        'patches': [(0x8CA111, b'\xff')],   # the small プロレス after the name (now in the name)
        'glyphs': ('　ー○●ACEFISUWYikuオカグスズトドナニハバメリルワンヶ維鋭革規軍子市若手女新世正精戦'
                   '代谷団超日本命龍'),
    },
}

HOOK = '''
.m16
.x16
TextH:                  ; copy of $8C:A9E7 for converted strings: one 8-pixel cell per code
  LDY #$0000
t_loop:
  LDA [$38],Y
  AND #$00FF
  CMP #$00FF
  BEQ t_end
  PHY
  JSL CellH
  PLY
  INY
  BRA t_loop
t_end:
  RTL

CellH:                  ; A = code b: tiles b + (b & $F0) and +$10 at the cursor, cursor + 1
  PHA
  AND #$00F0
  CLC
  ADC 1,S
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


LEFT = {}                                # set -> glyph cells no letter took (for tools/hires.py)


def hires_strings(cfg):
    """Addresses of the strings with English in the hires text file that shares this set."""
    if 'hires' not in cfg:
        return set()
    path = paths.TRANSLATION / 'text' / f'hires_{cfg["hires"]}.txt'
    if not path.exists():
        return set()
    return {int(b.id, 16) for b in blocks.BlockFile(path).blocks if b.english}


def to_off(addr):
    return ((addr >> 16) & 0x7F) * 0x8000 + (addr & 0x7FFF)


def to_cpu(off):
    return 0x800000 | ((off // 0x8000) << 16) | 0x8000 | (off % 0x8000)


def scan(data):
    """[(site file offset, string CPU address, {'bank': off, 'addr': off}, $3C)] for JSL $8CA9E7."""
    jsl = bytes([0x22, ROUTINE & 0xFF, (ROUTINE >> 8) & 0xFF, ROUTINE >> 16])
    out = []
    i = data.find(jsl)
    while i != -1:
        w0 = max(0, i - 40)
        w = data[w0:i]
        m38 = list(re.finditer(rb'\xa9(..)\x85\x38', w, re.S))
        m3a = list(re.finditer(rb'\xa9(.)\x00\x85\x3a', w, re.S))
        c3 = 0 if w.endswith(b'\x64\x3c') else None
        if m38 and m3a:
            a = m38[-1].group(1)[0] | m38[-1].group(1)[1] << 8
            bank = m3a[-1].group(1)[0]
            out.append((i, bank << 16 | a, {'addr': w0 + m38[-1].start() + 1, 'bank': w0 + m3a[-1].start() + 1}, c3))
        i = data.find(jsl, i + 1)
    return out


def string_bytes(data, addr):
    o = to_off(addr)
    e = data.find(b'\xff', o)
    return data[o:e]


def decode(b, glyphs):
    return ''.join(glyphs[x] if x < len(glyphs) else '{%02X}' % x for x in b)


def text_path(name):
    return paths.TRANSLATION / 'text' / f'menu_{name}.txt'


def dump(name, addrs):
    data = paths.ROM.read_bytes()
    cfg = SETS[name]
    sites = scan(data)
    path = text_path(name)
    bf = blocks.BlockFile(path) if path.exists() else None
    lines = [f'# menu_{name}: glyph strings of the glyph set ${cfg["block"]:06X} (tools/glyphstr.py).',
             '# EN may be as wide as the JP (2 letters per JP glyph); "width=N" in the @ line allows N.', '']
    known = {b.id for b in bf.blocks} if bf else set()
    if bf:
        lines = bf.text().splitlines()
    for a in addrs:
        ident = f'{a:06X}'
        if ident in known:
            continue
        b = string_bytes(data, a)
        s = [f'{to_cpu(o):06X}' for o, sa, _, _ in sites if sa == a]
        lines += [f'@ {ident} sites={",".join(s)} width={2 * len(b)}', 'JP ' + decode(b, cfg['glyphs']), '']
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')
    print(f'{paths.show(path)}')


def find_loader(data, block):
    """File offsets of LDY #lo / LDA #bank that load the packed tile set."""
    pat = bytes([0xA0, block & 0xFF, (block >> 8) & 0xFF, 0xA9, block >> 16])
    out = []
    i = data.find(pat)
    while i != -1:
        out.append(i)
        i = data.find(pat, i + 1)
    return out


def apply(rom, name):
    cfg = SETS[name]
    path = text_path(name)
    if not path.exists():
        return 0, 0
    data = bytes(rom)
    bf = blocks.BlockFile(path)
    todo = [b for b in bf.blocks if b.english]
    if not todo:
        return 0, 0
    sites = scan(data)
    conv = {int(b.id, 16): b for b in todo}
    # glyph slots used by converted strings and not by any other scanned string of the set
    used_conv = set()
    for a in conv:
        used_conv |= set(string_bytes(data, a))
    used_other = set()                   # strings of the set left in Japanese (no EN lines)
    for b in bf.blocks:
        if not b.english:
            used_other |= set(string_bytes(data, int(b.id, 16)))
    hires_conv = hires_strings(cfg)      # strings tools/hires.py converts with full-slot letters
    used_hires = set()
    for a in hires_conv:
        used_hires |= set(string_bytes(data, a))
    used_protect = set()
    for a in cfg.get('protect', []):     # strings of the set drawn by other routines
        if a not in hires_conv:
            used_protect |= set(string_bytes(data, a))
    reserve = set(cfg.get('reserve', []))   # slots drawn by code, not by any string
    slots = sorted(used_conv - used_other - used_protect - used_hires - reserve - {0, 0xFF})
    cells = [c for n in slots for c in (2 * n, 2 * n + 1) if c < 0xFE]
    # slots only the hires strings used: free for tools/hires.py, with the cells left over below
    hslots = sorted(used_hires - used_other - used_protect - set(slots) - reserve - {0, 0xFF})
    chars = sorted({ch for b in todo for s in b.english for ch in s} - {' '})
    bad = set(chars) - set(font8.CODES)
    if bad:
        raise SystemExit(f'menu_{name}: characters not in the font: {"".join(sorted(bad))}')
    if len(chars) > len(cells):
        raise SystemExit(f'menu_{name}: {len(chars)} letters, {len(cells)} free cells')
    code = {' ': 0}
    code.update({ch: cells[i] for i, ch in enumerate(chars)})
    LEFT[name] = sorted(cells[len(chars):] + [c for n in hslots for c in (2 * n, 2 * n + 1)])
    # tile set
    loaders = find_loader(data, cfg['block'])
    if not loaders:
        raise SystemExit(f'menu_{name}: no loader of ${cfg["block"]:06X}')
    tiles, _ = kpack.unpack(data, to_off(cfg['block']))
    tiles = bytearray(tiles)
    ref = None                           # the colour of the glyphs: copy the planes of glyph 1
    for y in range(8):
        t = (1 & 7) * 2
        p0, p1 = tiles[t * 16 + 2 * y], tiles[t * 16 + 2 * y + 1]
        if p0 or p1:
            ref = (bool(p0), bool(p1))
    ref = ref or (True, False)
    f8 = font8.glyph_bytes()
    for ch, b in code.items():
        if b == 0:
            continue
        t = b + (b & 0xF0)
        g = f8[font8.CODES[ch] * 16:font8.CODES[ch] * 16 + 16]
        for half in range(2):
            o = (t + 16 * half) * 16
            for y in range(8):
                tiles[o + 2 * y] = g[half * 8 + y] if ref[0] else 0
                tiles[o + 2 * y + 1] = g[half * 8 + y] if ref[1] else 0
    packed = kpack.pack(bytes(tiles))
    r = snes.Rom(rom)
    to = r.to_file((cfg['tiles_bank'] << 16) | 0x8000)
    rom[to:to + len(packed)] = packed
    for i in loaders:
        rom[i + 1:i + 3] = bytes([0x00, 0x80])
        rom[i + 4] = cfg['tiles_bank']
    # hook
    hook, labels = asm65816.assemble(HOOK, HOOK_ADDR)
    ho = r.to_file(HOOK_ADDR)
    rom[ho:ho + len(hook)] = hook
    # strings
    base = r.to_file((STR_BANK << 16) | 0x8000)
    pos = cfg['str_at']                  # each set has its own area of the string bank
    nsites = 0
    newpos = {}
    for a, b in conv.items():
        m = re.search(r'width=(\d+)', b.meta)
        width = int(m.group(1)) if m else 2 * len(string_bytes(data, a))
        s = ' '.join(b.english) if len(b.english) > 1 else b.english[0]
        if len(s) > width:
            raise SystemExit(f'menu_{name} @{b.id}: {len(s)} letters, width {width}')
        body = bytes(code[c] for c in s.ljust(width)) + b'\xff'
        rom[base + pos - 0x8000:base + pos - 0x8000 + len(body)] = body
        for site, sa, at, _ in sites:
            if sa != a:
                continue
            rom[at['addr']:at['addr'] + 2] = bytes([pos & 0xFF, pos >> 8])
            rom[at['bank']] = STR_BANK
            rom[site + 1:site + 4] = bytes([labels['TextH'] & 0xFF, (labels['TextH'] >> 8) & 0xFF, labels['TextH'] >> 16])
            nsites += 1
        newpos[a] = pos
        pos += len(body)
    for tab, idx, ldab, jsl in cfg.get('tables', []):
        # (table of 16-bit pointers, entries, LDA #bank before the draw, its JSL $8CA9E7)
        to = to_off(tab)
        addrs = [(tab & 0xFF0000) | data[to + 2 * i] | data[to + 2 * i + 1] << 8 for i in idx]
        if not all(a in newpos for a in addrs):
            if any(a in newpos for a in addrs):
                raise SystemExit(f'menu_{name}: table ${tab:06X}: translate all its strings or none')
            continue
        if data[to_off(ldab)] != 0xA9 or data[to_off(jsl):to_off(jsl) + 4] != b'\x22\xe7\xa9\x8c':
            raise SystemExit(f'menu_{name}: table ${tab:06X}: unexpected code')
        for i, a in zip(idx, addrs):
            rom[to + 2 * i:to + 2 * i + 2] = newpos[a].to_bytes(2, 'little')
            nsites += 1
        rom[to_off(ldab) + 1] = STR_BANK
        rom[to_off(jsl) + 1:to_off(jsl) + 4] = labels['TextH'].to_bytes(3, 'little')
    for a, b in cfg.get('patches', []):
        rom[to_off(a):to_off(a) + len(b)] = b
    if pos > cfg['str_at'] + 0x800:
        raise SystemExit(f'menu_{name}: strings overrun their 2 KB area')
    return len(conv), nsites


def main(argv=None):
    argv = paths.configure(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ['scan']:
        data = paths.ROM.read_bytes()
        for site, a, _, c3 in scan(data):
            print(f'{to_cpu(site):06X} {a:06X} 3c={c3} ' + ' '.join(f'{x:02X}' for x in string_bytes(data, a)[:16]))
    elif argv[:1] == ['dump'] and len(argv) >= 3:
        dump(argv[1], [int(a, 16) for a in argv[2:]])
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
