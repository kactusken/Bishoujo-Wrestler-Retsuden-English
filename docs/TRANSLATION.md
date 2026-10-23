# Translation

## Where the text is

| File | Holds | Checked by |
|---|---|---|
| `translation/script/bank_XX.txt` | the story dialogue (Champion Road and the World Circuit), one file per ROM bank (`tools/script.py dump`) | `tools/script.py check`, `tools/lint.py` |
| `translation/script/profiles.txt` | the 60 wrestler profile blurbs (4 lines of 28 letters) | `tools/script.py check` |
| `translation/names.tsv` | every name record: real names, ring names, short names, ring name parts | `tools/names.py stats` |
| `translation/tables/font98.tsv`, `font90.tsv` | the Japanese fonts, code -> character | |
| `translation/text/schedule_help.txt` | the schedule screen's help texts (line 1: 22 letters, line 2: 21) | build (tools/helptext.py) |
| `translation/text/menu_*.txt` | glyph strings per glyph set (headers, lists, options, card list header) | build (tools/glyphstr.py) |
| `translation/text/hires_*.txt` | labels of the hi-res screens (status, logic, info box, stat-up, League, World Circuit), one letter per cell | build (tools/hires.py) |
| `translation/moves.tsv`, `movelabels.tsv` | the 105 move names (24 capitals) and the move screens' labels | build (tools/moves.py) |
| `translation/text/ticker.txt`, `winner.txt` | match commentary (one line, 110 letters) and winner quotes (4 lines of 22) | build (tools/ticker.py) |
| `translation/places.tsv`, `belts.tsv` | hometowns (about 9 capitals) and belt names (11 letters) | build (tools/recfont.py) |
| `translation/glossary.csv` | names and terms | `tools/lint.py` |
| `translation/graphics.csv` | empty: the text graphics are drawn by build steps ([EDITING.md](EDITING.md)) | `tools/check.py` |

## File format

Message blocks: `@ offset refs=N`, `JP` lines (reference), `EN` lines. One line = one line on
screen. Codes: `{p}` page start, `{w}` wait for a button (end of page), `{s1}`-`{s6}` the scene's
speaker name (alone on the first line of a page: the game draws the name there), `{n1}`-`{n6}`
names inside sentences (`{n1}` is usually the heroine), `{player}` the heroine's ring name,
`{3E2}` `{3E9}` `{3EA}` rare codes kept as they are. Pages without `{w}` are choice menus.

