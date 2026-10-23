# Hidden content

Unlockables, debug features, button codes and unused content, each marked *verified in game* or
*from the code*. The main menu codes are listed on GameFAQs' cheats page (checked by hand; the page
blocks automated fetches, so the match debug mode and the smaller leftovers have not been compared
with it). A Japanese fan wiki (ジョシカクアーカイブス) notes the hidden wrestlers in the World Circuit;
no other published source was found.

## Main menu button codes
Entered on the main menu (Champion Road / Exhibition / ...), one button at a time; the last step is
L and R pressed together. The listeners are started with the menu at `$8A:8577` and compare new
presses (`$0AFC`) against the lists below. A sound plays when a code is accepted.

| Code | Effect |
|---|---|
| Up, Up, Down, Down, Right, Left, Right, Left, L+R (`$8A:86D4`) | Debug flag `$7E:CAB2` = 1: every Champion Road rating gate is open (the script sees rating ÷ 10 as 255, `$8D:C4A6`); the Exhibition roster grows from 59 to 63 wrestlers |
| Up, Left, Down, Right, Up, Left, Down, Right, L+R (`$8A:873A`) | Debug flag = 2: as above, plus a chapter number in the top-left corner (Left/Right change it, `$7E:CAB4`); Champion Road then starts at that chapter, and the heroine starts with every base stat and every attack/defence value at 16 (`$8D:C37D`) |
| Right, Left, Right, Left, then A+B+X+Y together (`$8A:878E`) | Clears the save data's signature (`$8C:D344` writes 0 to SRAM `$70:0000` and `$70:1000`); on the next check the saves are re-initialised. **This erases the saves.** *(from the code; not tried)* |

Codes 1 and 2 *verified in game* (English build, Mesen): the flag, the 63-wrestler list (`$7E:F071`)
and, for code 2, chapter 6 starting with route 150 and the stats at 16.

**Hidden wrestlers** (ids 60-63, on the Exhibition list only with a debug flag): Megumi Muto, Chigusa Yuki, Reiko
Kanamori, Narumi Otaka. The first two are the girls in Champion Road's shared epilogue. All four
names are in translation/names.tsv. Without any code they are the opponents at the World Circuit's
last stop: the circuit's 13 opponent teams (`$8C:FD1C`, built into `$7E:CB94` by `$8C:FAB6`) always
end with ids 60-63, so every World Circuit finishes against them. *(verified in game: the stop list in
WRAM during a World Circuit run reads 60 61 62 63 for stop 13)* They cannot join a team (the 7 teams are fixed), and they share
one empty profile.

**Chapters** (code 2; the number is v00, dispatched at `$88:803A`):

| # | Starts at | Route |
|---|---|---|
| 0 | the normal start | by faction |
| 1 | `$88:8687` back in Japan after Komatsu, Yoshimi's invitation | 2 |
| 2 | `$88:891F` World Joshi before the war with Shinjo | 21 |
| 3 | `$93:8A76` World Joshi, the World Tag League offer | 21 |
| 4 | `$88:89B7` Yoshihara joins Shinjo | 21 (v34 = 30) |
| 5 | `$88:87C9` back from hospital, World Joshi wants her | 21 |
| 6 | `$88:9176` AAC Tag champions with Chaos | 150 |
| 7 | `$88:90C8` the ending itself | 150: ending 8 |
| 8 | `$88:90C8` the ending itself | 118: ending 6 |
| 9 | `$88:8CA3` after the Tsurumi grudge match | 101 |
| 10 | `$88:83AF` New York, after the Dadarne match | 1 |
| 11 | `$88:8BF7` the M Sand title match | 1 |
| 12 | `$93:9521` the Athena Climax | 119 |

Other things the debug flag changes *(from the code)*:
- World Circuit result list (`$8C:8BBF`): normally it shows matches only while one of the player's
  team is in them; with the flag every match's result is listed. `$8C:8B16` on the same screen sets
  `$7E:D04C` to 0 instead of 1 (meaning not checked).
- Weekly schedule (`$8B:8000`): the screen's starting state `$7E:CAA6` is 0 instead of 2 (meaning
  not checked).
- Roster picker (`$8E:B838`): with flag 2 the wrestler data is loaded from starting set 2 instead of
  set 3 (`$8F:8173`).

## Unlocks
There are none. Finishing an ending, the World Circuit, the League or the Tournament writes nothing
outside that run's save slot (all save code is at `$8C:D340`-`$8C:DB80`). *(from the code)*

One save byte outside the slots, `$70:0004` (`$7E:CAD0`), looks like the remains of planned
unlockable options: it is loaded at the main menu and written back by the System screen, but nothing
ever sets it. Its bits 0 and 1 add two rows below Message on the System screen (`$8E:E831`); the
rows have no label and no function (A falls through to the Music handler). *Verified in game* with
the byte poked to 3: the cursor reaches two invisible rows. Only editing the save data shows them.

## Match debug mode (move test)
On the title screen, hold **L+R on controller 2** while the logo finishes sliding in (`$80:D1FB`,
checked once, about 190 frames after the title appears); the title then waits for **A+B+X+Y together
on controller 1** (`$80:D2BE`), plays a sound and sets `$7E:F06D` = 2. In every match after that:
- a move number and the developers' own 8-letter move label are drawn over the left name panel
  (`$84:A8BB`, labels at `$84:A983`: "NO USE!!", "ARM WHIP", "SIDE SP", "W ARM SP", ...);
