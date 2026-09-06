"""The scenarios from the plan's test matrix.

Run:  .venv/bin/python -m pytest tests -q
"""

from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "server"))
sys.path.insert(0, str(ROOT / "corpus"))

from corpus import load as load_corpus          # noqa: E402


@pytest.fixture(autouse=True)
def _fresh_repeat_guard():
    """The repeat guard remembers sections per session, and the test process is
    one session. Without a reset, any test that looks something up twice sees
    the second call refused — a real behaviour, wrong place to observe it."""
    import repeat_guard
    repeat_guard.reset()
    yield
    repeat_guard.reset()
from legality import is_legal                    # noqa: E402
from lookup import Index, lookup                 # noqa: E402
from tools import TOOLS                          # noqa: E402


# --- Format legality --------------------------------------------------------

def test_current_mark_is_legal():
    assert is_legal("H", "standard")["legal"] is True


def test_rotated_mark_is_not():
    assert is_legal("G", "standard")["legal"] is False


def test_paper_and_digital_rotate_on_different_days():
    """15 days apart in 2026, so a date inside the gap has two right answers."""
    inside = date(2026, 4, 1)
    assert is_legal("G", "standard", inside, digital=True)["legal"] is False
    # Paper had not rotated yet; with only the 2026 rotation loaded the honest
    # answer is "unknown", not "legal".
    assert is_legal("G", "standard", inside, digital=False)["legal"] is None


def test_unmarked_card_is_not_standard_legal():
    assert is_legal(None, "standard")["legal"] is False


def test_missing_format_data_returns_unknown_not_a_guess():
    assert is_legal("H", "expanded")["legal"] is None


def test_mark_newer_than_any_rotation_is_legal():
    assert is_legal("K", "standard")["legal"] is True


# --- Corpus and lookup ------------------------------------------------------

def test_corpus_loads_with_exceptions_first():
    sections = load_corpus()
    assert sections, "corpus is empty"
    assert sections[0].kind == "exceptions"


def test_editor_notes_never_reach_a_section_body():
    assert not any("STATUS: draft" in s.body for s in load_corpus())


def test_unreviewed_sections_are_flagged():
    """Draft rules content must be visibly draft in the response."""
    assert any(s.needs_review for s in load_corpus())


def test_super_rod_resolves_to_an_authoritative_override():
    """Either the Compendium's own Super Rod errata ruling or the hand-written
    exception — both override the printed text. The official ruling outranking
    the hand-written note about the same card is the right order."""
    index = Index()
    hits = index.search("Super Rod printing text errata")
    assert hits and hits[0][0].kind in ("exceptions", "ruling")
    assert "super rod" in hits[0][0].heading.lower()


def test_portuguese_question_finds_an_english_section():
    result = lookup("KO por veneno ativa a habilidade?",
                    "poison knock out checkup trigger ability")
    assert not result["no_match"]


def test_no_match_rather_than_a_bad_guess():
    result = lookup("penalty for wearing a hat at a Regional",
                    "hat clothing dress code apparel")
    assert result["no_match"] is True


# --- Tool contract ----------------------------------------------------------

def test_every_tool_demands_the_disclaimer():
    for tool in TOOLS:
        assert "ALWAYS end your answer with the `disclaimer` field" in tool["description"]


def test_every_response_shape_carries_a_disclaimer():
    import tools as t
    for name in ("RULE_RESPONSE", "CARD_RESPONSE", "TOURNAMENT_RESPONSE", "PENALTY_RESPONSE"):
        assert getattr(t, name).get("disclaimer"), f"{name} has no disclaimer"


def test_penalty_tool_asks_before_it_assumes():
    penalty = next(t for t in TOOLS if t["name"] == "lookup_penalty")
    assert "ASK BEFORE YOU CALL" in penalty["description"]
    for field in ("event_tier", "division", "repeat_offense"):
        assert field in penalty["inputSchema"]["properties"]
        assert field not in penalty["inputSchema"]["required"], \
            "required fields make models invent values instead of asking"


def test_free_text_tools_take_english_search_terms():
    """The corpus is English and the judges are not."""
    for name in ("lookup_rule", "lookup_tournament", "lookup_penalty"):
        tool = next(t for t in TOOLS if t["name"] == name)
        assert "terms" in tool["inputSchema"]["properties"]


