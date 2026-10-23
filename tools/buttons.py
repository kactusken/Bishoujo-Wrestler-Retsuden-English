#!/usr/bin/env python3
"""Button labels drawn as sprites (build step).

  buttons.py sheet OUT.png     the relettered labels (Pillow)

Many buttons (Exhibition: シングル, 選手選択, ロード, 決定, メニューに戻る ...) are a framed box on the
background with the label as 16x16 (or 8x8) sprites on top: white text (colour 1) on transparent,
in packed 4bpp sprite tile blocks. LABELS lists, per block, each label as its sprites in screen
order - (tile, size, x offset) as the game's OAM places them, seen in Mesen. The English is drawn
proportionally (tools/font8.py letters, 1 pixel apart), centred in the label's width, rows 3-12
of the 16-pixel sprites; the block is repacked into its own bank and its loaders
(LDY #lo / LDA #bank) point there.
"""
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import font8  # noqa: E402
import kpack  # noqa: E402
import paths  # noqa: E402
import snes  # noqa: E402

TEXT = 1           # white
TOP = 3            # first row of the letters in a 16-pixel sprite

# block -> (bank for the repacked block, labels: (english, [(tile, 16 or 8, x, y)], what))
BLOCKS = {
    0x9286A3: (0xE8, [
        ('Singles', [(0x00, 16, 0, 0), (0x02, 16, 16, 0), (0x04, 16, 32, 0)], 'シングル'),
        ('Tag', [(0x06, 16, 0, 0), (0x08, 16, 16, 0)], 'タッグ'),
        ('Trios', [(0x0A, 16, 0, 0), (0x0C, 16, 16, 0), (0x0E, 16, 32, 0)], '6人タッグ'),
        ('Roster', [(0x2A, 16, 0, 0), (0x2C, 16, 16, 0), (0x2E, 16, 32, 0)], '選手選択'),
        ('Load', [(0x40, 16, 0, 0), (0x4D, 8, 16, 0), (0x4E, 8, 16, 8)], 'ロード'),
        ('OK', [(0x42, 16, 0, 0), (0x44, 16, 16, 0)], '決定'),
        ('Team', [(0x22, 16, 0, 0), (0x24, 16, 16, 0)], 'チーム (4チーム / 8チーム: the digit is its own sprite)',
         'left'),                # next to the digit, clear of the frame on the right
    ]),
    0x9281DA: (0xF6, [         # move screens' category tabs (Learn, Move Lv., Finisher)
        ('Throw', [(0x00, 16, 0, 0), (0x02, 16, 16, 0)], '投げ技'),
        ('Holds', [(0x04, 16, 0, 0), (0x06, 16, 16, 0)], '関節技'),
        ('Hits', [(0x08, 16, 0, 0), (0x0A, 16, 16, 0)], '打撃技'),
        ('Air', [(0x0C, 16, 0, 0), (0x0E, 16, 16, 0)], '飛び技'),
        ('Power', [(0x20, 16, 0, 0), (0x22, 16, 16, 0)], 'パワー技'),
        ('Dive', [(0x24, 16, 0, 0), (0x26, 16, 16, 0)], '空中技'),
    ]),
    0x9280BE: (0xE9, [         # loaded at sprite tile $C0
        ('Back', [(0x04, 16, 0, 0), (0x06, 16, 16, 0), (0x08, 16, 32, 0), (0x0A, 16, 48, 0)], 'メニューに戻る'),
        ('OK', [(0x00, 16, 0, 0), (0x02, 16, 16, 0)], '決　定 (two sprites, moved side by side: OK_DEF)'),
    ]),
}

# Sprite tiles to clear in a block: the finisher row of the move lists has an EXTRA box under the
# move name (sprite tiles $28/$2A at x 8) and one at the right; the big Japanese glyphs hid the
# left one's lettering, thin English letters do not, so it goes (the right one marks the row).
BLANK = {
    0x9281DA: [0x28, 0x29, 0x2A, 0x2B],
}

