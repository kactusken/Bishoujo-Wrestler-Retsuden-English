# Technical notes - Bishoujo Wrestler Retsuden: Blizzard Yuki Rannyuu!!

**Conventions:** numbers in hex with `0x`; addresses are RAM addresses unless marked as file
offsets; `u16`/`u32` little-endian unless marked BE. Findings are marked *verified in game* or
*from the code*.

## Contents
- [Image](#image) · [ROM layout](#rom-layout) · [Executable and memory](#executable-and-memory)
- [Archives and compression](#archives-and-compression) · [Text](#text)
- [English text](#english-text-this-projects-code-toolshookspy) ·
  [Schedule help texts](#schedule-screen-help-texts-toolshelptextpy) ·
  [Glyph strings](#glyph-strings-menus-headers) · [Buttons and headers](#buttons-and-headers-toolsbuttonspy)
- [Hi-res screens](#hi-res-screens-toolshirespy-toolsmovespy-toolsrecfontpy) ·
  [Schedule art](#schedule-screen-art-toolsschedartpy) · [Card list header](#card-list-header) ·
  [Commentary and quotes](#match-commentary-and-winner-quotes-toolstickerpy) ·
  [Card list results](#card-list-results-and-bout-buttons-toolsresultspy-toolsbuttonspy)
- [Layout fixes](#layout-fixes-toolslayoutpy) · [Banks](#banks-used-by-this-project) ·
  [Images](#images) · [Open questions](#open-questions)

Champion Road's routes and match rules are in [CHAMPION_ROAD.md](CHAMPION_ROAD.md); codes and
unused content in [HIDDEN_CONTENT.md](HIDDEN_CONTENT.md).

## Image
`Bishoujo Wrestler Retsuden - Blizzard Yuki Rannyuu!! (J).smc`, 2621440 bytes (headerless), CRC32
`f4d20413`, SHA-1 `de5fc2caae6803bfcb2eaf831a346b0e422a4e77`.

## ROM layout
| | |
|---|---|
| Title | `ﾋﾞｼｮｳｼﾞｮﾚｽﾗｰﾚﾂﾃﾞﾝ` |
| Map | LoROM FastROM (`$30`), header at `0x7fc0` |
| Size | 0x280000 bytes (20 Mbit), 80 banks of 32 KB |
| ROM | $80:8000 - $CF:FFFF |
| Cart | type `$02`, SRAM 8 KB |
| Reset | $00:8000 |
| Checksum | `0xa9c3` (fixed by tools/disc.py on every build) |

Runs of `$00`/`$FF` of 1 KB or more (free space candidates - verify nothing reads them):

| Offset | CPU | Bytes | Fill |
|---|---|---|---|
| `0x00666f` | $80:E66F | 0x991 | `$ff` |
| `0x007002` | $80:F002 | 0xfae | `$ff` |
| `0x00f818` | $81:F818 | 0x7e8 | `$ff` |
| `0x02fbd2` | $85:FBD2 | 0x42e | `$ff` |
| `0x036062` | $86:E062 | 0x1f9e | `$ff` |
| `0x03e5c2` | $87:E5C2 | 0x1a3e | `$ff` |
| `0x0473ca` | $88:F3CA | 0xc36 | `$ff` |
| `0x04f16b` | $89:F16B | 0xe95 | `$ff` |
| `0x05e2b7` | $8B:E2B7 | 0x1d49 | `$ff` |
| `0x06ee6f` | $8D:EE6F | 0x1191 | `$ff` |
| `0x07723a` | $8E:F23A | 0xdc6 | `$ff` |
| `0x07ec99` | $8F:EC99 | 0x1367 | `$ff` |
| `0x09738d` | $92:F38D | 0xc73 | `$ff` |
| `0x09bd0c` | $93:BD0C | 0x42f4 | `$ff` |
| `0x0a58b1` | $94:D8B1 | 0x274f | `$ff` |
| `0x0af68e` | $95:F68E | 0x972 | `$ff` |
| `0x0b3fcf` | $96:BFCF | 0x4031 | `$ff` |
| `0x0b9b2e` | $97:9B2E | 0x4d2 | `$ff` |
| `0x0bf092` | $97:F092 | 0xf6e | `$ff` |
| `0x0c76f0` | $98:F6F0 | 0x610 | `$00` |
| `0x0ce27f` | $99:E27F | 0x1d81 | `$ff` |
| `0x0d4c5e` | $9A:CC5E | 0x33a2 | `$ff` |
| `0x0defdb` | $9B:EFDB | 0x1025 | `$ff` |
| `0x0f34b6` | $9E:B4B6 | 0x662 | `$00` |
| `0x106662` | $A0:E662 | 0x199e | `$ff` |
| `0x1cf5e8` | $B9:F5E8 | 0xa18 | `$ff` |
| `0x1d73e1` | $BA:F3E1 | 0xc1f | `$ff` |
| `0x1df7f4` | $BB:F7F4 | 0x80c | `$ff` |
| `0x1e77cc` | $BC:F7CC | 0x834 | `$ff` |
| `0x21d1bf` | $C3:D1BF | 0x2e41 | `$ff` |
| `0x237b48` | $C6:FB48 | 0x4b8 | `$ff` |
| `0x24f908` | $C9:F908 | 0x6f8 | `$ff` |
| `0x2537c3` | $CA:B7C3 | 0x1c83d | `$ff` |
| `0x277890` | $CE:F890 | 0x770 | `$ff` |
| `0x27cf38` | $CF:CF38 | 0x30c8 | `$ff` |

## Executable and memory
- Text and windows run as cooperative tasks: a routine stores its continuation address in DP `$03`
  and returns (`RTL`); `JML $80:89FF` yields until the next frame. *(from the code)*
- Event scripts: bytecode in banks $88 and $93, interpreter `$8D:C452` (pointer at `$7E:F221`,
  opcode table `$8D:C60F`, indexed by the opcode byte; opcodes are even). `3C ptr24 slot` shows a
  dialogue string; slot 0-9 picks the scene character (`$7E:F22E` + slot) whose face is drawn at
  the left of the window (`$8C:ADD2` -> `$7E:F349`), 99 shows none. *(verified with Mesen traces)*
- Dialogue window, per page: unpack the string (`$8C:B450`) into `$7E:D342` (up to 256 codes; the
  English build moves it, see [Layout fixes](#layout-fixes-toolslayoutpy));
  collect the page's glyph codes into `$7E:F1A1` (`$8C:B42C`, 16-bit words); draw them as 16x16
  glyphs into `$7F:C000` (`$8C:A924`: 8 glyphs per 0x200-byte row of tiles, top halves first) and
  DMA 4 KB to VRAM `$5000` (BG3 tiles $200-$2FF); then code by code write 2x2 tilemap entries at the
  cursor `$16FE` (`$80:BC43`, tile table `$89:8000`, cursor += 2), one code per frame (typewriter).
  `$7E:D33E` counts glyphs ($80 + n), `$7E:D340` is the line index. *(verified)*
- Event opcodes (tools/events.py `dis`): lengths and meanings from the handlers. `00` goto16,
  `02 v cmp x addr16` if (cmp low nibble: != == <= >= < >; bit 4: x is a variable), `04` call24,
  `06` ret, `08`-`1A` set/add/sub/and/or v (by variable or value), `1C` end, `46` jump24, `3C` say,
  `5A` music, `50` wait; one-byte "run" opcodes start a screen task and resume when it ends.
  Variables vNN: bytes at `$7E:F225` + NN. *(from the code; verified with Mesen traces)*
- World Circuit (`$93:B6AF`): briefing `$88:F37D`, team choice (`74`, `$8B:9CE5`), 13 stops of
  `5E n` stop card, `$93:B886` belt + rival's taunt (by v17), `22` Training (`$8B:B174`: the team
  list is the hub, a wrestler's 10-button menu returns to it with OK; the list's top button ends
  Training), `60` lineup + matches (`$8E:94D0`), `62` tally (`$8C:8ADD`; v11 = 0 when the main
  singles and one more match are won), `$93:BACE` remark. v11 = 0 goes to the next stop, else back
  to Training for the same stop: **no game over**. After stop 13: president `$88:F3A6`, records
  `72` (`$8D:EB01`), staff roll `70` (`$84:FB15`, original English credits; "ENDING NO." = v3F, set
  only by Champion Road, `$88:D79E`.., endings 1-9; the circuit is always 0), then the circuit starts
  again. `tools/events.py wctest` makes a test image that wins every stop. *(verified in game)*
- Champion Road (`$88:8000`, `tools/events.py listing 888000 OUT`): heroine v09 (1 Yukiko, 2 Haruka,
  3 Kazuko, 4 Kayo, 5 Yuki), faction v13/v14 (Regulars, Rebels, World Joshi, Freelance; Yukiko only the
  first two) sets the route v39 (1, 2, 21, 30). **v12 is the heroine's rating / 10** (`$8D:C48B`), so
  "series until v12 >= N" gates the story on rating (440-850), not time. op48 is a 2-option choice (v10),
  op48 03 a 3-option one. v20-v32 are the belt holders. The IWWF Heavyweight win (`$88:D6EE`) picks the
  ending by v39 (1/119 -> 1, 2 -> 2, 21 -> 3, 101 -> 4, 113 -> 5, 118 -> 6, 122 -> 7, 150 -> 8, other -> 1);
  `$88:90C8` gives ending 9 for v09 = 5 with v39 = 98. *(from the script; rating gate verified in RAM;
  all nine endings reached in game with the `tools/events.py crtest` test image)*
- Weekly training (`$84:DFD6`, 21 day types): stat exp += `$83:F198`[rating tier][grade], 256 exp = +1
  (cap 16; atk/def cap 31, a type's atk+def at most 32); grade from rand(0-63) + fatigue (record +$AE,
  +8 per session, Play -70/-50/-30) + 50 when a drill's atk+def >= 2 x its base stat. Rating (`$8A:8000`)
  = 4 x (atk/def + base stats + move bonus 0/5/10/14/17/19/21 per category + finisher byte).
- **`$7E:F1A1` holds 64 words; the event pointer `$7E:F221` follows it.** A page of more than 64
  codes overwrites the event pointer and the scene jumps elsewhere (seen with English pages before
  the byte list hook). *(verified)*
- Speaker codes `$3E3`-`$3E8` place the 4 pre-drawn name glyphs of slot `$C0 + 4n`, `$3EB`-`$3F0`
  the names in `$7E:D242`, `$3F1` the player's ring name (8 glyphs, `$7E:D25A`). Glyph slots
  `$C0`-`$FF` are reserved for these. *(from the code)*
- A face covers columns 0-5 of the window; the original text always starts at column 6.
  *(verified in game)*

## Archives and compression
- Decompressor `$80:D907` (tools/kpack.py): method byte, u16 length, data. Source `[$38]`,
  destination `$30` in the data bank. Methods (even numbers, jump table `$80:D917`): `$00` raw words,
  `$02` byte runs, `$04` byte pairs (2 bits per item: count present, second byte = first), `$06`
  word runs, `$08` word pairs, `$0A`/`$0C` byte/word groups where a set bit reads a new value and a
  clear bit repeats the last one (0 at the start of each group), `$0E` a tree code (not decoded),
  `$10` incrementing runs, `$12` runs with a signed step. Method `$04` verified byte-exact against
  WRAM; `$0C` verified by the English names font. *(verified)*

## Text
- **Dialogue font**: 16x16 1bpp at `$98:8000` (file 0xC0000), codes `$000`-`$3B6`, glyph c at
  `(c & ~7) * 32 + (c & 7) * 16` (top-left 8 bytes, top-right 8, bottom halves +0x80). Order: JIS X
  0208 (symbols, digits, Latin, hiragana, katakana, then the kanji the game uses in JIS order).
  Table: `translation/tables/font98.tsv` (tools/fontid.py aligned the glyphs with the JIS list;
  22 fixed by eye, among them 組 果 簡 絡 画 that the first pass read as neighbours). *(verified)*
- **Script encoding**: 10-bit codes packed 4 per 5 bytes (bytes 0-3 the low bits, byte 4 the high
  2 bits of each, first code in bits 7-6); a string ends with the group holding `$3FF`. Controls:
  `$3E0` page start, `$3E1` wait for a button, `$3FE` line break, `$3E3`-`$3E8` / `$3EB`-`$3F0` /
  `$3F1` names, `$3E2` `$3E9` `$3EA` rare. 3413 strings in banks $94-$96, $99-$9B, $CF; 3140 are
  referenced by event `$3C` opcodes, 2894 of them from reachable script; the other 519 are unused
  (HIDDEN_CONTENT.md). *(verified)*
- **Profiles**: 63-entry table of 24-bit pointers at `$8C:B9C1` (60 strings in $CF, no page codes),
  drawn by the same renderer (`$8C:B857` collect, `$8C:B86A` draw, `$8C:B942` map). *(verified)*
- **Names font**: 16x16 1bpp, same layout, packed at `$90:8000`, 8-bit codes, loaded by ~30 screens
  (`LDA #$0090 / STA $32` + `LDA #$8000 / STA $30`). Name records: 8 codes + `$FF` (real names
  0x7de0a, ring names 0x7e04a and 0x7e281) and 4 codes + `$FF` (short names 0x7e3a6, ring name
  parts 0x7e4e1). The kana parts give the readings: 新咲 しんざき, 羽田 はだ. *(verified)*

## English text (this project's code, tools/hooks.py)
- ROM expanded to 32 Mbit. `$D0:8000` the 8x16 English font (tools/font8.py), `$D0:9000` code,
  `$D1`-`$DF` reserved for the English script (tools/script.py insert; it fills `$D1`-`$DA`),
  `$E0:8000` the English names font.
- Collect8 (`$8C:AD87`, `$8C:B857`): page codes as bytes, at most 120. Render8 (`$8C:ADA2`,
  `$8C:B86A`): one 8x16 cell per letter, cell k at tile `$200 + k + (k & $70)` (bottom +`$10`).
  Tile8 (`$8C:AF17`, `$8C:B942`): map one cell, cursor + 1. Window clears and line starts moved
  from column 6 to column 2 (26 -> 30 columns).
- Line layout (tools/script.py layout): narration strings (every `$3C` reference has slot 99, no
  speaker code, every page waits) use columns 2-31 (30 letters); other strings are indented 4 cells to column 6 (26 letters) because of
  the face or a choice menu's cursor. Long lines are wrapped and full pages split by the encoder.
- Names: two 8-pixel letters per names-font glyph, in capitals. Most screens render names from the
  whole font (`$8C:A89F`, codes up to `$FE`), but the Exhibition / League / Tournament screens copy
  only the first `$C0` glyphs to VRAM (`$8E:A5AE`), so every name they can show must use codes
  1-`$BF`: see [Layout fixes](#layout-fixes-toolslayoutpy). 254 records, 191 distinct pairs.
  tools/names.py.

## Schedule screen help texts (tools/helptext.py)
- Messages: 8-bit glyph indices, `$FE` line break, `$FF` end, padded with `$00` to 11 glyphs per
  line; 28 reached through the 16-bit table `$83:F01A` (`$84:EA8C`), two more only by address
  (`LDY #$EF2F` / `#$EF48`, `LDA #$0083`, `STY $30`, `STA $32`, `JSR $EA9B`). Drawn by `$84:EA9B`:
  line 1 at column 8, line 2 at 9; each glyph via `$80:BC43` (cursor + 2). The game redraws only as
  many cells as a message has. *(verified)*
- Glyph n = BG3 tiles `(n & 7) * 2 + (n >> 3) * 32` (+1, +16, +17) of the screen's tile set, packed
  at `$B4:CA38` (entry 2 of the 24-bit table `$89:8200`), unpacked to `$7F:C000`, DMA to VRAM
  `$4000`. *(verified)*
- English: TileH replaces the JSL at `$84:EAC4`: code b = tile `b + (b & $F0)` (one half of a
  glyph slot), cursor + 1; letters drawn into the halves of the slots the Japanese used; messages
  in `$E1`, tile set repacked into `$E2`, lines padded to full width.
- Other loads of the same messages, all pointed at `$E1` too: `LDY #addr / LDA #$0083 / BRA` to a
  shared `STY $30 / STA $32` (`$84:DD84`.., the title redrawn on return from the Practice Match,
  Move Difficulty and Finisher screens), and `LDA $83:F036,X` / `LDA $83:F04A,X` (`$84:E6A0`,
  `$84:E6DD`, `$84:E8C8`: the drill type picker, opened by A or Y on Offense / Defense Drills, and
  "Choose N more"). Missed at first, they drew Japanese glyph indices over the English letter
  tiles. *(verified in game)*

## Glyph strings (menus, headers)
- Most menu and window texts are 8-bit glyph strings (`$FF` end) over a per-screen glyph set, drawn
  by `$8C:A9E7` / `$8C:AA01` / `$8C:AA1B` / `$8C:AA4C` (pointer `[$38]`, index + `$3C` -> `$80:BC43`,
  2x2 tiles from the `$89:8000` table). Over 400 call sites. Examples (bank $8A): `$8A:970F`
  主人公を決定して下さい, `$8A:9706` Ｘボタン 能力値, `$8A:971C` 新女 正規軍, `$8A:B0BE`
  リングネームを選択して下さい. Lists of slot numbers (`$8A:9482`: b0 b1 ... b7) place pre-drawn
  names. Select screens' glyph set: `$B4:A461` (2bpp). *(verified with traces)*

## Buttons and headers (tools/buttons.py)
- Sprite labels: white text (colour 1) on transparent 16x16/8x8 sprites over a framed box on the
  background. `$92:86A3` (sprite tile 0): シングル タッグ 6人タッグ 選手選択 ロード 決定 (Exhibition);
  `$92:80BE` (tile $C0): 決　定, メニューに戻る. *(verified)*
- Words built from shared 16x16 character sprites, with metasprite definitions (count, then x, y,
  tile, flags; flags bit 1 = 16x16): `$91:8493` headers/menu words, definitions `$87:DBD3`-`$87:DCA8`;
  screens that load only a header copy its characters with lists from `$8B:E038` (count, 16-bit
  offsets tile * 32, 8x8 count) and place them with relative definitions from `$8B:E052` (bank $87,
  tile = 2 * index in the list); `$92:D7DB` logic screen styles and move types, `$87:DCCE`-`$87:DD46`.
  A menu button's frame is centred 32 pixels right of its definition's origin (the Japanese
  3-character words sit 8 pixels left of it); the English rewrites x and size of each entry and
  centres the word there by pixel on 16x16 sprites.
- Background buttons: 自動 / 手動 are 4x2 framed tiles of `$91:D7B7` (BG3 tile $340) placed by packed
  maps `$97:8C64` / `$97:8C75` through a row queue at `$7E:4B60` (`$80:AF10` adds base and attributes);
  決定 bars: `$91:D477` tiles $2A-$2F/$36-$3B, map `$97:8CEA` (others in screen maps); O is drawn
  at the right of 決's tiles, K at the left of 定's, and `$97:8CEA` is rearranged so they meet.
- The 決　定 sprite button (info menu, World Circuit, ...) is metasprite `$87:DD53`: its two
  sprites moved from x 8 / 40 to 16 / 32 so "OK" is one word. *(verified)*
- Schedule screen activity icons: `$A0:B731` (second sprite name table, block tile $E0 = sprite
  tile $100); 実行 = tiles $E4-$E7, $F4-$F7, $FC-$FF (32x24; colours b frame, d fill, 5 outline,
  3 shadow). *(verified)*

## Hi-res screens (tools/hires.py, tools/moves.py, tools/recfont.py)
- Status, logic, info menu, League, World Circuit and the move screens are mode 5 with 16x16 BG
  tiles: one map entry is 16 hi-res pixels (8 normal) wide. `$8C:AA1B` draws one glyph slot per
  code (index + `$3C`); value strings are copied first from 16-bit pointer tables into
  `$7E:F1A1` (word loops, `CPX #6`). *(verified)*
- Fonts: status labels `$91:EFD8` (80 slots, `$8A:B11F`); logic/info box share `$91:DC15` with the
  save screens; stat-up shares `$92:9416`; League `$92:E8D8` (24 slots); World Circuit `$92:DE21`
  (64 slots); World Circuit rivals `$92:EC3C` (`$30` slots; names from `$40`, finishers from `$70`;
  strings `$8B:D578`-`$8B:D5B7`, tables `$8B:D523` assist, `$8B:D529` logic, `$8B:D4F9` best of
  the 10 attack/defense values; `$8B:D405` +7 cells before the type, now +1); move screens
  `$92:8B38` (48 slots, one loader `$8B:D7AB`). English: one font8 letter, doubled in width,
  per slot; strings in `$F0`. For a shared set, tools/glyphstr.py leaves the slots of the
  converted hi-res strings free (`LEFT`) and tools/hires.py draws whole-slot letters there.
  A label moves with `col=N` in its text file; a string drawn from several sites (the Stats Up
  headers over both columns) moves by the same number of cells at each.
- Move names: 105 records of 12 codes at file 0x7e691 over the move font `$90:9962` (1bpp 16x16,
  names layout). The status screen renders them into tiles (`$8C:A89F`); the move screens convert
  the first `$80` glyphs into VRAM (`$8C:A99E`, four loaders) and draw codes as slots + `$30`.
  English letter pairs, font in `$F2`; the move screens now load `$B8` glyphs from slot `$18` to
  `$CF` (DMA `$2E00`, VRAM + `$300` words, offset `$18` at four sites; whole rows of 8 glyphs).
  Slots `$C0`-`$CF` are also the upload of the wrestler's name (`$8C:A89F`, 16 glyphs: the name
  and 8 stale ones, at `$8B:8E44`, `$8D:9675`, `$8D:AD13`, `$8D:BCF0`): a hook (`$FD:F000`) puts
  the converted pairs of `$C8`-`$CF` ($7F:AC00) into the second half of its buffer first. Pairs
  only labels use sit in label set slots `$14`-`$17`, `$05`, `$06` (set repacked in `$FD`).
  In hi-res the even pixel columns come from the main screen, which the move screens darken by
  colour math; 1-pixel letters on even columns turned dark red in palette 3, so the letters sit
  one pixel right. The finisher row has two EXTRA sprites (`$92:81DA` tiles `$28`/`$2A` at x 8,
  `$2C`/`$2E` at x 88); the left one is cleared, the right one redrawn and moved (Layout fixes). Status screen move list: rows at `$8A:BF71`..,
  column 17 -> 18. *(verified)*
- Hometowns: 54 records of 4 codes at 0x7e583 over `$90:A6B8` (each record drawn as its own 64-pixel
  picture, `$F3`). Belts: 14 records of 11 codes at 0x7ebf2 over the 2bpp `$90:959B` (64 glyphs,
  one letter each, `$F4`; not seen in play yet).

## Schedule screen art (tools/schedart.py)
- BG2: tiles `$CA:8000` (4bpp, 256), map `$B9:99B2` (32x32 words, priority added on load); the
  checker background is map words `[[1, 2], [$C002, 3]]`. The title, the stat labels and the
  攻/防 marks are redrawn into tiles of their own; both blocks move to `$F7`. *(verified)*

## Card list header
- `$8C:93CC` (promotions, League, Tournament) and `$8C:93DE` (factions): pointer tables drawn with
  `$8C:A9E7` over glyph set `$92:C421`; the small プロレス is `$8C:A111` (`$8C:AA01`). *(verified)*
- Table-driven glyph strings found so far: `$8C:F752` System menu, `$8A:9DFF` promotions,
  `$8D:EA88` tournaments, `$8E:9985` factions, `$8E:F1B9` difficulty (tools/glyphstr.py 'tables').

## Match commentary and winner quotes (tools/ticker.py)
- Commentary: 8-bit strings over the match screen's BG3 font (16x16 glyphs, names at `$C8`+),
  16-bit pointers at `$89:EAAD` (229 entries, bank set at `$81:F4AD`); `$81:F5D5` copies a string
  to `$7E:F1A1` expanding `$E0` / `$E1` / `$E3` (mover, partner, opponent); `$81:F58A` draws one
  cell every 8 frames into a scrolling row. Winner quotes: five tables of 16 at `$89:CD8B`..,
  typed by `$81:F685` (`$FE` line break). *(verified)*
- English: font8 codes in `$FA`; hooks at `$81:F5AA` and `$81:F6BB` (code at `$D0:A000`) render
  two letters into a glyph slot per cell (ticker: slots `$40`-`$5F` by map column; quotes:
  `$40`-`$7F`) and send the 32 words through the VRAM word queue `$80:94C9`.
- Savestates made mid-match keep the old bank in the ticker task's direct page (`$7E:0D42` in the
  test state); a new match sets it.

## Card list results and bout buttons (tools/results.py, tools/buttons.py)
- Results: the small 8x8 font `$92:CDF7` (tile = code, BG3 tile `$100`), drawn by `$8C:AA01`; holds
  are 37 records of 8 codes at `$8C:9FB4`.. (table `$8C:96A2`), 分 / 秒 are `$8C:A10C` / `$8C:A10E`.
  English: 5x7 capitals at codes `$0D`+, font in `$FB`. *(verified)*
- Bout buttons: 8x2 maps `$97:8C80` 観戦しない / `$97:8C91` 観戦する (pointer table `$8C:9E1F`, bank
  `LDA #$0097` at `$8C:9DE3`; both moved to `$EC`) and `$97:8CB4` 試合中, over `$91:D7B7` (only its
  first 64 tiles reach VRAM). *(verified)*

## Layout fixes (tools/layout.py)
- Heroine / faction selection bar (`$8A:93E0`): a 14x2 map of tile 1 (packed `$97:89BF`) placed on
  BG1 by `$80:AF10` at the row's offset from `$8A:9443`, cleared by `$8A:944F`; both widths 14 -> 16
  and the map repacked 16 wide in `$FF`. *(verified in game)*
- Dialogue buffer: `$8C:B450` unpacks a whole `$3C` string into `$7E:D342` (256 codes); the window
  reads it through `[$44]`, set at `$8C:AD58`. `$7E:D542` right after it is the HDMA table of
  channel 1 (COLDATA, the window's colour math): English strings over 256 codes overwrote it and
  the text darkened for the rest of the scene. Both pointers now name `$7E:F400` (0x300 bytes, zero in
  every WRAM dump taken, no writes in traces); tools/script.py refuses strings over 384 codes.
  `$7E:D342` is also scratch for other screens (`$8C:A11C`-`$8C:A625`). *(verified in game)*
- Move lists: the right EXTRA box (sprite tiles `$2C`-`$2F` of `$92:81DA`, x 88; metasprite
  `$87:E44F`) covered the level digits, in the original too; redrawn 24 pixels wide (tools/buttons.py
  REDRAW) and moved to x 82 (relative x `$50`/`$60` -> `$4A`/`$5A`, tools/buttons.py EXTRA_DEF), so it
  ends before two-digit levels (x 107); names of up to 18 letters stay clear of it.
- Exhibition / League / Tournament copy only the first `$C0` names glyphs and VRAM after them is
  in use, so the player's ring name and short name (one of the choices at 0x7e281 and one of the
  parts at 0x7e4e1, both shown there; Champion Road's Practice Match uses the same screen) must use
  codes below `$C0` too. Unshifted the roster screens would need 211 pairs; real names, ring names
  and the choices may start one letter right (tools/names.py; short names and parts never do,
  NO_SHIFT), which brings them to 191 = `$BF`, the limit. Saves made before this keep
  the old codes of the ring name. *(verified in game)*

## Banks used by this project
`$D0` code + font8, `$D1`-`$DA` script, `$E0` names, `$E1`/`$E2` help, `$E3` glyph strings,
`$E4`-`$E7` glyph sets, `$E8`-`$EF` buttons and icons, `$F0` hi-res strings, `$F1` status font,
`$F2` move font, `$F3` hometowns, `$F4` belts, `$F5` League font, `$F6` move tabs, `$F7`
schedule art, `$F8` card list set, `$F9` World Circuit font, `$FA` commentary and quotes, `$FB` small result font,
`$FC` rivals font, `$FD` move label set + name hook, `$FE` match strategy icons, `$FF` layout fixes
(tools/layout.py).

## Images
- Done: buttons, headers and icons (tools/buttons.py), the schedule screen art (tools/schedart.py),
  the match strategy icons (tools/strategy.py): 32x16 on BG2 (palette 3, map row 24, cell 17),
  tiles packed at `$B0:DCFE` (49 tiles, VRAM `$CF`-`$FF`, one loader `$84:80E1`), records of 8 map
  words at `$B9:9932` (大技 間合 忍耐 必殺 返し 一撃 場外 フォール) that `$80:AF31` copies on a
  strategy change. English: BIG RNG END FIN CTR KO OUT PIN, repacked into `$FE`.
  Kept in Japanese by choice: the save slots' ticket picture, the title logo and the main menu's
  background pattern (the logo), the title screen's copyright line.

## Open questions
- Is the ROM the No-Intro dump? CRC32 `f4d20413` - not yet compared with the DAT.
- Method `$0E` of the decompressor (a tree code) is not decoded.
- Belt names (tools/recfont.py) have not been seen on screen in the English build.
