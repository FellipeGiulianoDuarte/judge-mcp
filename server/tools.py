"""MCP tool definitions.

Two tools. The descriptions are the only lever we have over how Claude uses
the results, so they carry the behaviour rules — see RISKS in the plan.
"""

# Shared preamble. Repeated in both descriptions because Claude reads them
# independently and there is no system-prompt channel on a connector.
_RULES = """
HOW TO REASON. Start from `principles` — the general rules of the game. Most
questions are answered by a general rule, not by a ruling written for that
exact card. Rulings (`rulings`) confirm or narrow a principle; a ruling about
an old card with different names is still the same rule if the wording of the
attack or Ability is the same. If a principle answers the question and no
ruling contradicts it, ANSWER from the principle. Do not say "not found"
because no ruling names the card in the question. Say "not found" only when
neither a principle nor a ruling nor the card text lets you decide.
Your memory of card text, set legality and the current rotation may be stale —
use `lookup_card` for those rather than remembering them.
COMMIT TO AN ANSWER. Answer the situation the user described. If the question
is yes/no, say yes or no for that situation, then the reason. Add a caveat only
when it changes the answer for THAT situation — not because another card of the
same name, another format, or another printing would come out differently. A
judge at a table needs a ruling, not a survey. "It depends" is only right when
the user's own facts are missing, and then say which fact.
Lead with the verdict. Keep it short — the user is usually mid-match.

ALWAYS end your answer with the `disclaimer` field, verbatim, on its own line.
Every single response, including follow-ups in a conversation where you have
already said it. Do not shorten it, merge it into a sentence, or drop it because
it is repetitive. A judge may screenshot any one message and send it to a player.
"""

LOOKUP_RULE = {
    "name": "lookup_rule",
    "description": f"""Look up a current Pokemon TCG rule, card interaction, or
tournament procedure (penalties, deck lists, tardiness, match procedure).

`principles` are the general rules that apply (attack order, what ends an
effect, Checkup order, what "do as much as you can" means). `exceptions`
OVERRIDE `principles`/`mechanics`: an exception exists precisely because the
general rule gives the wrong answer for that case.

HOW TO SEARCH. The rulings are indexed by their own wording, which is usually
about an OLDER card with the same mechanic. Search by the mechanic and by the
wording of the attack or Ability ("discard an Energy", "during your next turn",
"prevent all effects", "Poison Point", "search your deck"), not by the card in
the question — put card names in `cards`, not in `terms`. One search with good
`terms` usually suffices; a second with different mechanic words is reasonable.
After two searches, answer from `principles` plus what `lookup_card` returned.
Do not keep searching for a ruling that names the card.

This tool is for how the GAME works. For how an EVENT runs — rounds, pairings,
tiebreakers, cut to top, divisions, eligibility — use `lookup_tournament`.
For "a player did X, what do I do" — an infraction or penalty — use `lookup_penalty`.
{_RULES}""",
    "inputSchema": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The user's question, verbatim, in whatever "
                               "language they asked. Do not translate it.",
            },
            "terms": {
                "type": "string",
                "description": "English search terms: the mechanic, status and "
                               "rules words, and the attack/Ability wording in "
                               "play (e.g. 'devolve Special Condition removed', "
                               "'attack discard Energy damage calculation order', "
                               "'Checkup order effects decide'). Not card names — "
                               "rulings are about older cards with other names. "
                               "The corpus is in English and the user may not be, "
                               "so this is what actually finds the rule. Always "
                               "supply it.",
            },
            "cards": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Card names mentioned in the question, in English "
                               "if you can map them. Improves matching. Omit if none.",
            },
        },
        "required": ["question"],
        "additionalProperties": False,
    },
}