Limits: 4 lines per page; 30 letters per line in narration (no speaker code, every page waits),
26 in all other strings (the speaker's face fills the left of the window). Names count 8 letters,
`{player}` 16. The encoder wraps long lines and splits full pages (`{w}` + `{p}`), so the checker
only warns; the translation currently fits without either.

## Style guide

- Names: Western order; glossary spellings (shared with Super Wrestle Angels where the same
  wrestlers appear). 新咲 = Shinzaki and 羽田 = Hada, as the game's own kana records read them.
- Honorifics dropped except `senpai`. 社長 = the President / Boss.
- No speaker labels or quote marks in dialogue (the game draws the speaker's name and face).
- `・・・` -> `...`. Foreign characters' broken Japanese (Ｍｅ, ヨ, ネ) -> lightly broken English;
  the Kansai-dialect World Joshi president -> casual, dropped-g speech.
- Names drawn by the game (speaker labels, select screens, lists) are in CAPITALS.

## Glossary

`translation/glossary.csv` (`japanese, english, notes`).

## Decisions

| Decision | Why |
|---|---|
| English drawn by a new 8x16 renderer, one letter per 8-pixel column (tools/hooks.py) | 26-30 letters per line instead of 13 glyphs; the 16-bit code list, 4 KB buffer and VRAM area of the original are reused |
| Narration starts at column 2, everything else at column 6 | faces fill columns 0-5; choice menus keep the original column |
| Names in capitals | the names font holds codes 1-$BF: letter pairs in mixed case need ~230, in capitals 191, every code (with some names shifted, below) |
| 新咲 Shinzaki, 羽田 Hada | the game's own kana records (しんざき, はだ); the glossary first had Niisaki / Haneda |
| A name of odd length used inside a sentence leaves a space before the next character ("Yukiko Shinzaki .") | names are two letters per glyph; same choice as Super Wrestle Angels |
| Names of minor characters romanized by guess: Zail (ザイル), Peil (ペイル), Kima (木間), Maegami (前上), Sae / Saeko (さえ / さえ子), Kana Kozuki (香月) | accepted for now (user, 2026-10-22); open to change if a better source turns up - names live in translation/glossary.csv and translation/names.tsv |
| Offensive language is translated as written (Dynamite Lin's ジャップ -> "Jap") | user, 2026-10-22: translate what's there, don't rewrite the script |
| Buttons: 決定 = "OK" (its two sprites moved side by side, and the background bar's halves rearranged), メニューに戻る = Back, 自動/手動 = Auto/Play, 6人タッグ = Trios, styles Safe/Fight/Even/Rush | the label space is fixed; "Manual" and "Steady"/"Charge" did not fit |
| アシスト (assist pattern) = "Tag", アシストパターン = "Tag Style", values Assist / Normal / Solo | "Assist Assist" read badly; the info box has 5 cells for the label |
| Status labels: Name / AKA / Real, Rating, From, Belts, Atk / Def, Str Dex Sta Rec Spd Guts; move types Throw / Holds / Power / Hits / Air, 空中技 = Dive | one 8-pixel letter per cell, in the space the kanji had |
| Logic options: Big, Range, Endure, Finish, Counter, KO Blow, Outside, Pinfall (大技 間合 忍耐 必殺 返し 一撃 場外 フォール) | literal, 7 letters at most; the exact game effect of each is not verified |
| Move names in capitals, some shortened: SPEED BRAINBUSTER, NORTHERN SUPLEX / BOMB, ARMBAR HOLD (ワキ固め), SCORPION HOLD, SHORT LARIAT, HEEL DROP (かかと落とし), COMBO KICK, JUMPING KNEE, FLYING SHOULDER, NECKBREAKER DROP, HURACANRANA; S / D / JO kept as letters | the move screens hold 167 letter pairs in VRAM; the full names needed 215. Some names start one letter in or have two spaces between words to share pairs |
| Guessed readings in move names: アキレス朧固め = Achilles Hold (朧 read as 腱), 図器攻撃 = Weapon Attack (図 read as 凶), Rゴリースペシャル = Reverse Gory Special | font glyph misreads, like the dialogue's |
| Hometowns: prefecture names without -ken (YAMAGUCHI), イギリス = BRITAIN | each record is drawn as its own picture, 9 letters fit |
| Factions shortened where space is short: Regulars, Revolution (革命軍), Team Ryuko, Ichigaya, Team Yuki; full "Shinjo Regulars" / "Revolutionaries" in the card list | 10-13 letter fields |
| Schedule screen: 今週のよてい! = "Weekly Plan!", stat bars STR DEX STA REC SPD GUT, types THR HLD POW HIT AIR, 攻 / 防 = ATK / DEF | redrawn art in the original's style (tools/schedart.py) |
| League labels "Team 1" .. "Team 8", 4チーム = "4 Team" | the digit is a separate sprite |
| Commentary and winner quotes: mixed case, two 8-pixel letters per 16-pixel cell, drawn on the fly; names in the commentary stay in capitals | the fonts have room for ~200 glyphs, far fewer than English letter pairs need |
| Card list (League / Tournament): 観戦しない / 観戦する / 試合中 = Skip / Watch / Playing; results "13m 9s" over the finishing hold in 8 capitals (translation/finishes.tsv: ROLL-UP, BODY PIN, GENBAKU, HALFCRAB, ...) | the button and the 8x8 result font hold 8 cells |
| 組 after a tag team's names (winner screen) = "Team": "OZAWA  YUKI  Team" | the names come first; nothing follows on the line |
| ブリッド = "Hybrid" (endings 2 and 7: Hybrid Breakers, Requiem of the Hybrid) | user's choice, 2026-10-23 |
| Match strategy icons: BIG RNG END FIN CTR KO OUT PIN | the 32x16 icon fits three bold letters; user chose these short forms from a mockup |
| Schedule help for drills: "Throw / Holds / Power / Hits / Air attack up." | the same words as the move tabs and status labels |
| Ring names and full names may start half a letter to the right; short names never do | names are drawn as letter pairs and the names font holds 191 of them; shifting some names lets them share pairs |
| Stats Up headers: Value / BP (要ＢＰ = BP needed) | short headers over narrow columns |
| Unreferenced script strings translated anyway | cheap; they are shown on the cut-content page ([HIDDEN_CONTENT.md](HIDDEN_CONTENT.md)) |

## What stays untranslated

All text is translated. Left in Japanese on purpose (artwork, user's decision 2026-10-23):

- the title logo, and the same logo repeated behind the main menu and the profiles (美少女レスラー列伝);
- the save slots' ticket picture (新日本女子プロレス, リングサイド 側 列 番, 6時半 試合開始);
- the copyright line on the title screen (the original novel's author and publisher).
