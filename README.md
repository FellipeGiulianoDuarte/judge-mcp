# judge-mcp

A rules connector for Pokémon TCG judges. Add it to Claude, ask on your phone at
an event, get an answer from current documents rather than from a model's memory.

**Unofficial. Not affiliated with or endorsed by The Pokémon Company International.**
At a sanctioned event the head judge's ruling is final.

Measured by [judge-bench](https://github.com/FellipeGiulianoDuarte/judge-bench),
which is deliberately a separate repository: a benchmark living beside the thing
it scores invites the obvious objection.

## Why

Rules change on a schedule. Cards with the "G" regulation mark left Standard on
10 April 2026. The Play! Pokémon documents were revised on 1 September 2026. Sets
arrive about every three months.

A model holds rules from its training data, and that data has a date. It does not
know the date has passed, so it answers with the same confidence before and after
a rotation.

## Four tools

| Tool | For |
|---|---|
| `lookup_rule` | how the game works — interactions, timing, effects |
| `lookup_card` | what a card does now, and where it is legal |
| `lookup_tournament` | how an event runs — rounds, pairings, tiebreakers, cut |
| `lookup_penalty` | what to do when someone breaks a rule |

`lookup_penalty` asks before it answers. The same infraction carries different
penalties by event tier, age division, and whether the player has offended before,
so it returns `needs_context` rather than assuming Masters and a first offence.

Every response carries a `disclaimer` field and every tool description requires it
on every answer, including follow-ups. A judge may screenshot any one message and
send it to a player.

Questions arrive in Portuguese and Spanish; the corpus is English because the rules
are English. Callers pass the question verbatim plus English search terms — the
model produces those, so the server needs no translation step.

## The corpus is two files you write, plus the official documents

Split every rules question by one test: **could a competent judge derive this from
the rulebook?**

| | `corpus/mechanics.md` | `corpus/exceptions.md` |
|---|---|---|
| Three judges reading the documents would | agree | argue |
| Example | Poison damage lands at Checkup, between turns | An alternate attack cost cannot be reduced |
| Why it is here | the documents decide it | TPCi decided it, and you could not have predicted which way |

Exceptions override mechanics at lookup time — an exception exists precisely
because the general rule gives the wrong answer for that case.

On top of those sit the official documents, chunked by section number so an answer
cites something a judge can check: `Penalty Guidelines 5.2`, not `chunk 37`.

## Running it

```bash
uv venv && uv pip install mcp pypdf
.venv/bin/python corpus/fetch.py          # rulebook + 3 handbooks -> corpus/raw/
.venv/bin/python corpus/build_docs.py     # chunk by section -> corpus/data/
.venv/bin/python corpus/cards.py --all    # card table from TCGdex (slow)
.venv/bin/python -m pytest tests -q

.venv/bin/python server/mcp_server.py                  # stdio, local
PUBLIC_HOST=your.host .venv/bin/python server/mcp_server.py streamable-http
```

`PUBLIC_HOST` is required behind a proxy or tunnel: the SDK rejects unexpected
`Host` headers to stop DNS rebinding, and without naming the hostname every
request fails with a bare "Invalid Host header".

Authless by design — every tool is a public read-only lookup, no user data and no
writes. The exposure is compute, so the control is a rate limit at the proxy.

## Printed text is not what a card does

`corpus/cards.sqlite` stores the words on the physical card. For any reprinted card
that is not what you play with: a card is identified by its name, so the newest
printing's text replaces the text on every earlier one.

Super Rod is the example. The Neo Genesis (2000) printing prints a coin-flip effect
and is played as the 2023 "shuffle up to 3". `lookup_card` returns both and sets
`printed_text_differs`. A tool answering from a card database alone gets this
confidently wrong while citing a real source.

## Measured

Real questions judges asked each other, rewritten, keyed by what those judges
concluded, then audited against the rulebook, the handbooks and the
Compendium wherever any system disagreed. Gemini 3.8 Flash answers in every
condition. Yes/no questions, contested ones excluded, exact verdict match, no
model grader. A quarter of the questions is held out and never used to change
the connector; that column is the one to trust.

| | public, 272 questions | held-out, 96 questions |
|---|---|---|
| plain chatbot with web search | 240 · 88% | 87 · 91% |
| **this connector** | **255 · 94%** | **91 · 95%** |
| plain chatbot, no tools | 205 · 75% | 74 · 77% |

Run-to-run noise on identical code is about ±3 questions on the public set (four
runs: 252, 255, 258, 255) and ±2 on the held-out set (89, 88, 89, 87, 91).
Head-to-head against web search on the latest run: public wins 19, loses 4;
held-out wins 7, loses 3. Refusals ("I don't know") fell from 23 to 2–8.

What moved the number, each measured on its own:

- **Serving the general rule first.** Thirteen of the first twenty-three losses
  were questions the rulebook answers with a general rule (attack order, effects
  end on the Bench, devolving clears Special Conditions) while short Compendium
  rulings about the same card outscored the rulebook section and the model,
  told not to use memory, said "not found". `principles` — hand-written general
  rules in `corpus/mechanics.md`, each with its checkable source — now come back
  with every rules lookup on their own floor. This was the largest gain.
- **Splitting the rulebook on its real headings.** A heading matched
  mid-sentence had merged three chapters into one 10,893-character section that
  nothing could lift above the score floor; a page number at the top of a page
  had been swallowing the text after it, including the single-elimination time
  table.
- **Telling the model to commit.** "It depends" on a fact the question already
  gave is a wrong answer at a table. Hedges fell from 16 to 4–5.
- **Card lookup by attack or Ability name** in English, Portuguese or Spanish,
  errata attached as the governing text, and a text filter for names with many
  printings.
- **Loading the Compendium** and **the repeat guard** (day one).
- **Auditing the keys.** Of 37 disputed keys, 8 were wrong or malformed and 4
  were time-bound; three described tournament rules TPCi had since changed.

What was tried, measured, and reverted is recorded in `server/lookup.py`.

## Known limits

**Judgement calls.** About half the remaining public misses are penalty questions
where the guidelines give the head judge latitude and the key is one defensible
reading; the model, web search and the bare model all disagree with it.
No corpus fixes that, and it should not.

**Rules that changed.** Tournament handbooks are re-issued every season; the
benchmark's `stale.py` lists keys never checked against the current revision.

**The corpus files are drafts.** Sentences inferred rather than quoted are marked
NEEDS REVIEW and the loader tags them `unreviewed` in responses. A Professor has
not reviewed them.

## Licence

Code [AGPL-3.0](https://www.gnu.org/licenses/agpl-3.0.html) — run a modified version
as a service and you publish your source to its users. The two corpus files are
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/); see `LICENSE-DATA`.

Nothing TPCi publishes is licensed or redistributed here. This ships the scripts
that download the rulebook, handbooks, Penalty Guidelines and card data; the
downloads are gitignored.
