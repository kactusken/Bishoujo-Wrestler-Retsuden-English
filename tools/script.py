#!/usr/bin/env python3
"""The dialogue script: packed 10-bit codes, reached from the event scripts by opcode $3C.

  script.py dump [--force]       ROM -> translation/script/bank_XX.txt (keeps files that exist;
                                 --force rewrites them, keeping EN lines and comments by id)
  script.py show OFFSET          decode one string (file offset, hex ok)
  script.py check [FILE...]      translated blocks: characters, codes, line widths, pages
  script.py check-part PART      the same for a translator's part file
  script.py merge PART...        copy the EN lines of part files into translation/script/
  script.py stats                strings, translated, references

Encoding (docs/TECHNICAL.md "Text"): 4 codes in 5 bytes - bytes 0-3 are the low 8 bits, byte 4
the high 2 bits (code 0 in bits 7-6 ... code 3 in bits 1-0). A string ends with the group that
holds $3FF. Codes below $3B7 are glyphs of the font at $98:8000 (translation/tables/font98.tsv);
$3E0-$3FF are controls. In the block files:

  {p}       $3E0  page start (clears the window)    {w}   $3E1  end of page: wait for a button
  {s1}-{s6} $3E3-$3E8  name of the scene's speaker 1-6 (drawn by the game, 4 name glyphs)
  {n1}-{n6} $3EB-$3F0  other names of the scene (4 name glyphs)
  {player}  $3F1  the player's ring name (8 name glyphs)
  {3E2} {3E9} {3EA}  rare controls kept as they are
  each line of a block is one line on screen ($3FE between lines); $3FF ends the string.

The game draws a page with at most 4 lines. The English is drawn by our own 8x16 renderer
(docs/TECHNICAL.md "English text"): one letter per 8-pixel column, LINE_WIDTH letters per line.
Lines that are too long are wrapped at spaces by the encoder and pages that grow past 4 lines
are split ({w} + {p}), so the checker reports them as warnings, not errors.

The @ line: file offset, then refs=N (how many $3C opcodes point at it; 0 = no reference found,
probably unused - translated anyway).

A $3C opcode is `3C ptr24 slot`: slot 0-9 shows the face of the scene's character in that slot at
the left of the window ($8C:ADD2), 99 none. A string shown with a face is never narration.
"""
import collections
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blocks  # noqa: E402
import paths  # noqa: E402

FONT_TSV = paths.TRANSLATION / 'tables' / 'font98.tsv'
SCRIPT_DIR = paths.TRANSLATION / 'script'
SCRIPT_BANKS = (0x94, 0x95, 0x96, 0x99, 0x9A, 0x9B, 0xCF)   # LoROM banks that hold the dialogue
EVENT_BANKS = (0x88, 0x93)                                   # event scripts with $3C pointers
LAST_GLYPH = 0x3B6
FACE_SLOTS = 10         # $3C slot bytes below this show a face
LINE_WIDTH = 30          # English letters per line (8-pixel columns 2-31)
INDENT = 4               # strings with a speaker face (or a choice menu) start at column 6: 26 letters
PAGE_LINES = 4
NAME_WIDTH = 8           # {s1}.. {n1}..: 4 name glyphs of 2 letters
PLAYER_WIDTH = 16

# Strings reached through tables of 24-bit pointers instead of event scripts:
# name -> (file offset of the table, entries, letters per line, lines). No pages: drawn whole.
TABLES = {
    'profiles': (0x639C1, 63, 28, 4),     # wrestler profiles ($8C:B83B, 4 lines in the profile box)
}

CONTROL = {0x3E0: '{p}', 0x3E1: '{w}', 0x3E2: '{3E2}', 0x3E9: '{3E9}', 0x3EA: '{3EA}', 0x3F1: '{player}'}
CONTROL.update({0x3E3 + i: '{s%d}' % (i + 1) for i in range(6)})
CONTROL.update({0x3EB + i: '{n%d}' % (i + 1) for i in range(6)})
TOKENS = {v: k for k, v in CONTROL.items()}
BREAK, END = 0x3FE, 0x3FF
NAME_TOKENS = {t for t in TOKENS if t.startswith('{s') or t.startswith('{n')}

# Characters the English font has (tools/font8.py draws them).
CHARSET = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 !"#$%&\'()*+,-./:;<=>?@[]_~…♥♪')


