#!/usr/bin/env python3
"""Build the translated image from the original. Standard library only.

  python3 build.py [--name NAME] [--unlocks all|none|GROUP,...] [--clean]
      -> build/NAME.<ext> (default NAME: "<game> (English)")

Steps (default folders shown; move any of them with the folder options - see --help):
  1. verify the original in rom/ (size + SHA-1; --skip-verify skips the hash)
  2. prepare build/NAME: a fresh copy of the original, or - much faster for big images - the last
     build with every range it wrote restored from the original (tools/image.py; --clean copies)
  3. text: translation/script/ and translation/text/ into the game's files (TEXT_STEPS)
  4. code patches picked by --unlocks (CODE_PATCHES, tools/codepatch.py)
  5. images: for every catalogued image the English file the catalogue picks (hand-made >
     approved > rendered), imported by tools/gfx.py; the final set is copied to review/images-english/
  6. write every changed file back into the image (files that fit in place first)

Test builds: --boot PART starts the game straight in PART (BOOT_PATCHES, once known);
--no-translation skips text and images, and gameplay patches unless --unlocks is given - on its
own the result is byte-identical to the original (tools/check.py --control proves it).
Developer flags (never for releases): --no-text FILE skips one text file.
"""
import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / 'tools'))
import catalog  # noqa: E402
import codepatch  # noqa: E402
import disc  # noqa: E402
import gfx  # noqa: E402
import image  # noqa: E402
import paths  # noqa: E402
import buttons  # noqa: E402
import glyphstr  # noqa: E402
import helptext  # noqa: E402
import hires  # noqa: E402
import hooks  # noqa: E402
import layout  # noqa: E402
import moves  # noqa: E402
import names  # noqa: E402
import recfont  # noqa: E402
import results  # noqa: E402
import schedart  # noqa: E402
import script  # noqa: E402
import ticker  # noqa: E402
import snes  # noqa: E402
import strategy  # noqa: E402

# Gameplay patches: (group, file, address, original, new, description) - see tools/codepatch.py.
CODE_PATCHES = [
]
UNLOCK_GROUPS = sorted({p[0] for p in CODE_PATCHES})

# --boot: (part, file, address, original, new) - patches that start the game in a given part.
BOOT_PATCHES = {
}


def to_offset(name, addr):
    """File offset of CPU address `addr` ($80:8000 = 0x808000) in the ROM (LoROM FastROM)."""
    return snes.Rom(bytes(Files.current.get(name))).to_file(addr)


# Text steps: (text file or folder under translation/, function(path, files)). Each inserts the
# English into the game's files through `files` and stops with a clear message if anything doesn't fit.
# Zero-padding files a grown file may take room from when the disc is full (PS2 disc.py
# take_from_padding: their end is cut off) - e.g. ['/DUMMY.DAT']; check they are all zeros.
PADDING_DONORS = []

def script_step(path, files):
    """The dialogue: expand the ROM, install the 8x16 renderer (tools/hooks.py), pack the English
    script into the new banks and repoint the event scripts (tools/script.py insert)."""
    rom = hooks.apply(files.get('/rom.sfc'))
    n, size, last = script.insert(rom, hooks.SCRIPT_FIRST_BANK)
    nr, npairs, nsites, nfont = names.apply(rom)
    mr, mpairs, msites = moves.apply(rom)
    print(f'text: {mr} move names ({mpairs} letter pairs, {msites} loaders)')
    for rf in recfont.FONTS:
        nr2, ng, ns2 = recfont.apply(rom, rf)
        print(f'text: {rf}: {nr2} records, {ng} glyphs/letters, {ns2} loaders')
    for hs in helptext.SETS:
        nm, nl, nd = helptext.apply(rom, hs)
        print(f'text: {hs}: {nm} messages, {nl} letters, {nd} direct loads')
    for gs in glyphstr.SETS:
        ns, nsites = glyphstr.apply(rom, gs)
        print(f'text: menu_{gs}: {ns} strings at {nsites} call sites')
    print(f'text: {results.apply(rom)} finishing holds on the card list')
    print(f'text: {buttons.apply(rom)} sprite button labels')
    print(f'text: schedule screen art ({schedart.apply(rom)} loaders)')
    print(f'text: match strategy icons ({strategy.apply(rom)} tiles)')
    print(f'text: {ticker.apply(rom)} commentary and winner quote strings')
    print(f'text: {layout.apply(rom)} layout fixes')
    for hs in hires.SCREENS:
        ns, nsites = hires.apply(rom, hs)
        print(f'text: hires_{hs}: {ns} strings, {nsites} call sites and table entries')
    files.put('/rom.sfc', rom)
    print(f'text: {nr} names ({npairs} letter pairs, font {nfont} bytes, {nsites} loaders)')
    print(f'text: {n} dialogue strings, {size} bytes in banks ${hooks.SCRIPT_FIRST_BANK:02X}-${last:02X}')


TEXT_STEPS = [
    ('script', script_step),
]


class Files:
    """The game's files for this build: read from the image on first use, written back at the end."""

    current = None

    def __init__(self, d):
        self.d, self.data, self.changed = d, {}, set()
        Files.current = self

    def get(self, name):
        if name not in self.data:
            self.data[name] = bytearray(self.d.read_file(self.d.find(name)))
        return self.data[name]

    def put(self, name, data):
        self.data[name] = bytearray(data)
        self.changed.add(name)


