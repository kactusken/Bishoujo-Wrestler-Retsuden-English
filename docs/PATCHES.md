# Patches

Everything the build changes besides putting English text in place. The details (original code,
addresses, limits) are in [TECHNICAL.md](TECHNICAL.md); this is the index. Each step runs from
build.py, checks the original bytes before it writes, and stops with a message if they differ.
The release patch has no gameplay changes (build.py `CODE_PATCHES` is empty).

| Change | Tool | Why | Details | Status |
|---|---|---|---|---|
| ROM expanded to 32 Mbit; 8x16 dialogue renderer (Collect8 / Render8 / Tile8), text from column 2 | tools/hooks.py, tools/script.py | 16x16 kanji cells fit 13 letters a line; English needs 26-30 | [English text](TECHNICAL.md#english-text-this-projects-code-toolshookspy) | verified in game |
| Glyph codes stored as bytes, not words | tools/hooks.py (Collect8) | English pages of more than 64 codes overwrote the event pointer at `$7E:F221` | [Executable and memory](TECHNICAL.md#executable-and-memory) | verified in game |
| Dialogue strings indented by the speaker's face slot | tools/script.py | narration uses the full width, faced lines start at column 6 | [English text](TECHNICAL.md#english-text-this-projects-code-toolshookspy) | verified in game |
| Dialogue unpack buffer `$7E:D342` -> `$7E:F400`, strings capped at 384 codes | tools/layout.py, tools/script.py | long strings overwrote the window's HDMA table and darkened the text | [Layout fixes](TECHNICAL.md#layout-fixes-toolslayoutpy) | verified in game |
| Names font rebuilt as letter pairs; roster screens' names kept below `$C0` | tools/names.py | names drawn from 16x16 glyphs; those screens load only `$C0` glyphs | [Text](TECHNICAL.md#text), [Layout fixes](TECHNICAL.md#layout-fixes-toolslayoutpy) | verified in game |
| Schedule help texts drawn in half-glyph letters (TileH), every loader repointed | tools/helptext.py | 11 kanji per line -> 22 letters | [Help texts](TECHNICAL.md#schedule-screen-help-texts-toolshelptextpy) | verified in game |
| Menu glyph strings and their glyph sets | tools/glyphstr.py | per-screen glyph sets of kanji | [Glyph strings](TECHNICAL.md#glyph-strings-menus-headers) | verified in game |
| Hi-res labels (status, logic, info, Stats Up, League, World Circuit, rivals), label moves | tools/hires.py | mode 5 screens, one glyph slot per code | [Hi-res screens](TECHNICAL.md#hi-res-screens-toolshirespy-toolsmovespy-toolsrecfontpy) | verified in game |
| Move names; move screens load glyphs from slot `$18`; name-upload hook at `$FD:F000` | tools/moves.py | more letter pairs than the screens loaded | [Hi-res screens](TECHNICAL.md#hi-res-screens-toolshirespy-toolsmovespy-toolsrecfontpy) | verified in game |
| Hometowns and belt names | tools/recfont.py | record fonts | [Hi-res screens](TECHNICAL.md#hi-res-screens-toolshirespy-toolsmovespy-toolsrecfontpy) | hometowns verified; belts not seen yet |
| Sprite buttons, headers, background buttons, OK button, EXTRA box (redrawn and moved) | tools/buttons.py | text drawn as graphics | [Buttons and headers](TECHNICAL.md#buttons-and-headers-toolsbuttonspy), [Layout fixes](TECHNICAL.md#layout-fixes-toolslayoutpy) | verified in game |
| Schedule screen art | tools/schedart.py | title, stat labels and marks are art | [Schedule art](TECHNICAL.md#schedule-screen-art-toolsschedartpy) | verified in game |
| Match strategy icons | tools/strategy.py | 32x16 kanji icons | [Images](TECHNICAL.md#images) | verified in game |
| Commentary ticker and winner quotes rendered on the fly (hooks at `$81:F5AA`, `$81:F6BB`) | tools/ticker.py | 16x16 font with no room for English | [Commentary](TECHNICAL.md#match-commentary-and-winner-quotes-toolstickerpy) | verified in game |
| Card list results font, bout buttons | tools/results.py, tools/buttons.py | small kanji font and button maps | [Card list results](TECHNICAL.md#card-list-results-and-bout-buttons-toolsresultspy-toolsbuttonspy) | verified in game |
| Heroine / faction selection bar 14 -> 16 tiles | tools/layout.py | 15-letter names ran past the bar | [Layout fixes](TECHNICAL.md#layout-fixes-toolslayoutpy) | verified in game |
| Internal checksum | tools/disc.py | fixed on every build | [ROM layout](TECHNICAL.md#rom-layout) | - |

Bank use: [Banks used by this project](TECHNICAL.md#banks-used-by-this-project).
