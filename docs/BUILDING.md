# Building

## Requirements

- Python 3.9+ - `build.py` and `make_patches.py` use only the standard library (the release
  patches are BPS, made by tools/bps.py; no xdelta is needed)
- For the research and preview tools: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`

## Setup (once)

1. Put `Bishoujo Wrestler Retsuden - Blizzard Yuki Rannyuu!! (J).smc` in `rom/` (or pass `--rom`):
   2,621,440 bytes, no copier header, CRC32 `f4d20413`, SHA-1 `de5fc2caae6803bfcb2eaf831a346b0e422a4e77`.
2. `python3 build.py` - the first build copies the ROM; later builds only restore what changed.

`python3 tools/extract.py` copies the ROM to `extracted/rom.sfc` for the research tools; the
build doesn't need it.

## I want to...

| I want to... | Do this |
|---|---|
| Build the translation | `python3 build.py` → `build/Bishoujo Wrestler Retsuden - Blizzard Yuki Rannyuu!! (English).smc` |
| See how far along it is | `python3 tools/status.py` |
| Check everything | `python3 tools/check.py` (`--control`: prove the build is lossless) |
| Check text only | `python3 tools/lint.py --warnings` (`--missing`: untranslated entries) |
| Check the dialogue's fit | `python3 tools/script.py check` |
| Look at a font or art the build draws | the tool's `sheet` / `preview` command (*Pillow*), see [tools/README.md](../tools/README.md) |
| Make release patches | `python3 make_patches.py --version v0.1` → `release/` |
| Run checks before every commit | `python3 tools/check.py --install-hook` |

## Build options

| Option | |
|---|---|
| `--name NAME` | output name (default `Bishoujo Wrestler Retsuden - Blizzard Yuki Rannyuu!! (English)`) |
| `--clean` | copy the original instead of restoring the last build |
| `--no-translation` | skip text and images; alone the result is identical to the original |
| `--no-text FILE` | developer: leave one text file untranslated |
| `--skip-verify` | don't hash the original |
| `--unlocks`, `--boot` | from the translation kit; this game has no gameplay or test-start patches yet |

## Folder options

Every tool takes `--root`, `--rom`, `--translation`, `--extracted`, `--build`, `--review` (see
`--help`); the defaults are the folders in [tools/paths.py](../tools/paths.py).
