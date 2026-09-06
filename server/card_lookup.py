"""Answer "what does this card do, and where is it legal".

Two sources, and mixing them up is the failure this whole project exists to fix:

  corpus/cards.sqlite   printed text — the words on the physical card
  corpus/exceptions.md  governing text — what the card is actually played as

For any reprinted card those differ, because a card is identified by its name and
the newest printing's text replaces every earlier one. Super Rod (Neo Genesis, 2000)
prints a coin-flip effect and is played as the 2023 "shuffle up to 3".

So printed text is never returned on its own. When an exception covers the card,
both are returned and `printed_text_differs` is set, and the tool description
requires the answer to say both.
"""

from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
from pathlib import Path

from corpus import load as load_corpus
from legality import all_formats, is_legal

DB = Path(__file__).parent.parent / "corpus/cards.sqlite"
COMPENDIUM = Path(__file__).parent.parent / "corpus/data/compendium.json"
_ERRATA: dict[str, list[dict]] | None = None


def errata_for(card_name: str) -> list[dict]:
    """Compendium errata entries for this card, by name.

    An errata rewrites the card by NAME: every printing is played with the new
    text however old it is. The card table only knows what was printed, so an
    older Quick Ball looked like a different, illegal card until this was added.
    """
    global _ERRATA
    if _ERRATA is None:
        _ERRATA = {}
        if COMPENDIUM.exists():
            data = json.loads(COMPENDIUM.read_text(encoding="utf-8"))
            for r in (data.get("rulings") if isinstance(data, dict) else data) or []:
                if r.get("category") == "1-errata":
                    _ERRATA.setdefault(folded(r.get("question", "")), []).append(
                        {"date": r.get("date"), "text": r.get("answer"), "source": r.get("source")})
    return _ERRATA.get(folded(card_name), [])


def folded(text: str) -> str:
    n = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in n if not unicodedata.combining(c)).strip()


# Printed conventions, not rules. A judge treats two printings as the same card
# when they differ only by these — and so must the ambiguity check, or "Pikachu"
# reports 84 distinct texts and the model asks which printing instead of answering.
_REMINDERS = [
    r"you may play as many item cards as you like during your turn(?: \(before your attack\))?\.?",
    r"you may play only one supporter card during your turn(?: \(before your attack\))?\.?",
    r"this card stays in play when you play it\. discard this card if another stadium card comes into play\.?",
    r"attach [a-z ]+ energy to 1 of your pok[eé]mon\. if that pok[eé]mon is knocked out, discard this card\.?",
    r"\(before your attack\)",
]
_REMINDER_RE = re.compile("|".join(_REMINDERS), re.I)


def rules_text(text: str | None) -> str:
    """Card text reduced to what changes how it plays.

    Strips reminder boilerplate, case, punctuation and the "back" in "back into
    your deck". Two printings with the same rules_text are the same card to a
    judge, whatever the layout artist did.
    """
    t = _REMINDER_RE.sub(" ", text or "")
    t = folded(t)
    t = re.sub(r"\bback into\b", "into", t)
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def governing(card_name: str) -> dict | None:
    """An exception naming this card overrides whatever the printing says."""
    needle = folded(card_name)
    for section in load_corpus():
        if section.kind != "exceptions":
            continue
        if needle in folded(section.heading) or needle in folded(section.body):
            return {"heading": section.heading, "text": section.body,
                    "overrides": section.overrides,
                    "unreviewed": section.needs_review}
    return None


def _by_move(db: sqlite3.Connection, key: str, set_id: str | None) -> tuple[list, dict | None]:
    """Cards that have an Ability or attack with this name, in en/pt/es.

    Judges often name the attack, not the card — "Olhar Abissal" — and a card
    named like that does not exist. Returns the rows and the move matched.
    """
    have = db.execute("SELECT name FROM sqlite_master WHERE name = 'moves'").fetchone()
    if not have:
        return [], None
    mv = db.execute("SELECT * FROM moves WHERE name_en_folded = ? OR name_pt_folded = ? OR name_es_folded = ?",
                    (key, key, key)).fetchall()
    if not mv:
        return [], None
    ids = sorted({m["card_id"] for m in mv})
    sql = f"SELECT * FROM cards WHERE id IN ({','.join('?' * len(ids))})"
    args: list = list(ids)
    if set_id:
        sql += " AND (set_id = ? OR set_name = ? OR set_abbrev = ?)"
        args += [set_id, set_id, set_id.upper()]
    rows = db.execute(sql + " ORDER BY released, id", args).fetchall()
    first = mv[0]
    return rows, {"kind": first["kind"], "name_en": first["name_en"], "name_pt": first["name_pt"],
                  "name_es": first["name_es"], "effect_en": first["effect_en"]}