- Down/Right and Up/Left step through moves 0-`$71`;
- holding **R** makes the wrestler use that move when she next picks one (`$84:967D`).
*Verified in game* with the flag set directly (Mesen drives controller 1 only): "00 NO USE!!",
then "03 W ARM SP" after three presses. The flag is cleared when the title sequence restarts
(`$80:CBF8`).

## Smaller leftovers
- **Attract demo:** while the demo plays (`$80:D302`, started from the title flow), holding L+R keeps
  it looping and holding Select ends it (`$80:D440`/`$80:D44C`). *(from the code)*
- **Sprite layout tool:** a complete screen at `$84:CB95` (graphics from `$A0:8000`, a cursor, a
  table of 128 eight-byte entries at `$7E:EC5B`; Select+L+R clears the table, Start+Select leaves)
  that nothing starts: an unused developer tool. *(from the code)*
- **Input recorder:** the joypad routine can record pad 1 into a table at `$80:F000` (`$80:81CA`)
  and play it back (`$80:81A2`), used for the demo; recording writes into ROM space, so it does
  nothing on a cartridge. *(from the code)*

Every read of the joypad values (`$08FC`/`$08FE` held, `$0AFC`/`$0AFE` new, 162 sites) was checked;
the codes above and on the main menu are the only special inputs.

## Unused moves, quotes and pictures
*(from the code unless marked)*
- **Four moves** have complete records (all strikes) but no name, and no wrestler, learn list or code
  uses them; only the match debug mode can pick them. Developer labels: `$3D` HARITE (open-hand
  slap), `$3E` PUNCH, `$3F` KICK, `$47` TECCHU (ring-post attack, the highest bleed chance of any
  move). Every move that has a name is used. RAIDEN and SHINDEN belong to Blizzard Yuki alone and
  WEAPON ATTACK to the heels; none of the three can be learned.
- **35 winner's quotes** are never shown. The quote depends on the winner's personality type
  (template +`$64`, read at `$84:BF86`), and every wrestler has type 0-4, so types 5-11 never occur:
  seven personalities of five lines each, among them an "Ohohoho!!" rich girl, a sadist and a
  foreigner in broken Japanese. They are translated in translation/text/winner.txt.
- **Scene picture 09** (`$BC:8000`, a street of shuttered shop fronts with a pink awning) is never
  used by the script's picture opcode (`$44`), which uses every other picture. *Seen in the emulator*
  with a test build.
- Two screen labels have no pointer anywhere: League 「Xボタンで能力値」 ("X: Stats") and Logic 「気合」
  ("Spirit"). Both are translated.
- No wrestler, promotion or faction is hidden beyond ids 60-63; the hometown list simply holds every
  prefecture, 16 of them unused.

## Unused story content
Champion Road and the World Circuit are the only two event-script entry points (`$88:8000`,
`$93:B6AF`, set at `$8D:C2EF`/`$8D:C405`); the only other writes to the script pointer restore a
saved position. A scene is shown only if a script instruction jumps or calls to it, and the script
has no computed jumps. So the content below cannot be reached in normal play or with the codes
above. *(from the code)*

Of the 3,413 dialogue strings, 2,894 are reachable. The rest:

- **246 strings in 16 scene subroutines that nothing calls** (`$88:9B4F`, `$88:9D25`, `$88:9FDC`-
  `$88:A11B`, `$88:A9F8`, `$88:AADE`, `$88:B943`, `$88:C33A`, `$88:C8F5`, `$88:CC70`, `$88:DD96`-
  `$88:DEDF`, `$88:E5FA`, `$88:EC56`, `$93:ABA0`, `$93:ADA5`, `$93:AE79`, `$93:B5AE`). They set
  variables no reachable code sets (v34 = 27, 28, 29, 86; v3E = 86; v36 = 9) and answer tests that
  never come true (the Dadarne scene's `v3E == 86`), so they are pieces of storylines that were cut
  or rewired:
  - an alternate USWA arrival in Dallas (promoter Peil; Yoko Hayashi is there too) and a Dallas
    "lost again" scene;
  - Tsurumi passing through Dallas with the EWA Tag belts she won with Ryuko, and an AAC "stay or go
    back to Japan" choice after winning a belt there;
  - Ryuko musing about World Joshi's future, foreshadowing a defection (tested by `v37 == 61`);
  - the Chaos route's extra scenes: the heroine secretly wrestling in Chaos's mask while Maria is in
    hospital, Dreck growing suspicious, Maria and the heroine moving to the IWWF, a Dadarne challenge;
  - Beauty Ichigaya storming the ring after the heroine's title match;
  - two introductions of Izumi Yoshihara (a Shinjo gym version and a standalone sparring scene in
    which she beats the heroine and leaves a message for Risako);
  - Yuki's monologue to her absent mother, who left "to fight Eric the karate master";
  - a homecoming after beating Greta in the USWA, Ryuko belittling it, and Choko setting up their
    match; plus the promoter's lead-up to the Greta match;
  - a coach scene in which Ichigaya has taken Dadarne's belt, so the shot becomes the US title.
  The Greta/Ryuko homecoming (`$93:AE79`) is still called from a block at `$88:9084` (Yuki only,
  followed by a special match), but that block is only reached through dead jumps at `$93:9515`-
  `$93:951D`, which sit after an unconditional jump: the route was rewired to the Uehara chapter.
- **273 strings with no code at all**, next to reachable text in the same banks: lines from scenes
  whose code was removed (Toshimi Minami introductions, a Revolutionaries briefing, "Shinobu Echigo
  joined the company", Maria's hospital and letter scenes, match-card briefings, and others).

All of this text is translated with the rest of the script (translation/script/), so it is ready if
it is ever restored. A test image could call any of these scenes from the script.