@pytest.mark.asyncio
async def test_server_registers_four_tools_and_answers():
    import json

    from mcp_server import mcp

    registered = {t.name for t in await mcp.list_tools()}
    assert registered == {"lookup_rule", "lookup_card", "lookup_tournament", "lookup_penalty"}

    # A real infraction: missing tier/division/repeat come back as questions,
    # not assumptions.
    found = await mcp.call_tool("lookup_penalty", {
        "situation": "player arrived 12 minutes late",
        "terms": "tardiness late match start penalty"})
    payload = json.loads(found.content[0].text)
    assert payload["disclaimer"]
    if not payload["no_match"]:
        assert set(payload["needs_context"]) == {"event_tier", "division", "repeat_offense"}
        assert payload["head_judge_may_deviate"] is True

    # Nothing matched: do not also ask for the division. There is no penalty for
    # it to vary, and the pair of messages reads as a bug.
    empty = await mcp.call_tool("lookup_penalty", {
        "situation": "player wore a funny hat",
        "terms": "hat clothing dress code apparel"})
    blank = json.loads(empty.content[0].text)
    assert blank["no_match"] is True
    assert blank["needs_context"] == []
    assert blank["disclaimer"]


# --- Card lookup ------------------------------------------------------------

@pytest.mark.skipif(not (ROOT / "corpus/cards.sqlite").exists(),
                    reason="card table not built (python3 corpus/cards.py --sets ...)")
class TestCardLookup:
    def test_printed_text_is_never_returned_alone_when_an_exception_covers_it(self):
        from card_lookup import lookup_card

        result = lookup_card("Super Rod")
        assert not result["no_match"]
        for match in result["matches"]:
            assert match["printed_text_differs"] is True
            assert "shuffle **up to 3**" in match["governing_text"].lower()

    def test_printings_that_read_differently_are_ambiguous(self):
        """One name, four printings, two different printed effects — ask which."""
        from card_lookup import lookup_card

        assert lookup_card("Super Rod")["ambiguous"] is True

    def test_the_2000_printing_is_played_as_the_modern_card(self):
        from card_lookup import lookup_card

        old = next(m for m in lookup_card("Super Rod")["matches"] if m["id"] == "neo1-103")
        assert "flip a coin" in old["printed_text"].lower()      # what it says
        assert "up to 3" in old["governing_text"].lower()        # what it does

    def test_unknown_legality_is_not_reported_as_a_disagreement(self):
        """None means 'no data', and no data cannot conflict with a verdict."""
        from card_lookup import lookup_card

        for match in lookup_card("Super Rod")["matches"]:
            clash = match.get("source_disagreement")
            if clash:
                for fmt, ours in clash["ours"].items():
                    assert ours is not None, f"{fmt}: reported unknown as a conflict"

    def test_unknown_card_returns_no_match(self):
        from card_lookup import lookup_card

        assert lookup_card("Definitely Not A Real Card")["no_match"] is True


# --- Official documents -----------------------------------------------------

DOCS_BUILT = (ROOT / "corpus/data/documents.json").exists()


def test_page_numbers_are_not_mistaken_for_sections():
    """A bare '35' on a heading line is the page number, not section 35."""
    from build_docs import real_section

    assert real_section("5.2")
    assert real_section("4.4.2")
    assert real_section("7")
    assert not real_section("35")       # these documents have no 35th top-level section


@pytest.mark.skipif(not DOCS_BUILT, reason="run corpus/fetch.py then corpus/build_docs.py")
class TestDocumentLookup:
    def test_sections_carry_a_citation_a_judge_can_check(self):
        from lookup import lookup

        result = lookup("player arrived late", "tardiness late match start",
                        docs=("penalty-guidelines",))
        assert not result["no_match"]
        top = result["documents"][0]
        assert re.match(r"^penalty-guidelines \d+(\.\d+)*$", top["citation"])
        assert top["revised"]

    def test_portuguese_question_reaches_the_right_penalty_section(self):
        from lookup import lookup

        result = lookup("jogador chegou 12 minutos atrasado, o que faço?",
                        "player arrived late tardiness match start",
                        docs=("penalty-guidelines",))
        assert result["documents"][0]["heading"] == "Tardiness"

    def test_a_question_no_document_answers_returns_no_match(self):
        """272 sections of tournament prose graze almost any question. The
        threshold is what stops that becoming a confident wrong citation."""
        from lookup import lookup

        result = lookup("player wore a funny hat", "hat clothing dress code apparel",
                        docs=("penalty-guidelines",))
        assert result["no_match"] is True

    def test_game_rule_lookup_does_not_return_handbook_sections(self):
        from lookup import lookup

        result = lookup("poison knock out", "poison checkup knock out trigger",
                        kinds=("exceptions", "mechanics"))
        assert result.get("documents", []) == []