def lookup_card(name: str, set_id: str | None = None, fmt: str | None = None,
                on_date: str | None = None, digital: bool = False,
                text: str | None = None) -> dict:
    if not DB.exists():
        return {"no_match": True, "ambiguous": False, "matches": [],
                "note": "Card table not built. Run: python3 corpus/cards.py --all"}

    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    # Judges name cards in Portuguese and Spanish as often as in English —
    # "Jardim Misterioso" is Mysterious Garden. Match on all three.
    key = folded(name)
    # The name alternatives are parenthesised: without that, AND bound tighter
    # than OR and a `set` filter applied only to the Spanish name, so
    # lookup_card("Mimikyu", set_id="Team Up") returned all 16 printings.
    sql = "SELECT * FROM cards WHERE (name_folded = ? OR name_pt_folded = ? OR name_es_folded = ?)"
    args: list = [key, key, key]
    if set_id:
        sql += " AND (set_id = ? OR set_name = ? OR set_abbrev = ?)"
        args += [set_id, set_id, set_id.upper()]
    # Oldest first, newest last — by release date, not id. "Newest printing" is
    # what decides the governing text, and by id string "xy8" sorts after "sv02".
    rows = db.execute(sql + " ORDER BY released, id", args).fetchall()
    matched_move = None
    if not rows:
        rows, matched_move = _by_move(db, key, set_id)
    db.close()

    text_filter_note = None
    if text:
        # "The Articuno that protects Benched Basic Pokémon": keep printings whose
        # rules text contains the words, so the compaction below cannot drop the
        # one printing the judge is holding.
        needle = rules_text(text)
        filtered = [r for r in rows if needle in rules_text(r["printed_text"])]
        if filtered:
            rows = filtered
        else:
            text_filter_note = (f"No printing of this name contains \"{text}\". The card you "
                                f"are thinking of may have another name; all printings are shown.")

    if not rows:
        return {"no_match": True, "ambiguous": False, "matches": []}

    card_names = sorted({r["name"] for r in rows})
    override = governing(name) or (governing(card_names[0]) if matched_move else None)
    errata = errata_for(name) or (errata_for(card_names[0]) if len(card_names) == 1 else [])
    matches = []
    for row in rows:
        mark = row["regulation_mark"]
        legality = ({fmt: is_legal(mark, fmt, on_date, digital, row["name"])}  # type: ignore[arg-type]
                    if fmt else all_formats(mark, on_date, digital, row["name"]))
        match = {
            "id": row["id"], "name": row["name"],
            "name_pt": row["name_pt"] if "name_pt" in row.keys() else None,
            "set": row["set_name"], "number": row["local_id"],
            "released": row["released"] if "released" in row.keys() else None,
            "regulation_mark": mark,
            "printed_text": row["printed_text"],
            "legality": legality,
        }
        if override:
            match["governing_text"] = override["text"]
            match["printed_text_differs"] = True
            match["governing_source"] = override["heading"]
            if override.get("unreviewed"):
                match["unreviewed"] = True
        elif errata:
            newest = errata[-1]
            match["governing_text"] = newest["text"]
            match["printed_text_differs"] = True
            match["governing_source"] = f"errata, {newest['date']} ({newest.get('source') or 'Compendium'})"
        else:
            # No exception on file. The printed text is the best we have — say so
            # rather than implying it was checked against the errata list.
            match["printed_text_differs"] = None
        # TCGdex's own verdict, kept only to catch our own errors.
        try:
            theirs = json.loads(row["tcgdex_legal"] or "null")
        except json.JSONDecodeError:
            theirs = None
        if theirs and not on_date:
            ours = {f: v.get("legal") for f, v in legality.items()}
            # None means "we have no data for that format" — unknown cannot
            # disagree with anything. Only flag a real verdict that differs.
            if any(ours.get(f) is not None and f in theirs and theirs[f] != ours[f]
                   for f in ("standard", "expanded")):
                match["source_disagreement"] = {"ours": ours, "tcgdex": theirs}
        matches.append(match)

    # A judge asked about "Pikachu" does not want 114 printings and 85,000
    # characters — that made the model ask which printing instead of answering,
    # or drown. Show the CURRENT card: the newest printing, plus any older
    # printing whose text differs (those are the ones that can trap a judge),
    # newest first. Everything else is a count. A set filter still returns all.
    if not set_id and len(matches) > 3:
        newest_first = list(reversed(matches))          # ordered oldest->newest above
        newest_text = rules_text(newest_first[0]["printed_text"])
        shown, seen_text = [], set()
        for m in newest_first:
            key = rules_text(m["printed_text"])
            if key in seen_text:
                continue
            seen_text.add(key)
            shown.append(m)
            if len(shown) == 3:
                break
        # Always include the OLDEST printing whose text differs from the newest.
        # That is the one a judge gets handed across the table and the one the
        # governing-text rule exists for — Super Rod's 2000 coin-flip printing
        # was being cut by the newest-three cap.
        oldest_differing = next((m for m in matches
                                 if rules_text(m["printed_text"]) != newest_text), None)
        if oldest_differing and oldest_differing not in shown:
            shown.append(oldest_differing)
        omitted = len(matches) - len(shown)
        printings = {rules_text(m["printed_text"]) for m in shown}
        return _decorate({
            "no_match": False,
            "ambiguous": len(printings) > 1,
            "matches": shown,
            "other_printings_omitted": omitted,
            "note": (f"{len(matches)} printings exist. Showing the newest and any older "
                     f"printing with different text. Pass `set` for a specific one, or "
                     f"`text` with words from the printing you mean."),
        }, matched_move, errata, card_names, text_filter_note)

    printings = {rules_text(m["printed_text"]) for m in matches}
    return _decorate({
        "no_match": False,
        "ambiguous": len(matches) > 1 and len(printings) > 1,
        "matches": matches,
    }, matched_move, errata, card_names, text_filter_note)


def _decorate(result: dict, matched_move: dict | None, errata: list[dict], card_names: list[str],
              text_filter_note: str | None = None) -> dict:
    if text_filter_note:
        result["text_filter"] = text_filter_note
    if matched_move:
        result["matched_by"] = f"{matched_move['kind']} name"
        result["move"] = matched_move
        result["cards_with_this_move"] = card_names
        if len(card_names) > 1:
            result["ambiguous"] = True
    if errata:
        result["errata"] = errata
        result["errata_note"] = ("This card has an errata. EVERY printing, however old, is played "
                                 "with the errata text, and is legal wherever the current printing is.")
    return result