def to_cpu(off):
    return 0x800000 | ((off // 0x8000) << 16) | 0x8000 | (off % 0x8000)


def to_off(addr):
    return ((addr >> 16) & 0x7F) * 0x8000 + (addr & 0x7FFF)


def font_table():
    t = {}
    for line in FONT_TSV.read_text(encoding='utf-8').splitlines():
        if line.startswith('#') or not line.strip():
            continue
        c, ch, _ = line.split('\t')
        t[int(c, 16)] = ch
    return t


def unpack_codes(data, p):
    """Codes of the string at file offset p (up to and including $3FF), and the end offset."""
    out = []
    while True:
        g = data[p:p + 5]
        if len(g) < 5:
            raise ValueError(f'{p:#x}: string runs past the end')
        p += 5
        for i in range(4):
            c = g[i] | ((g[4] >> (6 - 2 * i)) & 3) << 8
            out.append(c)
            if c == END:
                return out, p


def pack_codes(cs):
    """Codes (ending in $3FF) -> bytes; the last group is padded with $000."""
    cs = list(cs)
    while len(cs) % 4:
        cs.append(0)
    out = bytearray()
    for i in range(0, len(cs), 4):
        g = cs[i:i + 4]
        out += bytes(c & 0xFF for c in g)
        out.append(sum(((c >> 8) & 3) << (6 - 2 * k) for k, c in enumerate(g)))
    return bytes(out)


def decode(cs, table=None):
    """Codes -> block lines (split at $3FE), without the terminator."""
    table = table or font_table()
    lines, cur = [], ''
    for c in cs:
        if c == END:
            break
        if c == BREAK:
            lines.append(cur)
            cur = ''
        elif c in CONTROL:
            cur += CONTROL[c]
        elif c <= LAST_GLYPH:
            cur += table.get(c, '{%03X}' % c)
        else:
            cur += '{%03X}' % c
    lines.append(cur)
    return lines


def find_strings(data):
    """{offset: end} of every string in the script banks plus every string an event $3C points at;
    and {offset: [reference offsets]}."""
    def valid(p):
        try:
            cs, q = unpack_codes(data, p)
        except ValueError:
            return None
        if len(cs) > 3000 or not all(c <= LAST_GLYPH or c >= 0x3E0 for c in cs):
            return None
        if not any(c <= LAST_GLYPH and c for c in cs):
            return None
        return q

    starts = {}
    for bank in SCRIPT_BANKS:
        p, end = (bank & 0x7F) * 0x8000, (bank & 0x7F) * 0x8000 + 0x8000
        while p < end - 5:
            if data[p] == 0xE0 and data[p + 4] >> 6 == 3:
                q = valid(p)
                if q:
                    starts[p] = q
                    p = q
                    continue
            p += 1
    refs = collections.defaultdict(list)
    for bank in EVENT_BANKS:
        base = (bank & 0x7F) * 0x8000
        for i in range(base, base + 0x8000 - 3):
            if data[i] == 0x3C and data[i + 3] & 0x80 and data[i + 2] & 0x80:
                o = to_off(data[i + 1] | data[i + 2] << 8 | data[i + 3] << 16)
                if o in starts:
                    refs[o].append(i)
    return starts, dict(refs)


def faced(data, refs):
    """File offsets of the strings some $3C opcode shows with a face."""
    return {o for o, rs in refs.items() if any(data[r + 4] < FACE_SLOTS for r in rs)}


_FACED = None


def rom_faced():
    """faced() of the original ROM, for the checker (empty if the ROM is missing)."""
    global _FACED
    if _FACED is None:
        try:
            data = paths.ROM.read_bytes()
        except OSError:
            data = None
        _FACED = faced(data, find_strings(data)[1]) if data else set()
    return _FACED


HEADER = '''# Dialogue of bank ${bank:02X} (tools/script.py; format and codes: docs/TRANSLATION.md).
# One JP/EN line = one line on screen. {{p}} starts a page, {{w}} waits for a button at its end.
# Names ({{s1}} {{n1}} {{player}}) are drawn by the game. Lines up to {width} letters, pages up to {lines}
# lines (a speaker name alone on the first line counts as a line). Longer lines are wrapped and
# full pages split by the encoder, but write to fit where you can.'''


def dump(force=False):
    data = paths.ROM.read_bytes()
    starts, refs = find_strings(data)
    table = font_table()
    SCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    by_bank = collections.defaultdict(list)
    for p in sorted(starts):
        by_bank[0x80 | (p // 0x8000)].append(p)
    dump_tables(data, force)
    for bank, offs in sorted(by_bank.items()):
        path = SCRIPT_DIR / f'bank_{bank:02X}.txt'
        old = blocks.BlockFile(path) if path.exists() else None
        if old and not force:
            print(f'kept {paths.show(path)}')
            continue
        lines = [HEADER.format(bank=bank, width=LINE_WIDTH, lines=PAGE_LINES), '']
        for p in offs:
            cs, _ = unpack_codes(data, p)
            ident = f'{p:06x}'
            lines.append(f'@ {ident} refs={len(refs.get(p, []))}')
            ob = old.get(ident) if old else None
            if ob:
                lines += [t for k, t in ob.lines if k == '#']
            lines += ['JP ' + s for s in decode(cs, table)]
            if ob:
                lines += ['EN ' + s for s in ob.english]
            lines.append('')
        path.write_text('\n'.join(lines), encoding='utf-8', newline='\n')
        print(f'{paths.show(path)}: {len(offs)} strings')


def table_strings(data, name):
    """{string offset: [file offsets of the table entries pointing at it]} for a TABLES entry."""
    at, n = TABLES[name][:2]
    out = collections.defaultdict(list)
    for i in range(n):
        o = at + 3 * i
        out[to_off(data[o] | data[o + 1] << 8 | data[o + 2] << 16)].append(o)
    return dict(out)


def dump_tables(data, force):
    table = font_table()
    for name, (at, n, width, nlines) in TABLES.items():
        path = SCRIPT_DIR / f'{name}.txt'
        old = blocks.BlockFile(path) if path.exists() else None
        if old and not force:
            print(f'kept {paths.show(path)}')
            continue
        lines = [f'# {name}: strings reached through the pointer table at file {at:#x} ({n} entries).',
                 f'# No pages: the whole string is drawn at once, up to {nlines} lines of {width} letters.', '']
        for p, refs in sorted(table_strings(data, name).items()):
            cs, _ = unpack_codes(data, p)
            ident = f'{p:06x}'
            lines.append(f'@ {ident} table={name} refs={len(refs)}')
            ob = old.get(ident) if old else None
            if ob:
                lines += [t for k, t in ob.lines if k == '#']
            lines += ['JP ' + x for x in decode(cs, table)]
            if ob:
                lines += ['EN ' + x for x in ob.english]
            lines.append('')
        path.write_text('\n'.join(lines), encoding='utf-8', newline='\n')
        print(f'{paths.show(path)}: {len(table_strings(data, name))} strings')


TOKEN_RE = re.compile(r'\{[^}]*\}')


def line_width(s):
    w = 0
    for part in re.split(r'(\{[^}]*\})', s):
        if not part:
            continue
        if part.startswith('{'):
            w += NAME_WIDTH if part in NAME_TOKENS else PLAYER_WIDTH if part == '{player}' else 0
        else:
            w += len(part)
    return w


def wrap(lines, width=LINE_WIDTH):
    """Lines -> lines no wider than `width`, broken at spaces (tokens never split)."""
    out = []
    for s in lines:
        while line_width(s) > width:
            cut = None
            for m in re.finditer(r' ', s):
                if line_width(s[:m.start()]) <= width:
                    cut = m.start()
            if cut is None:
                break
            out.append(s[:cut])
            s = s[cut + 1:]
        out.append(s)
    return out


def is_narration(lines, face=False):
    """A string shown without a face, with no speaker code, whose every page waits ({w}) is drawn
    from column 2; others (faces fill columns 0-5, choice menus) keep the original column 6."""
    if face or any(re.search(r'\{s\d\}', s) for s in lines):
        return False
    return all(any('{w}' in s for s in page) for page in split_pages(lines))


def width_for(lines, face=False):
    return LINE_WIDTH if is_narration(lines, face) else LINE_WIDTH - INDENT


def split_pages(lines):
    """Lines -> list of pages (each a list of lines); a page starts at a line beginning with {p}."""
    pages = []
    for s in lines:
        if s.startswith('{p}') or not pages:
            pages.append([])
        pages[-1].append(s)
    return pages


def layout(lines, table=None, face=False):
    """Table strings (TABLES): wrapped to their width, no pages. Dialogue: wrap and paginate English block lines (pages of at most PAGE_LINES lines: a page that grows
    gets {w} + {p} inserted), and indent non-narration strings to column 6. Returns the lines."""
    if table:
        width, nlines = TABLES[table][2], TABLES[table][3]
        out = wrap(lines, width)
        if len(out) > nlines:
            raise ValueError(f'{len(out)} lines after wrapping, the box holds {nlines}')
        return out
    narr = is_narration(lines, face)
    width = width_for(lines, face)
    out = []
    for page in split_pages(lines):
        body = wrap(page, width)
        first = True
        while body:
            chunk, body = body[:PAGE_LINES], body[PAGE_LINES:]
            if not first and not chunk[0].startswith('{p}'):
                chunk[0] = '{p}' + chunk[0]
            if body:
                chunk[-1] = chunk[-1].replace('{w}', '') + '{w}'
            out.extend(chunk)
            first = False
    if not narr:
        out = ['{p}' + ' ' * INDENT + s[3:] if s.startswith('{p}') else ' ' * INDENT + s for s in out]
    return out


MAX_CODES = 0x180           # the dialogue buffer: $7E:F400, 0x300 bytes (tools/layout.py)


def encode(lines, table=None, face=False):
    """English block lines -> codes ending in $3FF (layout() first: wrapped, paginated)."""
    import font8
    out = []
    for i, line in enumerate(layout(lines, table, face)):
        if i:
            out.append(BREAK)
        for part in re.split(r'(\{[^}]*\})', line):
            if not part:
                continue
            if part.startswith('{'):
                if part not in TOKENS:
                    raise ValueError(f'unknown code {part}')
                out.append(TOKENS[part])
            else:
                for ch in part:
                    if ch not in font8.CODES:
                        raise ValueError(f'character not in the font: {ch!r}')
                    out.append(font8.CODES[ch])
    out.append(END)
    return out


def insert(rom, first_bank):
    """Pack every translated, referenced string into banks first_bank.. of `rom` (bytearray, already
    expanded) and point the $3C references at them. Returns (strings, bytes, last bank used)."""
    data = bytes(rom)
    starts, refs = find_strings(data)
    faces = faced(data, refs)
    bank, pos = first_bank, 0
    n = total = 0
    for f in sorted(SCRIPT_DIR.glob('bank_*.txt')):
        bf = blocks.BlockFile(f)
        for b in bf.blocks:
            if not b.english:
                continue
            off = int(b.id, 16)
            if off not in starts:
                raise SystemExit(f'{paths.show(f)} @{b.id}: no string starts there in the ROM')
            if off not in refs:
                continue                      # no reference: never shown
            try:
                codes = encode(b.english, face=off in faces)
            except ValueError as e:
                raise SystemExit(f'{paths.show(f)} @{b.id}: {e}')
            if len(codes) > MAX_CODES:
                raise SystemExit(f'{paths.show(f)} @{b.id}: {len(codes)} codes, the dialogue buffer holds {MAX_CODES}'
                                 ' (tools/layout.py): split the text or shorten it')
            packed = pack_codes(codes)
            if pos + len(packed) > 0x8000:
                bank, pos = bank + 1, 0
                if bank > 0xDF:
                    raise SystemExit('script: the English does not fit in banks $D1-$DF')
            addr = (bank << 16) | 0x8000 | pos
            o = to_off(addr)
            rom[o:o + len(packed)] = packed
            for r in refs[off]:
                rom[r + 1:r + 4] = bytes([addr & 0xFF, (addr >> 8) & 0xFF, addr >> 16])
            pos += len(packed)
            n += 1
            total += len(packed)
    for name in TABLES:
        path = SCRIPT_DIR / f'{name}.txt'
        if not path.exists():
            continue
        trefs = table_strings(data, name)
        for b in blocks.BlockFile(path).blocks:
            if not b.english:
                continue
            try:
                packed = pack_codes(encode(b.english, name))
            except ValueError as e:
                raise SystemExit(f'{paths.show(path)} @{b.id}: {e}')
            if pos + len(packed) > 0x8000:
                bank, pos = bank + 1, 0
            addr = (bank << 16) | 0x8000 | pos
            o = to_off(addr)
            rom[o:o + len(packed)] = packed
            for r in trefs[int(b.id, 16)]:
                rom[r:r + 3] = bytes([addr & 0xFF, (addr >> 8) & 0xFF, addr >> 16])
            pos += len(packed)
            n += 1
            total += len(packed)
    return n, total, bank


def check_lines(ident, en, jp):
    """Problems (errors, warnings) of one translated block."""
    errors, warnings = [], []
    width = width_for(en, int(ident, 16) in rom_faced())
    toks_en = [t for t in TOKEN_RE.findall('\n'.join(en))]
    toks_jp = [t for t in TOKEN_RE.findall('\n'.join(jp))]
    for t in toks_en:
        if t not in TOKENS:
            errors.append(f'unknown code {t}')
    if [t for t in toks_en if t not in ('{p}', '{w}')] != [t for t in toks_jp if t not in ('{p}', '{w}')]:
        errors.append(f'name/other codes differ from the JP: {toks_jp} vs {toks_en}')
    if bool(en) and en[0].startswith('{p}') != bool(jp and jp[0].startswith('{p}')):
        errors.append('first line must start with {p} like the JP')
    for s in en:
        bad = set(TOKEN_RE.sub('', s)) - CHARSET
        if bad:
            errors.append(f'characters not in the font: {"".join(sorted(bad))}')
        if line_width(s) > width:
            warnings.append(f'line wider than {width} ({line_width(s)}): {s}')
    for page in split_pages(en):
        if len(page) > PAGE_LINES:
            warnings.append(f'page of {len(page)} lines (max {PAGE_LINES}): will be split')
    return errors, warnings


def check_table_lines(name, en, jp):
    errors, warnings = [], []
    if TOKEN_RE.findall('\n'.join(en)) != TOKEN_RE.findall('\n'.join(jp)):
        errors.append('codes differ from the JP')
    for s in en:
        bad = set(TOKEN_RE.sub('', s)) - CHARSET
        if bad:
            errors.append(f'characters not in the font: {"".join(sorted(bad))}')
    try:
        layout(en, name)
    except ValueError as e:
        errors.append(str(e))
    for s in en:
        if line_width(s) > TABLES[name][2]:
            warnings.append(f'line wider than {TABLES[name][2]} ({line_width(s)}): {s}')
    return errors, warnings


def check_file(path, show_warnings=True):
    bf = blocks.BlockFile(path)
    ne = nw = 0
    for b in bf.blocks:
        en = b.english
        if not en:
            continue
        m = re.search(r'table=(\w+)', b.meta)
        if m:
            errors, warnings = check_table_lines(m.group(1), en, bf.source(b))
        else:
            errors, warnings = check_lines(b.id, en, bf.source(b))
        for e in errors:
            print(f'{paths.show(path)} @{b.id}: ERROR {e}')
        if show_warnings:
            for w in warnings:
                print(f'{paths.show(path)} @{b.id}: {w}')
        ne += len(errors)
        nw += len(warnings)
    return ne, nw


def merge(parts):
    files = {p: blocks.BlockFile(p) for p in sorted(SCRIPT_DIR.glob('*.txt'))}
    index = {b.id: (f, b) for f in files.values() for b in f.blocks}
    changed = set()
    n = 0
    for part in parts:
        pf = blocks.BlockFile(part)
        for b in pf.blocks:
            if not b.english:
                continue
            if b.id not in index:
                print(f'{part}: unknown block {b.id}')
                continue
            f, tb = index[b.id]
            tb.english = b.english
            changed.add(f)
            n += 1
    for f in changed:
        f.save()
    print(f'merged {n} blocks into {len(changed)} files')


def main(argv=None):
    argv = paths.configure(sys.argv[1:] if argv is None else argv)
    if not argv:
        sys.exit(__doc__)
    cmd, args = argv[0], argv[1:]
    if cmd == 'dump':
        dump('--force' in args)
    elif cmd == 'show':
        data = open(paths.ROM, 'rb').read()
        p = int(args[0], 0)
        cs, q = unpack_codes(data, p)
        print(f'{p:#x}-{q:#x} ({to_cpu(p):06X})')
        print('\n'.join(decode(cs)))
    elif cmd in ('check', 'check-part'):
        files = [Path(a) for a in args if not a.startswith('--')] or sorted(SCRIPT_DIR.glob('*.txt'))
        ne = nw = 0
        for f in files:
            e, w = check_file(f, show_warnings=(cmd == 'check-part' or '--warnings' in args))
            ne, nw = ne + e, nw + w
        print(f'{ne} error(s), {nw} warning(s)')
        sys.exit(1 if ne else 0)
    elif cmd == 'merge':
        merge(args)
    elif cmd == 'stats':
        tot = done = 0
        for f in sorted(SCRIPT_DIR.glob('*.txt')):
            bf = blocks.BlockFile(f)
            d = sum(1 for b in bf.blocks if b.english)
            print(f'{f.name}: {d}/{len(bf.blocks)}')
            tot += len(bf.blocks)
            done += d
        print(f'total {done}/{tot}')
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