# The right EXTRA box (32x8, sprite tiles $2C-$2F at x 88) covers the move level digits at the
# right edge of the list, in the original too. It is redrawn 24 pixels wide (same colours: border
# 4/5, letters 8) and moved left (EXTRA_DEF) so it ends before the digits; names of up to 18
# letters stay clear of it.
REDRAW = {
    0x9281DA: (0x2C, [
        '044444444444444444455550',
        '400000000000000000000005',
        '400888080808880880008005',
        '400800080800800808080805',
        '400880008000800880088805',
        '400800080800800808080805',
        '400888080800800808080805',
        '055555555555555555555550',
    ]),
}


# Screen headers and menu words built from 16x16 character sprites of $91:8493 (sprite tile 0):
# metasprite definitions at $87:DBD3.. (count, then x, y, tile, flags per sprite; flags bit 1 =
# 16x16). Characters are shared between words, so every English word gets glyph positions of
# its own (all positions except TRAINING's) and its definition is pointed at them.
WORD_SETS = [
    {   # $91:8493: headers and menu words (sprite tile 0)
        'block': 0x918493, 'bank': 0xEA, 'headers': True,
        # every button's frame is centred 32 pixels right of its definition's origin (the Japanese
        # words of 3 characters were not centred): words are centred there by pixel, on 16x16 sprites
        'centre': 32,
        'words': [   # (definition file offset, English, Japanese[, 'left'])
            (0x3DBD3, 'Next', '次選手'),
            (0x3DBE0, 'Stats Up', '能力値UP'),
            (0x3DBF1, 'Logic', 'ロジックパターン'),
            (0x3DC02, 'Rivals', '敵データ'),
            (0x3DC13, 'Status', 'ステータス'),
            (0x3DC24, 'Match Card', '対戦カード'),
            (0x3DC35, 'Prev', '前選手'),
            (0x3DC42, 'Learn', '技取得'),
            (0x3DC4F, 'Move Lv.', '技レベル変更'),
            (0x3DC60, 'Exhibition', 'エキシビション'),
            (0x3DC71, 'System', 'システム'),
            (0x3DC97, 'Wrestler', '選手情報'),
            (0x3DCA8, 'Finisher', '必殺技'),
        ],
        # every 16x16 position except TRAINING's ($86-$8E); the block ends at tile $B7
        'positions': [n for row in (0x00, 0x20, 0x40, 0x60, 0x80) for n in range(row, row + 16, 2)
                      if n not in (0x86, 0x88, 0x8A, 0x8C, 0x8E)] + [0xA0, 0xA2, 0xA4, 0xA6],
    },
    {   # $92:D7DB: logic pattern screen - fighting styles and move types
        'block': 0x92D7DB, 'bank': 0xEB, 'headers': False,
        'words': [
            (0x3DCCE, 'Safe', '安定型'),
            (0x3DCDF, 'Fight', '攻撃型'),
            (0x3DCF0, 'Even', '平均型'),
            (0x3DD01, 'Rush', '突撃型'),
            (0x3DD12, 'Throw', '投げ', 'left'),
            (0x3DD1F, 'Holds', '関節', 'left'),
            (0x3DD2C, 'Power', 'パワー', 'left'),
            (0x3DD39, 'Hits', '打撃', 'left'),
            (0x3DD46, 'Air', '飛び', 'left'),
        ],
        # the block ends at tile $5E; $4A-$4E and $5D/$5E hold the slot markers and 型
        'positions': [n for row in (0x00, 0x20) for n in range(row, row + 16, 2)] + [0x40, 0x42, 0x44, 0x46, 0x48],
    },
]
# 決　定 is two sprites 32 pixels apart (metasprite $87:DD53: count, then x, y, tile, flags): they
# move to x 16 and 32 (the same centre) so "OK" reads as one word.
# The EXTRA boxes' metasprite ($87:E44F: count, then x, y, tile, flags): the right box (tiles
# $2C/$2E at x $50/$60 from x 8) moves 6 pixels left so the 24-pixel box ends at x 105, before
# two-digit levels (x 107).
EXTRA_DEF = (0x87E44F, bytes([0x04, 0x00, 0x00, 0x28, 0x02, 0x10, 0x00, 0x2A, 0x02, 0x50, 0x00, 0x2C, 0x02, 0x60, 0x00, 0x2E, 0x02]),
             bytes([0x04, 0x00, 0x00, 0x28, 0x02, 0x10, 0x00, 0x2A, 0x02, 0x4A, 0x00, 0x2C, 0x02, 0x5A, 0x00, 0x2E, 0x02]))