LOOKUP_CARD = {
    "name": "lookup_card",
    "description": f"""Look up a Pokemon TCG card: what it does now, and whether
it is legal in a format.

A card's printed text may be out of date. When `printed_text_differs` is true you
MUST say both: what the card in the player's hand reads, and what it actually
plays as. The current text governs every printing.

Legality follows the regulation mark, not the set. If `ambiguous` is true the name
matches several printings that differ — ask which one the player is holding rather
than picking one, or pass `text` with words from the printing you mean.

You may pass the name of an ATTACK or ABILITY instead of a card, in English,
Portuguese or Spanish ("Olhar Abissal", "Poison Point"): `matched_by` says so and
`move` gives its English name and effect. Judges name the move, not the card.

If `errata` is present the card has an official errata: every printing is played
with the errata text (`governing_text`), whatever it says on its face, and an old
printing is legal wherever the current one is. Say so.
{_RULES}""",
    "inputSchema": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Card name, or the name of an attack or Ability, in English, Portuguese or Spanish."},
            "set": {
                "type": "string",
                "description": "Set name or code, if the user named a printing "
                               "(e.g. 'Neo Genesis', 'PAL'). Omit if unknown.",
            },
            "format": {
                "type": "string",
                "enum": ["standard", "expanded", "unlimited", "glc"],
                "description": "Omit to get legality for all formats.",
            },
            "on_date": {
                "type": "string",
                "description": "ISO date. Omit for today. Use when the user asks "
                               "about a past or future event date — rotation dates "
                               "differ between paper and digital play.",
            },
            "text": {
                "type": "string",
                "description": "A few words that appear on the printing you mean "
                               "(e.g. 'Benched Basic Pokemon'). Filters the "
                               "printings when a name has many.",
            },
        },
        "required": ["name"],
        "additionalProperties": False,
    },
}

LOOKUP_PENALTY = {
    "name": "lookup_penalty",
    "description": f"""Work out the penalty or procedure for something that happened
at an event: a deck list error, a marked card, slow play, tardiness, an illegal
deck, a match restart, a concession problem.

Unlike a card rule, a penalty is NOT a single correct answer. The guidelines give a
default that varies by event tier and age division, and the head judge may deviate.
So you MUST report `default_penalty` as the default, list any `modifiers` that apply,
and state that the head judge's ruling is final. Never present it as the only
possible outcome.

ASK BEFORE YOU CALL. The penalty for the same infraction changes with the event tier,
the age division, and whether the player has already had this infraction today. If the
user has not said, ask them — one short question, they are usually mid-event. Never
assume Masters, never assume a first offense, never assume a tier.

If you call without them anyway, the response comes back with `needs_context` listing
what is missing and `varies_by` showing the answer for each case. Report the variants
and ask which applies — do not pick one.

Not for logistics: player IDs, registration, forms, prize payouts, or software.
Return `no_match` for those rather than guessing.
{_RULES}""",
    "inputSchema": {
        "type": "object",
        "properties": {
            "situation": {
                "type": "string",
                "description": "What happened, verbatim from the user, in their "
                               "language. Do not translate or summarise it.",
            },
            "terms": {
                "type": "string",
                "description": "English search terms: the mechanic, status and "
                               "rules words, and the attack/Ability wording in "
                               "play (e.g. 'devolve Special Condition removed', "
                               "'attack discard Energy damage calculation order', "
                               "'Checkup order effects decide'). Not card names — "
                               "rulings are about older cards with other names. "
                               "The corpus is in English and the user may not be, "
                               "so this is what actually finds the rule. Always "
                               "supply it.",
            },

            "event_tier": {
                "type": "string",
                "description": "Event tier (e.g. League Challenge, League Cup, "
                               "Regional, Worlds). Changes the penalty. Ask the user "
                               "if they have not said. Never assume one.",
            },
            "division": {
                "type": "string",
                "enum": ["junior", "senior", "masters"],
                "description": "Age division. Juniors and Seniors are treated "
                               "differently from Masters for several infractions. "
                               "Ask the user if they have not said. Never assume "
                               "Masters. VERIFY these three values against the "
                               "current handbook before shipping.",
            },
            "repeat_offense": {
                "type": "boolean",
                "description": "Whether this player already had this infraction "
                               "today — repeats usually upgrade the penalty. Ask the "
                               "user. Never assume false.",
            },
        },
        "required": ["situation"],
        "additionalProperties": False,
    },
}

