# Champion Road: how the mode works

Champion Road is the game's career mode. This document covers how it moves forward, what training and
matches do, and how to reach each of the nine endings. Findings are marked *from the code* (read
from the event script or the 65816 code) or *verified in game* (seen in Mesen). Addresses and the
script listing tool are described in [TECHNICAL.md](TECHNICAL.md); `tools/events.py listing 888000 OUT`
prints the whole Champion Road script with its English.

## Contents
- [The shape of the mode](#the-shape-of-the-mode) · [New game](#new-game) · [Training](#training)
- [Matches](#matches) · [Endings](#endings) · [Choices that matter](#choices-that-matter)
- [Testing](#testing) · [Open questions](#open-questions)

## The shape of the mode
- **The story is gated by rating, not time.** Each chapter repeats "series" (a schedule of training
  weeks plus a card of matches) until the heroine's rating reaches a target: 440 at the start, up to
  850 late on some routes. The script stores rating ÷ 10 (`$8D:C48B`) and tests it after each series.
  *(verified in game)*
- Some series are **must-win**: a title or special match that repeats until the heroine wins it.
  Every other match only costs time; there is no game over.
- **Choices** between series move the heroine between promotions: Shinjo (Regulars and Rebels),
  World Joshi, IWWF (New York), USWA (Dallas), AAC (Mexico) and SWA.
- **The finale** on most routes is the Athena Climax league, then the IWWF Heavyweight title. Winning
  the title plays the ending the route has earned (route value v39, `$88:D6EE`).
- When the card is announced, the coach's comment reads the card's win odds (v06): under 3 "a
  wrestler on a different level", 3 to 5 "seize the flow", 6 and up "give it your all".

## New game
| Heroine | Start rating | Factions | Notes |
|---|---|---|---|
| Yukiko Shinzaki | 440 | Shinjo Regulars, Shinjo Rebels | Many choices are made for her; endings 1 and 2 |
| Haruka Yamada | 440 | all four | |
| Kazuko Hada | 440 | all four | some partners and cards differ |
| Kayo Ozawa | 440 | all four | |
| Yuki Katsuragi | 436 | all four | fixed ring name; own opening (masked debut, Hulk Hongo); only heroine with ending 9 |

| Faction | Route value | Default ending |
|---|---|---|
| Shinjo Regulars | 1 | 1 |
| Shinjo Rebels | 2 | 2 |
| World Joshi | 21 | 3 (branch point for 4, 5, 6, 7, 8) |
| Freelance | 30 | none: becomes 2 when she joins Shinjo, or a route abroad |

## Training
Each wrestler's record is 256 bytes at `$7E:832A + id × 256`. The schedule screen's day types are
handled at `$84:DFD6` (21 entries). *(from the code; one week checked in game)*

| Activity | Trains | Fatigue |
|---|---|---|
| Weight Training, Sparring, Running, Breakfalls, Dash Drills | Str, Dex, Sta, Rec, Spd | +8 |
| Practice Match | Guts (by result) | +8 |
| Offense / Defense Drills (pick types) | attack or defence of each type picked | +6 |
| Learn Moves, Move Difficulty, Finisher | moves | +8, +3, +5 |
| Sleep | HP + 3/16 to 5/16 of max | −5 |
| Play | HP + 1.5/16 of max | −70 / −50 / −30 |

- A session adds experience; 256 experience = +1. Base stats cap at 16. Attack and defence cap at 31
  each, and a type's attack + defence at 32 (raising one past that lowers the other).
- Experience per session by rating (best / middle / worst grade): under 550: 145/95/45; 550-699:
  135/85/40; 700-899: 125/75/35; 900-1099: 115/65/30; 1100 and up: 100/52/25 (`$83:F198`).
- Grade: random 0-63 + fatigue (+50 for a drill whose type's attack + defence is already at least
  twice its base stat: Throw-Str, Holds-Dex, Power-Sta, Hits-Rec, Air-Spd). 66 or less is best, up to
  99 middle, above that worst. Fatigue 0-3 always gives the best grade; average gain at the lowest
  tier falls from 145 (fatigue 0) to 124 (30), 97 (50) and 46 (99).
- Practice Match Guts: beating someone rated 100+ / 50+ / less above you gives 255 / 180 / 105;
  losing to someone 300+ / 150+ / less above gives 128 / 64 / 16.
- **Rating** (`$8A:8000`) = 4 × (all attack/defence values + base stats + a move bonus per category
  + the finisher's level). The move bonus for 1-6 moves in a category is 5, 10, 14, 17, 19, 21: the
  first move in each category is worth +20 rating.

**Getting stronger fast:** train while the rating tier is low; keep fatigue under about 40 with one
Play a week; raise base stats before drills (they lift the drill cap); fill each type's attack +
defence to 32 (that pool is worth up to 640 rating); learn one move in every category early.

## Matches
From a study of the match code (`$84:8B1D` referee task, `$84:91DA` exchange, `$80:E038` damage).

- **Only HP ends a match**: a 3-count or a submission. There is no count-out; the Return value only
  sets how long a brawl outside lasts. *(from the code; a 3-count verified in game)*
- **Pins** work only near zero HP: below 1/16 of max HP, and at HP 4 or less the pinned wrestler still
  kicks out with chance Guts/128 (2/3 of that in tag matches). Rolling Clutch Hold pins at 2/16.
- **Submissions** need the targeted part (HP, arm or leg) under about 3/16; escapes use Dex.
- **Move choice**: the Logic screen's 8-slot pattern is read **bottom-up**. The bottom row is used
  while the opponent is fresh, the top rows when she is nearly beaten (row = opponent's HP rank / 2).
  The row's type is picked about half the time. The move used is the strongest one whose level is
  below 16 − the opponent's HP rank + a tier from `attack(type) − opponent's defence(type)`.
- **Initiative** each exchange: the same attack − defence difference, the move's modifier, a
  comeback bonus after taking 3+ moves in a row, and a random 0-15.
- **Damage** = the move's damage at its level × (1 + spirit/128) + attacker's Str. Spirit (SPR)
  builds when you take damage and drains when you deal it, so a beaten-down wrestler hits back up to
  twice as hard.
- **Logic style** (Safe, Even, Fight, Rush) is not read in a watched match. It only changes the
  random swing when a match on the card is auto-resolved.
- **Strategies** (A/X/Y/B, set on the Logic screen; the CPU never uses them):

| Strategy | Effect |
|---|---|
| Big 大技 (BIG) | moves two tiers bigger, sooner |
| Range 間合 (RNG) | never starts a lock-up; −2 initiative; −4 damage dealt; HP recovery ×4/3 |
| Endure 忍耐 (END) | −8 initiative; damage taken ×3/4; more spirit from damage |
| Finish 必殺 (FIN) | 50% per exchange to use the finisher (+20/+40 bonus); at most two, the second after about 3:20 |
| Counter 返し (CTR) | −2 initiative, and **raises the opponent's chance to counter your attacks** by 32/128 (as coded; verified in the code for both sides) |
| KO 一撃 (KO) | +5 damage on every hit; +24/128 to counter when defending |
| Outside 場外 (OUT) | stay outside 2 actions longer; +4 initiative outside |
| Pinfall フォール (PIN) | when pinned, you mash the button to kick out instead of an automatic roll |

**Winning matches:** raise the attack of the types your logic pattern uses; put the types with your
strongest, highest-level moves in the top rows; never leave a type with no moves (it becomes a
6-HP poke); KO is the best all-round strategy, Big once the opponent is past half HP, Finish to close;
avoid Counter. In tag matches the Assist style breaks up pins fastest and adds to the win odds.

## Endings
The ending is chosen by the route value when the IWWF Heavyweight title is won (`$88:D6EE`; ending 9
at `$88:90C8` for Yuki with route 98). Every ending then shows a shared epilogue (a girl inspired by
the champion's win) and the staff roll.

| # | Route | How to get it | Status |
|---|---|---|---|
| 1 | 1, 119, or any other value | Shinjo Regulars and stay on the Shinjo line; or "Move to AAC" on the three-way menu, then the AAC tag titles, M Sand and training with Uehara | *verified in game*: Yukiko / Regulars (all first options); Haruka / World Joshi, three-way menu "Move to AAC" (route 119) |
| 2 | 2 | Shinjo Rebels; or Freelance, then in Mexico take Yukiko's offer ("Shinjo, huh..." or "Guess I'll join you") | *verified in game*: Yukiko / Rebels; Haruka / Freelance (Yukiko's offer); Yuki / Rebels after moving to World Joshi |
| 3 | 21 | World Joshi; beat Tsurumi in the grudge match; when World Joshi folds, "Go to Shinjo" | *verified in game*: Haruka / World Joshi |
| 4 | 101 | World Joshi line; lose the grudge match against Tsurumi: she resigns and is pushed into the SWA; EX Tag with Hongo, the Athena, then the title against Ichigaya | *verified in game*: Haruka / World Joshi, grudge match lost |
| 5 | 113 | World Joshi line; beat Tsurumi; when World Joshi folds, "Go to the USWA" | *verified in game*: Haruka / World Joshi |
| 6 | 118 | Reach the IWWF tag titles in New York: "Move to IWWF" on the three-way menu, or (non-Yukiko, Yukiko beat Risako) "I want the world too" then "It's got to be the IWWF" | *verified in game*: Haruka / World Joshi: no Mexico, refuse Ryuko, accept the President, decline renewal, "Move to IWWF" |
| 7 | 122 | Reach the USWA tag titles in Dallas: "Move to USWA", "Maybe the USWA", or "Going home is..." when Japan calls her home from the USWA; ends with the EX Tag alongside Chaos (no Athena) | *verified in game*: as for 6, "Move to USWA" |
| 8 | 150 | World Joshi; refuse Ryuko's tag offer and then the President's pairing ("Me... with her..."); she quits, teams with Maria in Mexico and becomes Dark Star Chaos | *verified in game*: Haruka / World Joshi: no Mexico, refuse Ryuko, refuse the President |
| 9 | 98 | Yuki only, Shinjo: stay in Japan, join the Revolutionaries, beat Risako, "Go to Mexico", beat M Sand (Blade Uehara), then win through the Athena | *verified in game*: Yuki / Rebels: "......", "For me....", "Overseas, huh...", "Sounds like fun", "Go to Mexico" |

The three-way menu (Move to IWWF / USWA / AAC) comes after declining World Joshi's contract renewal
("The promotion war...") or, as a freelancer, declining Shinjo's offer ("I'm sorry").

## Choices that matter
| When | Options | Effect |
|---|---|---|
| After the Rookie of the Year tournament | I'll go! / ...... | IWWF study abroad or stay in Japan (Yukiko always goes to Mexico) |
| After the Dadarne match (only if lost) | I think I'll go back / Not yet... | Back to Shinjo, or stay in the IWWF |
| Yoshimi's invitation | You're right / For me.... | World Joshi or stay at Shinjo |
| World Joshi, after beating Kozuki | Mexico, huh... / Hmmm... | AAC or stay (losing that match skips the offer) |
| Ryuko's tag offer, then the President's pairing | accept / refuse | Refusing both: the Chaos route (8). Yuki gets a contract renewal instead |
| Contract renewal | re-sign / "The promotion war..." | Declining opens the three-way menu |
| Freelance in Mexico: Yukiko's offer | Shinjo, huh... / Help Yukiko? Well... | Join Shinjo (ending 2), or a second menu: World Joshi / stay with the AAC |
| Freelance, AAC juice test | Grrrgh.. / All right | Clean or heel AAC run; drinking skips Yukiko's tag offer |
| Revolutionaries invitation | Sounds like fun / Sorry, but... | Join the challengers to Risako (needed for ending 9) |
| After beating Risako | Go to Mexico / Train harder in Japan | Mexico leads to M Sand |
| If Yukiko beat Risako instead | I'll be Shinjo's ace / I want the world too, then IWWF / USWA | Stay, or the IWWF (6) / USWA (7) tag titles |
| World Joshi folds | Go to Shinjo / Go to the USWA | Ending 3 or ending 5 |
| Tsurumi grudge match (a match) | win / lose | Losing leads to the SWA and ending 4 |

## Testing
`tools/events.py crtest OUT.smc` makes a test image (never for release) that opens every rating gate
and skips the weekly schedule and the matches, so the story runs as scenes and choices. Each skipped
series' result comes from WRAM `$7E:5E80`+ (one byte per series, 0 = won), and with `$7E:5E42` set to
1 the choices are answered from `$7E:5E00`+ (one byte per choice, 0 = first option) instead of the
menu. Driven in Mesen, a whole route takes 10-20 minutes; every ending above was reached this way
(the route recipes in the table are the choice lists used).

## Open questions
- Scenes that nothing in the script references (an Izumi Yoshihara karate scene `$93:ABA0`, a
  monologue to the heroine's mother `$93:ADA5`, a Greta/Ryuko feud `$93:AE79`, and more) are cut
  content: the script has no computed jumps, so they cannot be reached
  ([HIDDEN_CONTENT.md](HIDDEN_CONTENT.md)).
- Auto-resolved card matches use the Logic style; the exact formula around `$8C:A52D` is only
  sketched.