OK_DEF = (0x87DD53, bytes([0x02, 0x08, 0x00, 0x00, 0x02, 0x28, 0x00, 0x02, 0x02]),
          bytes([0x02, 0x10, 0x00, 0x00, 0x02, 0x20, 0x00, 0x02, 0x02]))


# Screens that load only a header copy their word's characters with lists at $8B:E038 (one per
# word of the header set, same order; count, 16-bit offsets tile * 32, then 8x8 count and
# offsets) into sprite tiles $A0+ and place them with relative definitions (tile = 2 * index in
# the list) from the 16-bit table at $8B:E052 (bank $87). Both are rewritten into free space.
COPY_TABLE, COPY_FREE = 0x8BE038, 0x8BE2B7
REL_TABLE, REL_FREE = 0x8BE052, 0x87E5C2


# Framed buttons on a 2bpp background: a packed tilemap (16-bit tile numbers, 4x2) over a packed
# tile set. The frame (outer pixel ring) is kept, the inside redrawn: text colour 1 with a colour 2
# shadow. A button whose tiles are shared with another gets new tiles from `free` and its map is
# repacked into BG_BANK.
BG_BANK = 0xEC
BG_BUTTONS = [
    {   # card list: 手動 / 自動 (tile set $91:D7B7 at BG3 tile $340, maps loaded by $8C:9C56 / 9CAD)
        'tiles': 0x91D7B7, 'tiles_bank': 0xED, 'free': list(range(0x35, 0x40)),   # 64 tiles reach VRAM
        'buttons': [(0x978C75, 4, 2, 'Play', '手動'), (0x978C64, 4, 2, 'Auto', '自動'),
                    # Tournament / League bouts in Play mode (試合中 is unframed: the original's two colours)
                    (0x978C80, 8, 2, 'Skip', '観戦しない'), (0x978C91, 8, 2, 'Watch', '観戦する'),
                    (0x978CB4, 8, 2, 'Playing', '試合中', 'plain')],
        # maps reached through a pointer table (bank set by an LDA #$0097): all of them move together
        'tabled': {'table': 0x8C9E1F, 'bank_site': 0x8C9DE3, 'maps': [0x978C80, 0x978C91]},
    },
]


# Unframed labels in 2bpp background tile sets: (tile set, bank, [(tile rows, English, Japanese)]);
# text colour 1 with a colour 2 shadow. 決定 bars: 決 and 定 are separate 3x2 groups that maps
# place with or without a gap, so each gets one letter.
BG_LABELS = [
    (0x91D477, 0xEE, [([[0x2A, 0x2B, 0x2C], [0x36, 0x37, 0x38]], 'O', '決', 'right'),
                      ([[0x2D, 0x2E, 0x2F], [0x39, 0x3A, 0x3B]], 'K', '定', 'left')]),
]


# Maps of those labels to rearrange: (map, new order of its words). The ring name screen's bar
# ($97:8CEA, 8x2) had 決, two blank cells, 定: now a blank, 決, 定, a blank, so O and K meet.
BG_LABEL_MAPS = {0x91D477: [(0x978CEA, [3, 0, 1, 2, 5, 6, 7, 4, 11, 8, 9, 10, 13, 14, 15, 12])]}


# Big lettering in 4bpp sprite icons: (block, bank, [(tile rows, English, Japanese, colours)]);
# colours: frame (kept on the outer ring), background, fill, outline, shadow. Letters at 2x.
ICONS = [
    (0xA0B731, 0xEF, [([[0xE4, 0xE5, 0xE6, 0xE7], [0xF4, 0xF5, 0xF6, 0xF7], [0xFC, 0xFD, 0xFE, 0xFF]],
                        'GO', '実行 (schedule screen icon)', {'bg': 0, 'fill': 0xD, 'outline': 5, 'shadow': 3})]),
]


