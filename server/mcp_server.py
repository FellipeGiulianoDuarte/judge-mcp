"""Remote MCP server. Four tools, no auth.

Authless is deliberate: everything here is a public read-only lookup, there is no
user data and no writes. The exposure is compute, not data, so the control is a
rate limit at the reverse proxy rather than a login.

Descriptions come from tools.py — they are the only lever over how Claude uses the
results, so they are hand-written and must not be regenerated or shortened.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from mcp.server import MCPServer
from pydantic import Field

from card_lookup import lookup_card as _lookup_card
from lookup import lookup as _lookup
from repeat_guard import guard as _guard
from tools import LOOKUP_CARD, LOOKUP_PENALTY, LOOKUP_RULE, LOOKUP_TOURNAMENT

CORPUS_BUILT = "2026-09-05"  # set by the corpus build, not by hand

DISCLAIMER_GAME = (
    "Unofficial tool, not affiliated with The Pokemon Company International. "
    "Verify before you rule; at an event the head judge decides."
)
DISCLAIMER_EVENT = (
    "Unofficial tool, not affiliated with The Pokemon Company International. "
    "The head judge's ruling is final at an event."
)
DISCLAIMER_PENALTY = (
    "Unofficial tool, not affiliated with The Pokemon Company International. "
    "This is the guideline default, not a ruling. The head judge decides and "
    "may deviate."
)

# Words that mean the answer changes with the event tier. Asking for it on every
# question would interrogate a judge who is mid-match, so only ask when it matters.
_TIER_WORDS = ("tier", "round", "cut", "top ", "best-of", "time limit", "swiss")


def _tier_sensitive(results: list[dict]) -> list[str]:
    blob = " ".join(f"{r.get('heading','')} {r.get('text','')}" for r in results).lower()
    return ["event_tier"] if any(w in blob for w in _TIER_WORDS) else []


# The name is what a judge sees in Claude's connector list, and it is a public
# identity — so it carries no trademark. "Pokemon" stays in the description,
# which is where discoverability lives, and out of the name, which is where
# trademark exposure lives.
mcp = MCPServer(
    name="judge-mcp",
    title="TCG rules for judges — unofficial",
    version="0.1.0",
    instructions=(
        "Current Pokémon TCG rules, cards, tournament operation and penalties. "
        "Unofficial. Answer from the tool results, not from memory — your training "
        "data may predate the current rotation."
    ),
)


@mcp.tool(name=LOOKUP_RULE["name"], description=LOOKUP_RULE["description"])
def lookup_rule(
    question: Annotated[str, Field(description=(
        "The user's question, verbatim, in whatever language they asked. "
        "Do not translate it."))],
    terms: Annotated[str, Field(description=(
        "English search terms for this question: the mechanics, statuses and rules "
        "words involved (e.g. 'knock out devolution opponent turn ability trigger'). "
        "The corpus is in English and the user may not be, so this is what actually "
        "finds the rule. Always supply it."))] = "",
    cards: Annotated[list[str] | None, Field(description=(
        "Card names mentioned in the question, in English if you can map them. "
        "Improves matching. Omit if none."))] = None,
) -> dict[str, Any]:
    # Game rules: the hand-written files AND the rulebook. Filtering to the two
    # Markdown files left this tool searching five draft sections while the
    # rulebook's fifty sat unreachable — the game-rules tool could not see the
    # game rules. The tournament handbooks stay out; they belong to the other
    # two tools.
    result = _guard("lookup_rule", _lookup(question, terms, cards,
                    kinds=("exceptions", "mechanics", "ruling", "document"),
                    docs=(None, "rulebook", "compendium")))
    return {**result, "corpus_built": CORPUS_BUILT, "disclaimer": DISCLAIMER_GAME}


@mcp.tool(name=LOOKUP_CARD["name"], description=LOOKUP_CARD["description"])
def lookup_card(
    name: Annotated[str, Field(description=(
        "Card name, or the name of an attack or Ability, in English, Portuguese "
        "or Spanish."))],
    set: Annotated[str | None, Field(description=(
        "Set name or code, if the user named a printing (e.g. 'Neo Genesis', "
        "'PAL'). Omit if unknown."))] = None,
    format: Annotated[Literal["standard", "expanded", "unlimited", "glc"] | None,
        Field(description="Omit to get legality for all formats.")] = None,
    on_date: Annotated[str | None, Field(description=(
        "ISO date. Omit for today. Use when the user asks about a past or future "
        "event date — rotation dates differ between paper and digital play."))] = None,
    text: Annotated[str | None, Field(description=(
        "A few words that appear on the printing you mean (e.g. 'Benched Basic "
        "Pokemon'). Filters the printings when a name has many."))] = None,
) -> dict[str, Any]:
    result = _lookup_card(name, set, format, on_date, text=text)
    return {**result, "corpus_built": CORPUS_BUILT, "disclaimer": DISCLAIMER_GAME}


@mcp.tool(name=LOOKUP_TOURNAMENT["name"], description=LOOKUP_TOURNAMENT["description"])
def lookup_tournament(
    question: Annotated[str, Field(description=(
        "The user's question, verbatim, in their language. Do not translate or "
        "summarise it."))],
    terms: Annotated[str, Field(description=(
        "English search terms for this question: the mechanics, statuses and rules "
        "words involved (e.g. 'knock out devolution opponent turn ability trigger'). "
        "The corpus is in English and the user may not be, so this is what actually "
        "finds the rule. Always supply it."))] = "",
    event_tier: Annotated[str | None, Field(description=(
        "Event tier if stated (League Challenge, League Cup, Regional, "
        "International, Worlds). Round counts and cut size depend on it. "
        "Omit if unknown."))] = None,
) -> dict[str, Any]:
    result = _guard("lookup_tournament", _lookup(question, terms,
                    docs=("tournament-rules-handbook", "tcg-tournament-handbook")))
    return {
        "no_match": result["no_match"],
        # Ask for the tier only when the sections found actually turn on it.
        "needs_context": ([] if event_tier or result["no_match"]
                          else _tier_sensitive(result["documents"])),
        "results": result.get("documents", []),
        "corpus_built": CORPUS_BUILT,
        "disclaimer": DISCLAIMER_EVENT,
    }


@mcp.tool(name=LOOKUP_PENALTY["name"], description=LOOKUP_PENALTY["description"])
def lookup_penalty(
    situation: Annotated[str, Field(description=(
        "What happened, verbatim from the user, in their language. Do not "
        "translate or summarise it."))],
    terms: Annotated[str, Field(description=(
        "English search terms for this question: the mechanics, statuses and rules "
        "words involved (e.g. 'knock out devolution opponent turn ability trigger'). "
        "The corpus is in English and the user may not be, so this is what actually "
        "finds the rule. Always supply it."))] = "",

    event_tier: Annotated[str | None, Field(description=(
        "Event tier (e.g. League Challenge, League Cup, Regional, Worlds). "
        "Changes the penalty. Ask the user if they have not said. "
        "Never assume one."))] = None,
    division: Annotated[Literal["junior", "senior", "masters"] | None,
        Field(description=(
            "Age division. Juniors and Seniors are treated differently from "
            "Masters for several infractions. Ask the user if they have not said. "
            "Never assume Masters."))] = None,
    repeat_offense: Annotated[bool | None, Field(description=(
        "Whether this player already had this infraction today — repeats usually "
        "upgrade the penalty. Ask the user. Never assume false."))] = None,
) -> dict[str, Any]:
    missing = [f for f, v in
               (("event_tier", event_tier), ("division", division),
                ("repeat_offense", repeat_offense)) if v is None]
    result = _guard("lookup_penalty", _lookup(situation, terms, docs=("penalty-guidelines",)))
    return {
        "no_match": result["no_match"],
        "needs_context": [] if result["no_match"] else missing,
        "results": result.get("documents", []),
        "head_judge_may_deviate": True,
        "corpus_built": CORPUS_BUILT,
        "disclaimer": DISCLAIMER_PENALTY,
    }


if __name__ == "__main__":
    import os
    import sys

    from mcp.server.transport_security import TransportSecuritySettings

    # Local development: stdio. Deployed: streamable-http behind a proxy that
    # rate limits — the server is authless because every tool is a public
    # read-only lookup, so the exposure is compute rather than data.
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"

    kwargs: dict = {}
    if transport == "streamable-http":
        # The SDK rejects unexpected Host headers to stop DNS rebinding, which
        # is right and which also blocks every tunnel and reverse proxy until
        # you name the hostname. Localhost only unless PUBLIC_HOST is set.
        public = os.environ.get("PUBLIC_HOST", "").strip()
        hosts = ["127.0.0.1", "127.0.0.1:8000", "localhost", "localhost:8000"]
        origins = ["http://127.0.0.1:8000", "http://localhost:8000"]
        if public:
            hosts.append(public)
            origins.append(f"https://{public}")
        kwargs["transport_security"] = TransportSecuritySettings(
            allowed_hosts=hosts, allowed_origins=origins)
        kwargs["host"] = os.environ.get("BIND_HOST", "127.0.0.1")
        kwargs["port"] = int(os.environ.get("PORT", "8000"))
        print(f"allowed hosts: {hosts}", file=sys.stderr)

    mcp.run(transport=transport, **kwargs)