def unlock_groups(value):
    if value == 'all':
        return set(UNLOCK_GROUPS)
    if value == 'none':
        return set()
    groups = {g.strip() for g in value.split(',') if g.strip()}
    if groups - set(UNLOCK_GROUPS):
        raise argparse.ArgumentTypeError(f'expected all, none or some of {",".join(UNLOCK_GROUPS) or "(no groups yet)"}')
    return groups


def images_step(files):
    final = catalog.final_images()
    missing, changed, _ = catalog.stale()
    if missing or changed:
        print(f'note: {len(missing) + len(changed)} automatic renders are out of date - run tools/render.py '
              f'(building with the frozen files there are)')
    n = gfx.import_images({k: p for k, (tag, p) in final.items()}, files)
    if paths.ENGLISH_IMAGES.exists():
        shutil.rmtree(paths.ENGLISH_IMAGES)
    if final:
        paths.ENGLISH_IMAGES.mkdir(parents=True)
        for name, (tag, p) in final.items():
            shutil.copyfile(p, paths.ENGLISH_IMAGES / f'{name}.png')
        counts = {}
        for tag, _ in final.values():
            counts[tag] = counts.get(tag, 0) + 1
        print(f'images: {n} imported (' + ', '.join(f'{c} {t}' for t, c in sorted(counts.items())) + ')')


def verify_original(original):
    """SHA-1 of the original image, once: the result is remembered with the file's size and
    modification time (build/original.verified), so later builds only re-hash a changed file
    (a DVD image takes ~20 s to hash)."""
    st = original.stat()
    stamp = f'{original.resolve()} {st.st_size} {st.st_mtime_ns} {paths.ORIGINAL["sha1"]}'
    memo = paths.BUILD / 'original.verified'
    if memo.exists() and memo.read_text() == stamp:
        return
    print('verifying the original...')
    if image.sha1(original) != paths.ORIGINAL['sha1']:
        sys.exit(f'{original.name} does not match the expected SHA-1 {paths.ORIGINAL["sha1"]}')
    paths.BUILD.mkdir(parents=True, exist_ok=True)
    memo.write_text(stamp)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0], epilog=paths.FOLDER_HELP,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--name', default=f'{paths.GAME_FILE} (English)')
    ap.add_argument('--skip-verify', action='store_true', help="don't hash the original image")
    ap.add_argument('--clean', action='store_true', help='copy the original instead of restoring the last build')
    ap.add_argument('--no-translation', action='store_true', help='skip text and images (alone: identical to the original)')
    ap.add_argument('--unlocks', type=unlock_groups, metavar='all|none|GROUP,...',
                    help='gameplay patches: all (default), none or some groups; none with --no-translation')
    ap.add_argument('--boot', choices=sorted(BOOT_PATCHES), help='TEST BUILD: start the game in this part')
    ap.add_argument('--no-text', action='append', default=[], metavar='FILE',
                    help='developer: leave this text file untranslated (repeatable)')
    args = ap.parse_args(paths.configure(sys.argv[1:] if argv is None else argv))
    if args.unlocks is None:
        args.unlocks = set() if args.no_translation else set(UNLOCK_GROUPS)

    original = paths.ROM
    if not original.exists():
        sys.exit(f'put the original image in {paths.show(paths.ROM_DIR)} (or pass --rom): {paths.ORIGINAL_NAME}')
    if original.stat().st_size != paths.ORIGINAL['size']:
        sys.exit(f'{original.name}: {original.stat().st_size} bytes, expected {paths.ORIGINAL["size"]} - not the right image')
    if not args.skip_verify:
        verify_original(original)

    out = paths.BUILD / (args.name + original.suffix)
    with image.prepare(original, out, clean=args.clean) as f:
        d = disc.Disc(f, writable=True)
        files = Files(d)

        if not args.no_translation:
            for rel, step in TEXT_STEPS:
                if rel in args.no_text:
                    print(f'text: skipped {rel} (--no-text)')
                    continue
                step(paths.TRANSLATION / rel, files)

        codepatch.apply(files, CODE_PATCHES, args.unlocks, to_offset)

        if not args.no_translation:
            images_step(files)

        if args.boot:
            codepatch.apply(files, [(args.boot, *p, f'TEST BUILD: boots into {args.boot}') for p in BOOT_PATCHES[args.boot]],
                            {args.boot}, to_offset)

        def fits(name):
            return (len(files.data[name]) + disc.SECTOR - 1) // disc.SECTOR <= d.allocated_sectors(d.find(name))
        for name in sorted(files.changed, key=lambda n: (not fits(n), n)):  # fixed order: same disc layout every build
            d.write_file(d.find(name), bytes(files.data[name]), relocate=True,
                         **({'donors': PADDING_DONORS} if PADDING_DONORS else {}))
            print(f'patched {name}')
    disc.companion_files(out)
    print(f'done: {paths.show(out)}  ({len(files.changed)} files patched)')
    return out


if __name__ == '__main__':
    main()
