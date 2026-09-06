<!--
  How the GAME works — the general rules a judge reasons from.

  These are the rules that answer questions no ruling was ever written for. A
  ruling about a 2011 card and a question about a 2026 card are usually the
  same general rule wearing different names, so the general rule comes first
  and the ruling confirms or narrows it.

  Everything here must be checkable against the rulebook, a tournament
  handbook, or a Compendium ruling. If two judges reading those would disagree,
  it is not a mechanic: put it in exceptions.md instead.

  Format: one `## ` section per rule. The heading is what keyword search
  matches on, so name the thing people ask about, not the chapter it lives in.
  `Source:` is for you when you re-check this in six months; it is not served
  to users. `NEEDS REVIEW` marks a sentence inferred from the sources rather
  than stated by them; it is served, flagged `unreviewed`.
-->

## Order of an attack — the attack steps

Attacking has a fixed order. Most disputes about "which happens first" are
settled by it.

1. Choose the attack and check its Energy cost against the Energy attached.
   Announce it. The Energy cost is the ONLY thing you need to declare an
   attack. Anything the attack's text tells you to do — discard Energy, discard
   cards, flip coins — is part of the attack's effect, not a cost, and does not
   stop you from declaring it.
2. Apply effects that could alter or cancel the attack, such as "if the
   Defending Pokémon tries to attack, flip a coin; if tails, that attack does
   nothing." Such an effect belongs to the Pokémon it was placed on. If that
   Pokémon has left the Active Spot since, the effect is gone.
3. If the attacker is Confused, flip for Confusion now.
4. Make every choice the attack asks for (which Pokémon, which cards).
5. Do what the attack requires in order to be used, such as a coin flip that
   decides whether it does anything.
6. Apply effects that happen before damage; then calculate and place the
   damage; then do the attack's other effects — discards, Special Conditions,
   switching, healing.
7. Damage is calculated in this order: the printed base damage, then modifiers
   on the attacking Pokémon, then Weakness, then Resistance, then modifiers on
   the Defending Pokémon, then damage counters are placed. If the attack
   places damage counters directly, none of this applies — no Weakness, no
   Resistance, no "takes less damage" effects.

Consequences of step 6 that come up constantly:

- An Energy the attack discards is still attached while damage is calculated,
  so an Ability or effect that checks attached Energy during damage sees it.
- After damage is placed, that Energy is gone, so anything that reacts to the
  attack afterwards (an Ability that triggers when the Pokémon is damaged or
  attacked) sees a Pokémon without it.

After the attack's effects are done: resolve Abilities that trigger on the
attack, then check Knock Outs for every Pokémon at once, resolve anything that
triggers on a Knock Out, take Prize cards (the opponent of the attacking player
takes first), replace Knocked Out Active Pokémon, then check win conditions.
Effects that say "at the end of your turn" or "after your attack" happen after
that, and only then does Pokémon Checkup begin. NEEDS REVIEW — the post-damage
order is assembled from rulings, not stated in one place in the rulebook.

Source: rulebook, Full details of attacking (steps 1–7); Compendium rulings on
Knock Out and end-of-turn timing (e.g. Sunny Bloom, 1738).

## Effects of attacks end when the Pokémon leaves the Active Spot

