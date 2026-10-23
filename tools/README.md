# Tools

Everything is Python 3 and runs from the project folder or anywhere else; every tool has `--help`
(or prints its usage). Folder locations come from [paths.py](paths.py) and can be moved with the
folder options. `build.py`, `make_patches.py` and everything they import use only the standard
library; the tools marked *Pillow* or *capstone* need `.venv` (`pip install -r requirements.txt`).

Set up from the translation kit (version 06a12b0). The kit's image workflow (`gfx.py`, `render.py`,
`edit.py`, `compare.py`, `contact.py`, `catalog.py`) is not used by this game: its text graphics are
drawn by the build steps below (docs/EDITING.md), and `gfx.py` / `extract.py`'s `unpack()` stay stubs.

## Used by the build

| Tool | What it does |
|---|---|
| [../build.py](../build.py) | builds the translated image (text steps, code patches, images, write-back) |
| [paths.py](paths.py) | every folder location and the folder options |
| [image.py](image.py) | the output image: fresh copy or fast restore from a journal; checksums |
| [disc.py](disc.py) | reads and writes files in the image (SNES; a cartridge ROM is one file - docs/PLATFORM.md) |
| [codepatch.py](codepatch.py) | applies code patch tables, checking the original bytes first |
| [catalog.py](catalog.py) | the image catalogue: which file the build uses, fingerprints, stale renders |
| [gfx.py](gfx.py) | *game*: exports the original images, imports the English ones |
| [pngio.py](pngio.py) | PNG reading and indexed PNG writing without dependencies |
| [blocks.py](blocks.py), [textdb.py](textdb.py) | message block files; every translatable string as one list |
| [snes.py](snes.py) | header, LoROM/HiROM/ExHiROM map (CPU address ↔ file offset), checksum, expansion, free space |
| [bps.py](bps.py) | BPS patches: make and apply (release patches) |
| [snesgfx.py](snesgfx.py) | planar 1/2/4/8bpp and Mode 7 tiles, BGR555 palettes, PNG sheets |
| [tbl.py](tbl.py) | `.tbl` character tables: decode, dump, encode |

## Build steps for this game

All run inside `build.py`'s text step, in this order; each has `--help` or a usage line, and most
can draw a preview (*Pillow*).

| Tool | What it does |
|---|---|
| [hooks.py](hooks.py) | ROM expansion to 32 Mbit, the 8x16 dialogue renderer and its code hooks (`show`) |
| [script.py](script.py) | the dialogue and profiles: dump, check and insert the packed 10-bit script (`dump`, `show`, `check`) |
| [names.py](names.py) | wrestler names as letter pairs in the names font (`stats`, `sheet`) |
| [moves.py](moves.py) | move names and the move screens' labels (`stats`) |
| [recfont.py](recfont.py) | hometown and belt fonts of the status screen (`sheet`) |
| [helptext.py](helptext.py) | the schedule screen's help texts (`dump`) |
| [glyphstr.py](glyphstr.py) | menu and window texts drawn from each screen's glyph set (`scan`, `dump`) |
| [results.py](results.py) | match times and finishing holds on the card list |
| [buttons.py](buttons.py) | button labels drawn as sprites (`sheet`) |
| [schedart.py](schedart.py) | the schedule screen's title and stat-label art (`preview`) |
| [strategy.py](strategy.py) | the match strategy icons (`preview`) |
| [ticker.py](ticker.py) | match commentary and winner quotes, drawn on the fly (`dump`) |
| [layout.py](layout.py) | layout fixes: wider selection bar, dialogue buffer moved clear of the HDMA table |
| [hires.py](hires.py) | labels of the hi-res screens (status, logic, Rivals, Stats Up, League, World Circuit) (`dump`) |
| [font8.py](font8.py) | the English 8x16 letters every step above draws with (`sheet`) |
| [kpack.py](kpack.py) | the game's compression: unpack and pack (`unpack`, `info`) |
| [asm65816.py](asm65816.py) | a small 65816 assembler for the hooks |

## Checking

| Tool | What it does |
|---|---|
| [check.py](check.py) | runs every check (`--quick` for the pre-commit hook, `--control` for a lossless-build proof) |
| [lint.py](lint.py) | text: leftover source text, control codes, line/char/byte limits, glossary |
| [status.py](status.py) | how far along the text and images are |
| [records.py](records.py) | fixed-record text tables (names, items, menus of records): `dump` the CSV, `verify` the layout, `measure` unknown data, build step - configure `TABLES` |
| [stepcheck.py](stepcheck.py) | run one build text step against `extracted/` (no image, nothing written) and list what it changed - for testing a step while the image is busy |

## Translating

| Tool | What it does |
|---|---|
| [fill_text.py](fill_text.py) | fills repeated strings from a source → English table |
| [render.py](render.py) | *Pillow*: automatic English renders, only redrawing what changed |
| [edit.py](edit.py) | *Pillow*: hand-edit workflow - start, check, approve, reset, sheets |
| [compare.py](compare.py) | *Pillow*: original \| English sheets |
| [contact.py](contact.py) | *Pillow*: every original image on labelled sheets |

## Releasing

| Tool | What it does |
|---|---|
| [../make_patches.py](../make_patches.py) | builds every variant, makes and re-verifies the patches, README.txt and the zip |

## Research

| Tool | What it does |
|---|---|
| [extract.py](extract.py) | copies the ROM to `extracted/rom.sfc` for the research tools |
| [events.py](events.py) | event-script disassembler and listings; test images for the World Circuit and Champion Road (`dis`, `listing`, `wctest`, `crtest`) |
| [mesen.py](mesen.py) | drives the game headless in Mesen 2 from a list of steps: input, screenshots, savestates, memory dumps, traces |
| [fontid.py](fontid.py) | *Pillow, numpy*: identifies a 16x16 font's glyphs against JIS X 0208 |
| [sjisscan.py](sjisscan.py) | finds Shift-JIS text in binary files |
| [relsearch.py](relsearch.py) | relative search for text in an unknown encoding (kana orders, ASCII, 8/16-bit) |
| [dis65816.py](dis65816.py) | 65816 disassembler (M/X flags followed through REP/SEP) and reference/pointer search |