LOOKUP_TOURNAMENT = {
    "name": "lookup_tournament",
    "description": f"""Look up how a Play! Pokemon EVENT runs, as opposed to how the
game is played: number of rounds, Swiss pairings, tiebreakers and resistance, cut to
top, match and series structure, time limits, age divisions, event tiers, player
eligibility and Player IDs, appeals, spectators, electronic devices.

Two documents are in scope and they are not the same: the Play! Pokemon Tournament
Rules Handbook covers every game (TCG, VGC, GO, UNITE), and the TCG Tournament
Handbook adds TCG-specific rules on top. Each result names which document it came
from in `doc` — say which one when it matters, and if both are returned and disagree,
report both rather than picking one.

If the situation also involves someone breaking a rule, call `lookup_penalty` as well
— this tool says how the event should run, not what the penalty is.

For tiebreaker questions, return the definition and let the user check their own
arithmetic. Do not compute standings yourself.
{_RULES}""",
    "inputSchema": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The user's question, verbatim, in their language. "
                               "Do not translate or summarise it.",
            },
            "terms": {
                "type": "string",
                "description": "English search terms: the mechanic, status and "
                               "rules words, and the attack/Ability wording in "
                               "play (e.g. 'devolve Special Condition removed', "
                               "'attack discard Energy damage calculation order', "
                               "'Checkup order effects decide'). Not card names — "
                               "rulings are about older cards with other names. "
                               "The corpus is in English and the user may not be, "
                               "so this is what actually finds the rule. Always "
                               "supply it.",
            },
            "event_tier": {
                "type": "string",
                "description": "Event tier if stated (League Challenge, League Cup, "
                               "Regional, International, Worlds). Round counts and "
                               "cut size depend on it. Omit if unknown.",
            },
        },
        "required": ["question"],
        "additionalProperties": False,
    },
}

TOOLS = [LOOKUP_RULE, LOOKUP_CARD, LOOKUP_TOURNAMENT, LOOKUP_PENALTY]


# --- Response shapes (what the server returns; not part of the MCP schema) ---

RULE_RESPONSE = {
    "no_match": False,
    "is_procedure": False,
    "mechanics": [
        {"doc": "tcg-tournament-handbook", "section": "4.3",
         "text": "...", "revised": "2026-05-21"},
    ],
    "exceptions": [
        {"title": "Alternate attack costs are not modifiable",
         "text": "...", "overrides": "attack cost reduction"},
    ],
    "corpus_built": "2026-09-05",
    "disclaimer": "Unofficial tool, not affiliated with The Pokemon Company "
                  "International. Verify before you rule; at an event the head "
                  "judge decides.",
}

TOURNAMENT_RESPONSE = {
    "no_match": False,
    "needs_context": [],                       # e.g. ["event_tier"]
    "results": [
        {"doc": "tournament-rules-handbook",   # cross-game
         "section": "5.2", "text": "...", "revised": "2026-05-21"},
        {"doc": "tcg-tournament-handbook",     # TCG-specific
         "section": "3.1", "text": "...", "revised": "2026-05-21"},
    ],
    "corpus_built": "2026-09-05",
    "disclaimer": "Unofficial tool, not affiliated with The Pokemon Company "
                  "International. The head judge's ruling is final at an event.",
}

PENALTY_RESPONSE = {
    # SHAPE IS PROVISIONAL. The real fields come from reading the Penalty
    # Guidelines PDF -- do that before finalising this. Do not invent categories.
    "no_match": False,
    "needs_context": ["event_tier", "division"],   # what was not supplied
    "varies_by": {                                  # so a missing field degrades,
        "division": {"masters": "...", "senior": "...", "junior": "..."},
        "event_tier": {"league-cup": "...", "regional": "..."},
    },                                              # rather than blocking the answer
    "infraction": "Deck/Decklist Error",
    "default_penalty": "...",
    "modifiers": [
        {"when": "repeat offense at this event", "becomes": "..."},
        {"when": "junior division", "becomes": "..."},
    ],
    "procedure": "...",                        # what the judge actually does now
    "head_judge_may_deviate": True,
    "section": "Penalty Guidelines 4.1.1",
    "revised": "2026-05-21",
    "corpus_built": "2026-09-05",
    "disclaimer": "Unofficial tool, not affiliated with The Pokemon Company "
                  "International. This is the guideline default, not a ruling. "
                  "The head judge decides and may deviate.",
}

CARD_RESPONSE = {
    "no_match": False,
    "ambiguous": False,
    "matches": [
        {
            "name": "Super Rod",
            "set": "Neo Genesis", "number": "103",
            "regulation_mark": None,
            "printed_text": "Shuffle 3 in any combination of Pokemon and basic "
                            "Energy cards from your discard pile into your deck.",
            "current_text": "Shuffle up to 3 in any combination of Pokemon and "
                            "basic Energy cards from your discard pile into your deck.",
            "printed_text_differs": True,
            "legality": {"standard": False, "expanded": True, "unlimited": True},
            "as_of": "2026-09-05",
        },
    ],
    "corpus_built": "2026-09-05",
    "disclaimer": "Unofficial tool, not affiliated with The Pokemon Company "
                  "International. Verify before you rule; at an event the head "
                  "judge decides.",
}