def icon_apply(rom, data, r):
    n = 0
    for block, bank, icons in ICONS:
        tiles = bytearray(kpack.unpack(data, r.to_file(block))[0])
        for grid, text, jp, col in icons:
            w, h = len(grid[0]) * 8, len(grid) * 8
            canvas = [[0] * w for _ in range(h)]
            for gy, row in enumerate(grid):           # the original, for the frame
                for gx, t in enumerate(row):
                    for y in range(8):
                        for x in range(8):
                            o, b = t * 32, 7 - x
                            canvas[gy * 8 + y][gx * 8 + x] = ((tiles[o + 2 * y] >> b) & 1) | \
                                (((tiles[o + 2 * y + 1] >> b) & 1) << 1) | (((tiles[o + 16 + 2 * y] >> b) & 1) << 2) | \
                                (((tiles[o + 17 + 2 * y] >> b) & 1) << 3)
            for y in range(1, h - 1):
                for x in range(1, w - 1):
                    canvas[y][x] = col['bg']
            small = render(text, w // 2, 16)
            rows = [i for i, row in enumerate(small) if any(row)]
            top = (h - 2 * (rows[-1] - rows[0] + 1)) // 2 - 2 * rows[0]
            for y, row in enumerate(small):
                for x, v in enumerate(row):
                    if v:
                        for dy in (0, 1):
                            for dx in (0, 1):
                                yy, xx = top + 2 * y + dy, 2 * x + dx
                                if 1 <= yy < h - 1 and 1 <= xx < w - 1:
                                    canvas[yy][xx] = col['fill']
            for key, test in (('outline', lambda yy, xx: any(canvas[yy + a][xx + b] == col['fill']
                                                          for a in (-1, 0, 1) for b in (-1, 0, 1))),
                              ('shadow', lambda yy, xx: canvas[yy - 1][xx - 1] == col['outline'] or
                               canvas[yy - 1][xx] == col['outline'])):
                marks = [(yy, xx) for yy in range(1, h - 1) for xx in range(1, w - 1)
                         if canvas[yy][xx] == col['bg'] and test(yy, xx)]
                for yy, xx in marks:
                    canvas[yy][xx] = col[key]
            for gy, row in enumerate(grid):
                for gx, t in enumerate(row):
                    for y in range(8):
                        for x in range(8):
                            set_pixel(tiles, t, x, y, canvas[gy * 8 + y][gx * 8 + x])
            n += 1
        packed = kpack.pack(bytes(tiles))
        to = r.to_file((bank << 16) | 0x8000)
        rom[to:to + len(packed)] = packed
        if not repoint(rom, data, block, bank):
            raise SystemExit(f'buttons: no loader for ${block:06X}')
    return n


def put_tiles(tiles, grid, canvas):
    for gy, row in enumerate(grid):
        for gx, t in enumerate(row):
            for y in range(8):
                p0 = p1 = 0
                for x in range(8):
                    v = canvas[gy * 8 + y][gx * 8 + x]
                    p0 |= (v & 1) << (7 - x)
                    p1 |= ((v >> 1) & 1) << (7 - x)
                tiles[t * 16 + 2 * y] = p0
                tiles[t * 16 + 2 * y + 1] = p1


def shadow(canvas):
    for y in range(len(canvas) - 1):
        for x in range(len(canvas[0]) - 1):
            if canvas[y][x] == 1 and canvas[y + 1][x + 1] == 0:
                canvas[y + 1][x + 1] = 2


def labels_apply(rom, data, r):
    n = 0
    for block, bank, parts in BG_LABELS:
        tiles = bytearray(kpack.unpack(data, r.to_file(block))[0])
        for grid, text, jp, *align in parts:     # O and K close to each other across the gap
            width = len(grid[0]) * 8
            left = {'left': 1, 'right': width - 2 - sum(glyph(c)[1] + 1 for c in text)}.get(
                align[0] if align else None)
            canvas = render(text, width, len(grid) * 8, left=left)
            shadow(canvas)
            put_tiles(tiles, grid, canvas)
            n += 1
        packed = kpack.pack(bytes(tiles))
        to = r.to_file((bank << 16) | 0x8000)
        rom[to:to + len(packed)] = packed
        if not repoint(rom, data, block, bank):
            raise SystemExit(f'buttons: no loader for ${block:06X}')
        pos = to + len(packed)
        for mp, order in BG_LABEL_MAPS.get(block, []):     # maps rearranged (after the tiles)
            words, _ = kpack.unpack(data, r.to_file(mp))
            nums = [words[2 * i] | words[2 * i + 1] << 8 for i in range(len(order))]
            pm = kpack.pack(b''.join(nums[k].to_bytes(2, 'little') for k in order))
            rom[pos:pos + len(pm)] = pm
            a = r.to_cpu(pos)
            if not repoint(rom, data, mp, a >> 16, a & 0xFFFF):
                raise SystemExit(f'buttons: no loader for ${mp:06X}')
            pos += len(pm)
    return n


def bg_apply(rom, data, r):
    n = 0
    mpos = r.to_file((BG_BANK << 16) | 0x8000)
    for spec in BG_BUTTONS:
        tiles, _ = kpack.unpack(data, r.to_file(spec['tiles']))
        tiles = bytearray(tiles)
        free = list(spec['free'])
        owner = {}
        final = {}
        for mp, w, h, text, jp, *style in spec['buttons']:
            words, _ = kpack.unpack(data, r.to_file(mp))
            nums = [words[2 * i] | words[2 * i + 1] << 8 for i in range(w * h)]
            canvas = [[0] * (w * 8) for _ in range(h * 8)]
            for i, t in enumerate(nums):                 # the original picture, for the frame
                for y in range(8):
                    for x in range(8):
                        b = 7 - x
                        canvas[(i // w) * 8 + y][(i % w) * 8 + x] = ((tiles[t * 16 + 2 * y] >> b) & 1) | \
                            (((tiles[t * 16 + 2 * y + 1] >> b) & 1) << 1)
            if style == ['plain']:                       # no frame: background and lettering colours
                counts = collections.Counter(v for row in canvas for v in row).most_common()
                bg, fg = counts[0][0], counts[1][0]
                txt = render(text, w * 8, h * 8)
                canvas = [[fg if v else bg for v in row] for row in txt]
            else:
                bg = fg = None
            for y in range(1, h * 8 - 1) if bg is None else ():
                for x in range(1, w * 8 - 1):
                    canvas[y][x] = 0
            txt = render(text, w * 8 - 4, h * 8) if bg is None else [[]]
            for y in range(h * 8) if bg is None else ():
                for x in range(w * 8 - 4):
                    if txt[y][x]:
                        canvas[y][x + 2] = 1
            for y in range(1, h * 8 - 2) if bg is None else ():   # shadow: right and down, in the frame
                for x in range(1, w * 8 - 2):
                    if canvas[y][x] == 1 and canvas[y + 1][x + 1] == 0:
                        canvas[y + 1][x + 1] = 2
            new = []
            for i, t in enumerate(nums):
                cell = bytearray(16)
                for y in range(8):
                    p0 = p1 = 0
                    for x in range(8):
                        v = canvas[(i // w) * 8 + y][(i % w) * 8 + x]
                        p0 |= (v & 1) << (7 - x)
                        p1 |= ((v >> 1) & 1) << (7 - x)
                    cell[2 * y], cell[2 * y + 1] = p0, p1
                if t in owner and owner[t] != mp and tiles[t * 16:t * 16 + 16] != cell:
                    if not free:                         # shared with an earlier button, different now
                        raise SystemExit(f'buttons: no free tiles in ${spec["tiles"]:06X}')
                    t = free.pop(0)
                owner.setdefault(t, mp)
                new.append(t)
                tiles[t * 16:t * 16 + 16] = cell
            tabled = spec.get('tabled', {})
            if mp in tabled.get('maps', []):
                final[mp] = new
            elif new != nums:
                packed = kpack.pack(b''.join(t.to_bytes(2, 'little') for t in new))
                rom[mpos:mpos + len(packed)] = packed
                addr = r.to_cpu(mpos)
                if not repoint(rom, data, mp, addr >> 16, addr & 0xFFFF):
                    raise SystemExit(f'buttons: no loader for ${mp:06X}')
                mpos += len(packed)
            n += 1
        if final:                                        # the table's maps, all in BG_BANK
            tab = spec['tabled']
            bs = r.to_file(tab['bank_site'])
            if data[bs:bs + 3] != b'\xa9\x97\x00':
                raise SystemExit('buttons: unexpected code at the map table\'s bank')
            rom[bs + 1] = BG_BANK
            for k, mp in enumerate(tab['maps']):
                packed = kpack.pack(b''.join(t.to_bytes(2, 'little') for t in final[mp]))
                rom[mpos:mpos + len(packed)] = packed
                to = r.to_file(tab['table']) + 2 * k
                if data[to] | data[to + 1] << 8 != mp & 0xFFFF:
                    raise SystemExit(f'buttons: the map table does not hold ${mp:06X}')
                rom[to:to + 2] = (r.to_cpu(mpos) & 0xFFFF).to_bytes(2, 'little')
                mpos += len(packed)
        packed = kpack.pack(bytes(tiles))
        to = r.to_file((spec['tiles_bank'] << 16) | 0x8000)
        rom[to:to + len(packed)] = packed
        if not repoint(rom, data, spec['tiles'], spec['tiles_bank']):
            raise SystemExit(f'buttons: no loader for ${spec["tiles"]:06X}')
    return n


def place_word(data, tiles, at, text, jp, alloc, blank, align='centre', centre=None):
    """Draw `text` over the word's sprites; returns the definition's entries (x, y, tile, flags)."""
    n = data[at]
    ents = [list(data[at + 1 + 4 * k:at + 5 + 4 * k]) for k in range(n)]
    size = [16 if e[3] & 2 else 8 for e in ents]
    x0, y0 = min(e[0] for e in ents), min(e[1] for e in ents)
    w = sum(glyph(c)[1] for c in text) + len(text) - 1 + (2 if align == 'left' else 0)
    if centre is not None:                      # k 16x16 sprites from x = centre - 8k, the rest blank
        k = -(-w // 16)
        if k > n:
            raise SystemExit(f'buttons: "{text}" needs {k} sprites, {jp} has {n}')
        rows = render(text, k * 16)
        for i, e in enumerate(ents):
            if i < k:
                e[0], e[1], e[3] = centre - 8 * k + 16 * i, y0, e[3] | 2
                e[2] = alloc(16, jp)
                draw(tiles, [row[16 * i:16 * i + 16] for row in rows], [(e[2], 16, 0, 0)])
            else:
                e[2] = blank
        return ents
    xs = sorted({e[0] for e, sz in zip(ents, size) if sz == 16 and e[1] == y0})
    if -(-w // 16) <= len(xs):                  # fits the 16x16 sprites: centred on whole sprites
        k = -(-w // 16)
        if k > len(xs):
            raise SystemExit(f'buttons: "{text}" needs {k} sprites, {jp} has {len(xs)}')
        first = 0 if align == 'left' else (len(xs) - k) // 2
        cx = xs[first] - x0
        rows = render(text, k * 16, left=2 if align == 'left' else None)
        canvas = [[0] * cx + row + [0] * 256 for row in rows]
    else:                                       # centred by pixel over all sprites
        width = max(e[0] + sz for e, sz in zip(ents, size)) - x0
        canvas = [row + [0] * 16 for row in render(text, width)]
    canvas += [[0] * len(canvas[0]) for _ in range(16)]
    for e, sz in zip(ents, size):
        sub = [row[e[0] - x0:e[0] - x0 + sz] for row in canvas[e[1] - y0:e[1] - y0 + sz]]
        if not any(any(row) for row in sub):
            e[2] = blank
            continue
        e[2] = alloc(sz, jp)
        draw(tiles, sub, [(e[2], sz, 0, 0)])
    return ents


def words_apply(rom, data, r):
    n = 0
    for ws in WORD_SETS:
        tiles, _ = kpack.unpack(data, r.to_file(ws['block']))
        tiles = bytearray(tiles)
        free = list(ws['positions'])
        singles = []
        blank = free.pop(0)
        for t in (blank, blank + 1, blank + 16, blank + 17):
            tiles[t * 32:t * 32 + 32] = bytes(32)

        def alloc(sz, jp):
            if sz == 8:
                if not singles:
                    if not free:
                        raise SystemExit(f'buttons: out of tiles in ${ws["block"]:06X} ({jp})')
                    p = free.pop()
                    singles.extend([p, p + 1, p + 16, p + 17])
                return singles.pop(0)
            if not free:
                raise SystemExit(f'buttons: out of glyph positions in ${ws["block"]:06X} ({jp})')
            return free.pop(0)

        lists = []
        for at, text, jp, *align in ws['words']:
            ents = place_word(data, tiles, at, text, jp, alloc, blank, *(align or ['centre']),
                              centre=ws.get('centre'))
            for i, e in enumerate(ents):
                rom[at + 1 + 4 * i:at + 5 + 4 * i] = bytes(e)
            lists.append(ents)
            n += 1
        if ws['headers']:
            free_at = r.to_file(COPY_FREE)
            table = r.to_file(COPY_TABLE)
            relfree = r.to_file(REL_FREE)
            rtab = r.to_file(REL_TABLE)
            for w, ents in enumerate(lists):
                big = []
                for e in ents:
                    if e[2] not in big:      # 8x8 pieces point at the blank glyph too
                        big.append(e[2])
                rel = bytes([len(ents)]) + b''.join(bytes([e[0], e[1], 2 * big.index(e[2]), e[3]]) for e in ents)
                rom[relfree:relfree + len(rel)] = rel
                rom[rtab + 2 * w:rtab + 2 * w + 2] = (r.to_cpu(relfree) & 0xFFFF).to_bytes(2, 'little')
                relfree += len(rel)
                body = bytes([len(big)]) + b''.join((t * 32).to_bytes(2, 'little') for t in big) + b'\x00'
                rom[free_at:free_at + len(body)] = body
                rom[table + 2 * w:table + 2 * w + 2] = (r.to_cpu(free_at) & 0xFFFF).to_bytes(2, 'little')
                free_at += len(body)
        packed = kpack.pack(bytes(tiles))
        to = r.to_file((ws['bank'] << 16) | 0x8000)
        rom[to:to + len(packed)] = packed
        if not repoint(rom, data, ws['block'], ws['bank']):
            raise SystemExit(f'buttons: no loader for ${ws["block"]:06X}')
    return n


def glyph(ch):
    """(rows of 16 bytes, width in pixels) of a font8 letter."""
    g = font8.glyph_bytes()[font8.CODES[ch] * 16:font8.CODES[ch] * 16 + 16]
    w = 0
    for b in g:
        for x in range(8):
            if b & (0x80 >> x):
                w = max(w, x + 1)
    return g, (w or 3)


def render(text, width, height=16, left=None):
    """A width x height canvas of colour indices with the text centred (or from x = left)."""
    letters = [glyph(c) for c in text]
    total = sum(w for _, w in letters) + max(0, len(letters) - 1)
    if total > width:
        raise SystemExit(f'buttons: "{text}" is {total} pixels, the label holds {width}')
    canvas = [[0] * width for _ in range(height)]
    x = (width - total) // 2 if left is None else left
    if x + total > width:
        raise SystemExit(f'buttons: "{text}" is {total} pixels from {x}, the label holds {width}')
    for g, w in letters:
        for row in range(16):
            y = row - 2 + TOP              # font rows 2.. -> label rows TOP..
            if not 0 <= y < height:
                continue
            for px in range(w):
                if g[row] & (0x80 >> px):
                    canvas[y][x + px] = TEXT
        x += w + 1
    return canvas


def set_pixel(tiles, t, x, y, v):
    o = t * 32
    b = 7 - x
    for plane, at in enumerate((o + 2 * y, o + 2 * y + 1, o + 16 + 2 * y, o + 17 + 2 * y)):
        tiles[at] = (tiles[at] & ~(1 << b)) | (((v >> plane) & 1) << b)


def sprite_tiles(tile, size):
    """[(tile, dx, dy)] of the 8x8 tiles of a sprite (16x16: n, n+1, n+16, n+17)."""
    if size == 8:
        return [(tile, 0, 0)]
    return [(tile, 0, 0), (tile + 1, 8, 0), (tile + 16, 0, 8), (tile + 17, 8, 8)]


def repoint(rom, data, block, bank, addr=0x8000):
    """Point the loaders of a packed block at $bank:addr: LDY #lo / LDA #bank (8-bit A) and
    LDA #lo / STA $38 / LDA #bank / STA $3A (16-bit A). Returns how many were found."""
    lo, hi, b = block & 0xFF, (block >> 8) & 0xFF, block >> 16
    found = 0
    for pat, at_lo, at_bank in ((bytes([0xA0, lo, hi, 0xA9, b]), 1, 4),
                                (bytes([0xA9, lo, hi, 0x85, 0x38, 0xA9, b, 0x00, 0x85, 0x3A]), 1, 6)):
        i = data.find(pat)
        while i != -1:
            rom[i + at_lo:i + at_lo + 2] = addr.to_bytes(2, 'little')
            rom[i + at_bank] = bank
            found += 1
            i = data.find(pat, i + 1)
    return found


def draw(tiles, canvas, sprites):
    for tile, size, sx, sy in sprites:
        for t, dx, dy in sprite_tiles(tile, size):
            for y in range(8):
                for x in range(8):
                    cy = sy + dy + y
                    v = canvas[cy][sx + dx + x] if cy < 16 else 0
                    set_pixel(tiles, t, x, y, v)


def apply(rom):
    r = snes.Rom(rom)
    data = bytes(rom)
    n = 0
    for a, old, new in (OK_DEF, EXTRA_DEF):
        o = r.to_file(a)
        if data[o:o + len(old)] != old:
            raise SystemExit(f'buttons: unexpected data at the sprite definition ${a:06X}')
        rom[o:o + len(new)] = new
    for block, (bank, labels) in BLOCKS.items():
        tiles, _ = kpack.unpack(data, r.to_file(block))
        tiles = bytearray(tiles)
        for text, sprites, what, *opt in labels:
            if isinstance(text, list):     # one part per sprite (labels with gaps between sprites)
                parts = [(render(t, size), [(tile, size, 0, sy)]) for t, (tile, size, _, sy) in zip(text, sprites)]
            else:
                parts = [(render(text, max(x + size for _, size, x, _ in sprites),
                                 left=1 if opt == ['left'] else None), sprites)]
            for canvas, group in parts:
                draw(tiles, canvas, group)
            n += 1
        for t in BLANK.get(block, []):
            tiles[t * 32:t * 32 + 32] = bytes(32)
        if block in REDRAW:
            first, rows = REDRAW[block]
            for t in range(first, first + 4):
                tiles[t * 32:t * 32 + 32] = bytes(32)
            for y, row in enumerate(rows):
                for x, ch in enumerate(row):
                    set_pixel(tiles, first + x // 8, x % 8, y, int(ch, 16))
        packed = kpack.pack(bytes(tiles))
        to = r.to_file((bank << 16) | 0x8000)
        rom[to:to + len(packed)] = packed
        found = repoint(rom, data, block, bank)
        if not found:
            raise SystemExit(f'buttons: no loader for ${block:06X}')
    return n + words_apply(rom, data, r) + bg_apply(rom, data, r) + labels_apply(rom, data, r) + icon_apply(rom, data, r)


def main(argv=None):
    argv = paths.configure(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ['sheet'] and len(argv) == 2:
        from PIL import Image
        rows = [lab for _, labels in BLOCKS.values() for lab in labels]
        im = Image.new('RGB', (80, 18 * len(rows)), (80, 20, 80))
        for i, (text, sprites, _) in enumerate(rows):
            width = max(x + size for _, size, x, _ in sprites)
            c = render(text if isinstance(text, str) else ' '.join(text), width)
            for y in range(16):
                for x in range(width):
                    if c[y][x]:
                        im.putpixel((x, i * 18 + y), (255, 255, 255))
        im.resize((im.width * 4, im.height * 4), Image.NEAREST).save(argv[1])
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
