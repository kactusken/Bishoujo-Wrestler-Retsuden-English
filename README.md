# Bishoujo Wrestler Retsuden: Blizzard Yuki Rannyuu!! — English Translation

An English translation patch for **Bishoujo Wrestler Retsuden: Blizzard Yuki Rannyuu!!**
(美少女レスラー列伝 ブリザードYuki乱入!!), a women's pro wrestling management game by KSS for the
Super Famicom (1996), released only in Japan.

Everything is in English: all 3,413 lines of story across Champion Road (the career mode, with
nine endings) and the World Circuit, the wrestlers' names and profiles, every menu, the schedule
and training help, move names, the match commentary and the winners' quotes. The game draws its
text as 16×16 kanji. The patch adds a new 8×16 English font, drawn into the game's text by a
renderer hook, and fits the wrestlers' names into the old name font by packing two letters into
each tile.

**[See screenshots](docs/SCREENSHOTS.md)** of the patched game.

> **Status: v0.1, the first public release.** All text is translated. Every ending was reached
> in an emulator, but not every route and mode has been played through from start to finish.
> Please report anything that looks wrong ([how to report](#reporting-problems)).
> [CHANGELOG.md](CHANGELOG.md) lists what's in each release.

## Downloads

Get the latest zip from the [Releases](../../releases) page. It contains one patch:

| Patch | What you get |
|---|---|
| **Bishoujo Wrestler Retsuden - Blizzard Yuki Rannyuu!! (English)** | The translation, with the game otherwise unchanged. |

## How to patch

You need your own copy of the original Japanese cartridge ROM. ROMs are not provided here.

- Game: *Bishoujo Wrestler Retsuden: Blizzard Yuki Rannyuu!!* (Japan), serial SHVC-A3QJ-JPN.
- The ROM must match: 2,621,440 bytes with no copier header, CRC32 `f4d20413`,
  SHA-1 `de5fc2caae6803bfcb2eaf831a346b0e422a4e77`.

Then:

1. Apply the `.bps` patch with a BPS patcher:
   - [Rom Patcher JS](https://www.marcrobledo.com/RomPatcher.js/) runs in your web browser.
   - Floating IPS (Flips) on Windows or Linux, MultiPatch on macOS.

   The patcher checks the ROM first. If it refuses, you have a different dump, or your ROM has a
   512-byte copier header (Rom Patcher JS can remove it).
2. Open the patched ROM in your emulator. The patch was tested in Mesen.

## Notes for players

- **Start a new game.** Saves made with the Japanese game, or with a different version of the
  patch, store names in the old letter codes, so the names show up garbled.
- **Names.** Wrestlers' names are written family name last, in capitals in the game's own name
  font. The readings follow the game's own kana records: 新咲 is Shinzaki and 羽田 is Hada.
  ブリッド, in two of the ending titles, is "Hybrid".
- **What's still in Japanese.** The title logo, the same logo repeated as the menu background, the
  ticket picture on the save screen and the copyright line on the title screen. These are left
  as they are on purpose.
- **Guides.** [docs/CHAMPION_ROAD.md](docs/CHAMPION_ROAD.md) explains how Champion Road works:
  the rating gates, training, how matches are decided and how to reach each ending. The same, with a
  route map, as a web page: [the Champion Road field guide](https://kactusken.github.io/Bishoujo-Wrestler-Retsuden-English/champion-road/).
- **Hidden content.** Button codes, a developers' move tester, four hidden wrestlers, and 519
  lines of cut story: see [docs/HIDDEN_CONTENT.md](docs/HIDDEN_CONTENT.md), and
  [the cut-content page](https://kactusken.github.io/Bishoujo-Wrestler-Retsuden-English/cut-content/) to read the cut scenes.

## Reporting problems

Open an [issue](../../issues) with:

- a screenshot,
- which patch version you used,
- where you were: the mode and menu, or roughly what had just happened.

Text that is cut off, overlaps, or still shows Japanese is especially helpful.

## For ROM hackers and contributors

Everything needed to rebuild the patch from the original ROM is in this repository: the
translated text, the patching code (Python 3, no dependencies for the build) and documentation of
the game's formats.

| Document | What's in it |
|---|---|
| [docs/BUILDING.md](docs/BUILDING.md) | Setting up, building, making patches, and the checking tools |
| [docs/TRANSLATION.md](docs/TRANSLATION.md) | Text file formats, scope, style guide, glossary, and naming decisions |
| [docs/EDITING.md](docs/EDITING.md) | Where each piece of English text art comes from |
| [docs/PATCHES.md](docs/PATCHES.md) | Each code patch and hook, with links to the details |
| [docs/TECHNICAL.md](docs/TECHNICAL.md) | The ROM layout, text and name formats, fonts, compression, and memory map |
| [docs/PLATFORM.md](docs/PLATFORM.md) | SNES pitfalls for this kind of work |
| [docs/CHAMPION_ROAD.md](docs/CHAMPION_ROAD.md) | Champion Road's rules, decoded from the event script |
| [docs/HIDDEN_CONTENT.md](docs/HIDDEN_CONTENT.md) | Codes, debug features, and unused and cut content |
| [tools/README.md](tools/README.md) | Every tool, what it's for and how to run it |

Quick start:

```sh
python3 tools/extract.py                 # copy the ROM in rom/ to extracted/ for the research tools
python3 build.py                         # -> build/Bishoujo Wrestler Retsuden - Blizzard Yuki Rannyuu!! (English).smc
python3 make_patches.py --version v0.1   # -> release/: the .bps patch and a zip
```

## AI disclosure

This translation was made with the assistance of AI.

## Legal

This is a non-commercial fan translation, not affiliated with or endorsed by the game's developers
or publishers. It contains no copyrighted game data that would let anyone play without owning the
game. The patch only works on your own copy of the ROM. Bishoujo Wrestler Retsuden: Blizzard Yuki
Rannyuu!! and its contents belong to their respective owners. The Japanese text in this repository
is included for translation and reference.

The code in this repository is released under the [MIT License](LICENSE).