When an Active Pokémon moves to the Bench, all effects of attacks on it go
away. This is true for effects the opponent's attack put on it ("can't retreat
during your next turn", "if this Pokémon tries to attack, flip a coin") and for
effects its own attack put on it ("during your next turn, this Pokémon's
attacks do 80 more damage"). If it later returns to the Active Spot, those
effects do not come back.

Evolving or devolving a Pokémon also removes the effects of attacks on it, along
with its Special Conditions.

The distinction that matters: an effect is something placed on a Pokémon. Text
that only looks at what happened earlier ("if this Pokémon used this attack
during your last turn") is a check of game history, not an effect, and moving
to the Bench does not erase history. Read the card: "during your next turn
this Pokémon…" places an effect; "if this Pokémon used X last turn" checks
history. Rulings treat these differently.

Source: rulebook, Full details of attacking, step B; rulebook Glossary,
devolve; Compendium meta-rulings on game-state checks (1115, 1610).

## Special Conditions — who can have them and how they end

Only the Active Pokémon can be Asleep, Burned, Confused, Paralyzed or
Poisoned. A Pokémon recovers from ALL Special Conditions when it moves to the
Bench (by retreating or by any card effect), when it evolves, and when it is
devolved. Damage counters stay; the Special Conditions do not.

Asleep, Confused and Paralyzed are shown by rotating the card, so only one of
those three can apply at a time — whichever happened last replaces the others.
Poisoned and Burned use markers and stack with anything. A Pokémon can be
Burned, Paralyzed and Poisoned at once.

Only Asleep and Paralyzed prevent retreating.

Source: rulebook, Removing Special Conditions; rulebook Glossary, devolve.

## Pokémon Checkup

Checkup happens BETWEEN turns — after one player's turn ends and before the
next begins. It belongs to neither player's turn.

Order inside Checkup: Special Conditions resolve as Poisoned, then Burned, then
Asleep, then Paralyzed. Abilities, Trainer cards and anything else that says it
happens "during Pokémon Checkup" or "between turns" are applied in the same
step. The player whose turn is NEXT decides the order of those other effects —
not the owner of the Pokémon. All Special Conditions happen at the same time
and cannot be split around an effect: you may apply one Ability, then all
Special Conditions, then another Ability, but not Poison, then an Ability, then
the Sleep flip.

Knock Outs are checked at the END of Checkup, after every effect and Special
Condition has been applied. Two Pokémon can be Knocked Out by Poison at the
same moment; neither one "goes first".

A Knock Out during Checkup did not happen during either player's turn. An
effect that triggers on "Knocked Out during your opponent's turn" does not
fire for it. NEEDS REVIEW.

Checkup is a between-turns step, so it only happens when another turn follows.
When a game ends at the end of a turn — the last extra turn of a timed round —
there is no next turn and no Checkup, so between-turns effects do not apply.
NEEDS REVIEW — a consequence of the definition, not a sentence in the rulebook.

Source: rulebook, Pokémon Checkup; rulebook, Other Effects; Compendium 2302
(2026-02-19: the player whose turn is next orders Checkup effects).

## Both players win at the same time — tiebreaker game

Win conditions are checked at the same time for both players. Taking your last
Prize card and your opponent having no Pokémon to put in the Active Spot are
both win conditions. Prize cards from simultaneous Knock Outs are taken at the
same time; nobody "gives up" a Prize first.

If both players meet a win condition at once, count them. A player who meets
more win conditions than the opponent wins — for example, both take their last
Prize card, but only one of them can put a new Active Pokémon in play: the one
who can continue wins. If the count is equal, play a tiebreaker game: a new
game, set up as normal, and the first player to take a Prize card wins it. At a
tournament the round timer still applies to the tiebreaker; the tournament
handbook says what happens if time runs out during it.

Source: rulebook, What if both players win at the same time?; rulebook, What's
a tiebreaker game?; Compendium 2240 (2025-11-06, Cursed Blast with one Prize
each).

## Do as much as you can

If an attack, Ability or Trainer card tells you to do something and you cannot
do all of it, do as much as you can. "Discard 3 Energy" with 2 attached
discards 2. "Search your deck for 7 cards" with 5 left searches 5. An attack can
be declared whenever its Energy cost is paid, even if none of its effect can
happen — you still do the damage.

Trainer cards with "If you do": a card such as "Switch in 1 of your opponent's
Benched Pokémon to the Active Spot. If you do, switch your Active Pokémon with 1
of your Benched Pokémon" can be played whenever its FIRST instruction can be
carried out. The part after "if you do" is conditional: if you have no Benched
Pokémon of your own, that part simply does not happen and the card was still
legally played. A card may not be played only when NONE of its effect could
happen (for that example: the opponent has no Benched Pokémon).

Two limits:

- Text that says "if you can't, this attack does nothing" (or that makes the
  effect a condition of the attack) means what it says.
- Public knowledge. If it is public knowledge that an effect cannot possibly
  do anything — search your deck for a card when all four copies are in your
  discard pile or in play, put a Pokémon on a full Bench — that part of the
  effect is not performed at all, and you do not get to look through your deck.
  The discard pile, the Bench and cards in play are public; your deck and hand
  are not. An attack with such an effect can still be declared (it may do
  damage); an Ability or Trainer card whose whole effect is publicly impossible
  cannot be used. NEEDS REVIEW — the Ability/Trainer half is inferred from
  rulings about attacks.

In a Limited format (a Prerelease), a deck may hold more than four copies of a
card, so "all four are in the discard pile" is not public knowledge that none
remain.

Source: Compendium rulings 2356, 2164 (as much as you can); 361, 362, 1835
(public knowledge); 2139 (Prerelease, more than four copies).

## Reminder text in parentheses

Text in parentheses on a card restates a normal game rule. It adds no
condition and takes nothing away: "(after your attack)" on an end-of-turn
effect tells you when it happens, not that you must have attacked; "(that
Pokémon can't evolve this turn)" restates the normal evolution rule. Because it
only restates the normal rule, an Ability or effect that changes the normal
rule wins over the reminder. NEEDS REVIEW — the "(after your attack)" reading
is an application of the ruling, not its wording.

Source: Compendium 2327 (2025, Strange Timepiece and Boosted Evolution).

## Evolving a Pokémon

A Pokémon cannot evolve on the turn it comes into play, and cannot evolve on
the first turn of the game. Evolving removes the Pokémon's Special Conditions
and the effects of attacks on it; damage counters stay. The evolved Pokémon
cannot use the attacks or Abilities of its previous stage unless a card says so.

Playing a Pokémon with Rare Candy is not evolving — it puts the Stage 2 into
play directly. The Pokémon it replaced was in play, so the "came into play this
turn" restriction is judged on the Pokémon that is now there.

An Ability that lets a Pokémon evolve on the turn it came into play changes the
general rule, but a card's own printed restriction ("you can't use this effect
on a Pokémon put into play this turn") is not the general rule — it is that
card's condition, and it still applies. NEEDS REVIEW.

Source: rulebook, Evolving; rulebook, Turn Actions.

## Regulation marks and format legality

A card's legality follows the regulation mark printed at its bottom left, not
the expansion it came from. A card from a recent set can still be illegal, and
a card from an old set can be legal if it was reprinted with a current mark.
Basic Energy cards are legal in every format regardless of printing.

In-person events and digital play rotate on different dates. In 2026 they were
fifteen days apart, so an event inside that window had two different right
answers.

This is answered by a query, not by this file — see server/legality.py.

Source: 2026 Standard Format Rotation Announcement, pokemon.com; TCG
Tournament Handbook, Constructed Tournament Formats.

## "Up to", "any amount", "any number" — how many you may choose

For effects of ATTACKS, "up to X" lets you choose any number from 0 to X. For
other effects — Trainer cards and Abilities — "up to X" means at least 1. One
exception: an effect that searches your deck or discard pile for any card at
all, without saying what kind, requires you to choose at least 1.

"Any amount" or "any number" — "discard any amount of Energy from this
Pokémon" — always lets you choose 0. An attack that does damage "for each card
you discarded in this way" can therefore be declared with nothing discarded; it
does 0 damage.

Source: rulebook, What's the difference between "up to" and "any amount"?;
Compendium 2301 (2026-02-19).

## Effects on a Pokémon versus effects on the player

Some attack effects are placed on a Pokémon ("the Defending Pokémon can't
retreat", "this Pokémon's attacks do 80 more damage"). Others are placed on the
player or on the game ("your opponent can't play Item cards during their next
turn", "Pokémon that have 2 or less Energy attached can't attack — this
includes new Pokémon that come into play").

Protection that reads "prevent all effects of attacks done to the Pokémon this
card is attached to" stops only the first kind. An effect that applies to all of
a player's Pokémon, or to Pokémon that enter play later, is not done to that
one Pokémon, so such protection does not stop it, and moving the attacker to
the Bench does not end it. The card's own words decide: if the effect names
"the Defending Pokémon" or "this Pokémon", it sits on that Pokémon and ends
when that Pokémon leaves the Active Spot.

Source: Compendium 2055 (2024-11-07, Frigid Fangs stays when Walrein is
benched); Compendium 1818 (2023, "the Defending Pokémon" effect ends when the
Active changes); Mist Energy card text.

## Using a Supporter's effect through an attack is not playing it

Attacks that discard a Supporter card and use its effect ("use the effect of
that card as the effect of this attack") do not PLAY the Supporter. So the
restrictions on playing a Supporter do not apply: you may already have played a
Supporter this turn, you may be under an effect that stops you playing
Supporters, and a "you can play this card only if…" condition printed on the
Supporter is a condition of PLAYING it, not of its effect — so a Supporter that
says "You can play this card only if your opponent has 2 or fewer Prize cards
remaining" has its effect applied through the attack even when the opponent has
more. The verdict for "does the effect still apply if the play condition is not
met?" is YES. You still do everything the effect itself says, and you still pay
costs that are part of the effect (a card that says "discard your hand, then…"
still discards your hand).

Source: Compendium 2226, 2225 (2025-09-25, Supernatural Shapeshifter); 1802
(2023, Primate Acting); 491 (2019, Impersonation: costs still paid); 2376
(2026-06-04).

## An errata changes every printing of the card — old printings stay legal

When a card receives an errata, every printing of that card — by name — is
played with the errata text, however old the printing and whatever it says on
its face. A printing whose printed text differs from the current text is
therefore still the same card, still legal wherever the current printing is
legal, and is played as the current text reads. The handbook's "functionally
identical" test for reprints is applied to the text the cards are PLAYED with —
after errata — not to the ink. So an older Quick Ball whose printed effect is
completely different is legal in Standard and is played as the current Quick
Ball, because Quick Ball has an errata. `lookup_card` returns the errata under
`errata` and the governing text; the printed text is what the player is
holding, not what is played.

Timing of reprints: a new printing of a card that is already legal in the
format (including alternate and full-art versions) is playable as soon as the
player has it — even before the new expansion's official release, for copies
obtained during its Prerelease window — provided the name is identical and the
text functionally identical. Only genuinely NEW cards wait for the expansion's
legality date.

Source: TCG Tournament Handbook, Reprinted Cards in the Standard & Expanded
Formats; Compendium errata list (e.g. 1128, Quick Ball, 2020-01-09); the Super
Rod exception in exceptions.md.

## Deck search — what a player may do while searching

Nothing in the rules stops a player from looking through their whole deck,
arranging or sorting the cards while they search, or counting what is left, as
long as the search is one the game allows. What the rules require is what
happens after: the deck must be thoroughly randomized before play continues,
and the search must fit the pace-of-play limits for the event. A search used to
stall, or a deck that is not properly shuffled afterwards, is the infraction —
not the sorting. NEEDS REVIEW — inferred from the absence of any prohibition
plus the shuffling and pace-of-play rules; no handbook sentence says "sorting
is allowed".

Source: TCG Tournament Handbook, Shuffling & Deck Randomization; Penalty
Guidelines, Pace of Play.

## Deck list and physical deck — which one counts

At a deck check the deck LIST is the deck. Any difference between list and
physical deck is fixed by changing the physical deck to match the list, never
the other way round. A list with fewer than 60 cards, or with cards that are
not legal or cannot be identified, is made legal by adding Basic Energy of the
player's choice, and the physical deck is changed to match.

A list or deck that does not contain 60 cards is a Major deck legality
infraction; the recommended starting penalty is a Game Loss. The head judge
may de-escalate when the error clearly gave no opportunity for advantage, and
the guidelines list such deviations as legitimate — but the default is the Game
Loss, not the Warning.

Source: Penalty Guidelines, Pokémon TCG Deck Legality; Penalty Guidelines,
Deviations from Recommended Starting Penalties.

## Tardiness clause — late players and time

A player who was late to the match, or left it without a judge's permission,
loses the match if it is still unresolved when time is called and the extra
turns have run out — whatever the game score at that point. Winning game 1 of
a best-of-three does not save a tardy player whose match reaches time; only
finishing the match before time does. This is applied on top of any penalty
for the lateness itself.

Source: TCG Tournament Handbook, Tardiness Clause; TCG Tournament Handbook,
Swiss Tournament Rounds (results apply only if no competitor satisfies the
Tardiness Clause).

## Prize Card penalties — what they do

A Double Prize Card or Quadruple Prize Card penalty is applied at once: the
opponent of the penalized player now needs two (or four) fewer Prize cards than
normal to win the game in progress. If the opponent has already taken that
many, they win immediately. The penalty is about how many Prize cards are
needed to win; it does not add cards to anyone's hand.

Source: Penalty Guidelines, Prize Card Penalties (Pokémon TCG Only).

## Card text is done in the order it is written

An attack, Ability or Trainer card is resolved one sentence at a time, in the
order printed. "Draw 3 cards. Then, shuffle this Pokémon and all attached cards
into your deck" means you draw — and see and keep — the 3 cards first, and the
Pokémon goes into the deck afterwards; the later sentence does not reach back
and undo the earlier one. "Discard a card from your hand. Then, search your
deck" means the discard is paid before the search happens. If a later sentence
cannot be carried out, the earlier ones still happened. Only text that names a
condition for the whole effect ("if you can't, this attack does nothing", "you
can play this card only if…") is checked before anything is done.

Source: Compendium rulings on effect order (e.g. Gumshoos "Evidence Gathering",
Peeking Red Card); rulebook, Full details of attacking, step F ("then do all
other effects").

## Copying an attack — you used your own attack

When a Pokémon uses an attack that copies another attack ("use 1 of the
Defending Pokémon's attacks as this attack", Copycat, Metronome), the attack it
USED is its own copying attack. Consequences:

- Energy: you pay the copying attack's cost, not the copied one's. If the
  copied text needs something you do not have (a type of Energy to discard),
  that part cannot be done; the rest happens.
- Restrictions written into the copied attack ("this Pokémon can't use X during
  your next turn") attach to the named attack, so a copier that does not have
  that attack is not restricted and may copy it again next turn.
- Anything that looks at "the attack this Pokémon used last turn" sees the
  copying attack. If your opponent then copies the attack you used, they copy
  the copying attack itself — which has nothing of its own to copy and does
  nothing.

Source: Compendium 381 (2019-11-14, Copycat and Flare Strike), 382 (2019-01-18,
Copycat Energy cost); rulebook, What counts as an attack?