# --- Repeat guard -----------------------------------------------------------

def test_same_section_for_new_terms_becomes_no_match():
    """The model searched nine times, got the same junk section nine times, and
    concluded the corpus lacked an answer it knew. The second identical top hit
    must come back as no_match so it can move on."""
    import repeat_guard

    repeat_guard.reset()
    hit = {"no_match": False, "documents": [{"citation": "rulebook Zones", "text": "x"}]}
    first = repeat_guard.guard("lookup_rule", dict(hit))
    second = repeat_guard.guard("lookup_rule", dict(hit))
    assert first["no_match"] is False
    assert second["no_match"] is True and "already returned" in second["note"]


def test_a_different_section_is_not_blocked():
    import repeat_guard

    repeat_guard.reset()
    repeat_guard.guard("lookup_rule", {"no_match": False, "documents": [{"citation": "A", "text": ""}]})
    other = repeat_guard.guard("lookup_rule", {"no_match": False, "documents": [{"citation": "B", "text": ""}]})
    assert other["no_match"] is False


def test_guard_is_per_tool():
    """The same section from lookup_rule and lookup_tournament are different events."""
    import repeat_guard

    repeat_guard.reset()
    repeat_guard.guard("lookup_rule", {"no_match": False, "documents": [{"citation": "A", "text": ""}]})
    via_other = repeat_guard.guard("lookup_tournament", {"no_match": False, "documents": [{"citation": "A", "text": ""}]})
    assert via_other["no_match"] is False


@pytest.mark.skipif(not (ROOT / "corpus/cards.sqlite").exists(), reason="card table not built")
class TestCardLookupByMoveAndErrata:
    def test_an_attack_named_in_portuguese_finds_the_card(self):
        """Judges name the attack, not the card. 'Olhar Abissal' is an attack of
        Mega Darkrai ex; no card has that name."""
        from card_lookup import lookup_card
        result = lookup_card("Olhar Abissal")
        assert result["no_match"] is False and result["matched_by"] == "attack name"
        assert "Mega Darkrai ex" in result["cards_with_this_move"]
        assert "Knocked Out" in result["move"]["effect_en"]

    def test_an_errata_makes_every_printing_play_as_the_current_text(self):
        """Quick Ball's 2008 printing reveals cards until a Pokémon; the 2020
        errata makes every printing play as the current search. The old
        printing must come back with the errata as governing text."""
        from card_lookup import lookup_card
        result = lookup_card("Quick Ball")
        assert result["errata"] and result["errata"][-1]["date"] == "2020-01-09"
        for match in result["matches"]:
            assert match["printed_text_differs"] is True
            assert match["governing_source"].startswith("errata")

    def test_text_filter_keeps_the_printing_the_judge_means(self):
        from card_lookup import lookup_card
        result = lookup_card("Articuno", text="Blizzard")
        assert result["matches"] and all("blizzard" in (m["printed_text"] or "").lower() for m in result["matches"])

    def test_set_filter_applies_to_every_name_alternative(self):
        """AND used to bind tighter than OR, so the set filter only applied to the
        Spanish name and "Mimikyu" in Team Up returned all sixteen printings."""
        from card_lookup import lookup_card
        result = lookup_card("Mimikyu", set_id="Team Up")
        assert result["matches"] and all(m["set"] == "Team Up" for m in result["matches"])
        by_code = lookup_card("Mimikyu", set_id="TEU")
        assert by_code["matches"] and all(m["set"] == "Team Up" for m in by_code["matches"])

