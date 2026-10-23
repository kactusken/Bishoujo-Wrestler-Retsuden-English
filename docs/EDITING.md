# Images with text

This game's text graphics are not edited as pictures. Every English label, font and piece of art
is drawn by a build step from letters defined in the tools, then packed back into the ROM, so
`translation/graphics.csv` is empty and the translation kit's hand-edit workflow (`render.py`,
`edit.py`, `compare.py`, `translation/images-*`) is not used.

To change one, edit the text or the tool and rebuild; each tool can draw a preview (*Pillow*).

| What | Where the English is | Preview |
|---|---|---|
| Dialogue letters (8x16) | `tools/font8.py` (the letter shapes) | `font8.py sheet OUT.png` |
| Wrestler names (letter pairs) | `translation/names.tsv` | `names.py sheet OUT.png`, `names.py stats` |
| Move names | `translation/moves.tsv`, `movelabels.tsv` | `moves.py stats` |
| Hometowns and belts | `translation/places.tsv`, `belts.tsv` | `recfont.py sheet places\|belts OUT.png` |
| Button labels drawn as sprites (OK, Back, Single, ...) | `LABELS` in `tools/buttons.py` | `buttons.py sheet OUT.png` |
| Schedule screen title and stat labels | `tools/schedart.py` | `schedart.py preview OUT.png` |
| Match strategy icons (BIG RNG END FIN CTR KO OUT PIN) | `tools/strategy.py` | `strategy.py preview OUT.png` |

Run the previews with `.venv/bin/python` (`pip install -r requirements.txt`). Then
`python3 build.py` and look at the screen in an emulator.

Left in Japanese on purpose: the title logo, the same logo repeated behind the main menu and the
profiles, the ticket picture on the save screen, and the copyright line on the title screen.
