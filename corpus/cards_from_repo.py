"""Build the card table from a clone of tcgdex/cards-database.

One shallow clone (~97 MB) replaces ~20,000 API requests, and the source files
carry something the API stubs do not: card names in Portuguese and Spanish. The
judges this is for ask in Portuguese, naming cards in Portuguese — "Jardim
Misterioso", not "Mysterious Garden" — and a table with English names only could
never match them.

Same schema as cards.py plus name_pt / name_es, so server/card_lookup.py works
unchanged and gains the extra names.

    git clone --depth 1 https://github.com/tcgdex/cards-database corpus/raw/tcgdex
    python3 corpus/cards_from_repo.py
"""

from __future__ import annotations

import json
import re
import sqlite3
import sys
import time
import unicodedata
from pathlib import Path

REPO = Path(__file__).parent / "raw/tcgdex/data"
DB = Path(__file__).parent / "cards.sqlite"

SCHEMA = """
DROP TABLE IF EXISTS cards;
CREATE TABLE cards (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    name_folded     TEXT NOT NULL,
    name_pt         TEXT,
    name_pt_folded  TEXT,
    name_es         TEXT,
    name_es_folded  TEXT,
    set_id          TEXT,
    set_name        TEXT,
    set_abbrev      TEXT,
    released        TEXT,
    local_id        TEXT,
    category        TEXT,
    trainer_type    TEXT,
    regulation_mark TEXT,
    printed_text    TEXT,    -- Trainer/Energy: effect. Pokemon: abilities + attacks, in English.
    tcgdex_legal    TEXT,
    fetched_on      TEXT
);
CREATE INDEX cards_by_name    ON cards (name_folded);
CREATE INDEX cards_by_name_pt ON cards (name_pt_folded);
CREATE INDEX cards_by_name_es ON cards (name_es_folded);

-- One row per Ability or attack, with its name in the three languages judges
-- use. A judge who asks about "Olhar Abissal" is naming an attack, not a card,
-- and the card table alone cannot answer that.
DROP TABLE IF EXISTS moves;
CREATE TABLE moves (
    card_id         TEXT NOT NULL,
    kind            TEXT NOT NULL,   -- 'ability' | 'attack'
    name_en         TEXT,
    name_en_folded  TEXT,
    name_pt         TEXT,
    name_pt_folded  TEXT,
    name_es         TEXT,
    name_es_folded  TEXT,
    effect_en       TEXT
);
CREATE INDEX moves_by_en ON moves (name_en_folded);
CREATE INDEX moves_by_pt ON moves (name_pt_folded);
CREATE INDEX moves_by_es ON moves (name_es_folded);
"""

STR = re.compile(r'"((?:[^"\\]|\\.)*)"')


def folded(text: str | None) -> str | None:
    if not text:
        return None
    n = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in n if not unicodedata.combining(c)).strip()


def block(src: str, key: str) -> str | None:
    """The value of a top-level `key: {...}` or `key: [...]`, by brace matching.

    The files are TypeScript object literals, regular enough that this beats a
    parser: find the key at one tab of indent, then walk to its closing bracket.
    """
    m = re.search(rf"^\t{key}:\s*([\[{{])", src, re.M)
    if not m:
        return None
    open_ch = m.group(1)
    close_ch = "]" if open_ch == "[" else "}"
    depth, i = 0, m.end() - 1
    in_str = False
    while i < len(src):
        c = src[i]
        if in_str:
            if c == "\\":
                i += 1
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c == open_ch:
            depth += 1
        elif c == close_ch:
            depth -= 1
            if depth == 0:
                return src[m.end():i]
        i += 1
    return None


def lang(blk: str | None, code: str) -> str | None:
    if not blk:
        return None
    m = re.search(rf"^\s*{code}:\s*\"((?:[^\"\\]|\\.)*)\"", blk, re.M)
    return m.group(1).replace('\\"', '"').replace("\\n", " ") if m else None


def scalar(src: str, key: str) -> str | None:
    m = re.search(rf"^\t{key}:\s*\"([^\"]*)\"", src, re.M)
    return m.group(1) if m else None


def parse_set(path: Path) -> dict:
    src = path.read_text(encoding="utf-8", errors="replace")
    return {
        "id": scalar(src, "id"),
        "name": lang(block(src, "name"), "en"),
        "abbrev": lang(block(src, "abbreviations"), "official"),
        "released": scalar(src, "releaseDate"),
    }


def pokemon_text(src: str) -> str:
    """A Pokemon's rules text is its Abilities and attacks. Judges ask about those."""
    parts = []
    for key, label in (("abilities", "Ability"), ("attacks", "Attack")):
        blk = block(src, key)
        if not blk:
            continue
        # Each entry is `{ ... name: {...}, effect: {...} ... }`. Split on the
        # entry boundary, then read the English name and effect of each.
        for entry in re.split(r"\n\t\t?\},\s*\{", blk):
            name = lang(block("\t" + entry.replace("\n\t\t", "\n\t"), "name") or "", "en") \
                or re.search(r'name:\s*\{[^}]*?en:\s*"((?:[^"\\]|\\.)*)"', entry, re.S)
            if hasattr(name, "group"):
                name = name.group(1)
            eff = re.search(r'effect:\s*\{[^}]*?en:\s*"((?:[^"\\]|\\.)*)"', entry, re.S)
            dmg = re.search(r'damage:\s*"?([0-9+×x-]+)"?', entry)
            if name or eff:
                line = f"{label} {name or ''}".strip()
                if dmg and label == "Attack":
                    line += f" ({dmg.group(1)} damage)"
                if eff:
                    line += f": {eff.group(1)}"
                parts.append(line)
    return "\n".join(parts)


def moves(src: str) -> list[dict]:
    """Every Ability and attack on the card, named in en/pt/es."""
    out = []
    for key, kind in (("abilities", "ability"), ("attacks", "attack")):
        blk = block(src, key)
        if not blk:
            continue
        for entry in re.split(r"\n\t\t?\},\s*\{", blk):
            names = {}
            for code in ("en", "pt", "es"):
                m = re.search(rf'name:\s*\{{[^}}]*?\b{code}:\s*"((?:[^"\\]|\\.)*)"', entry, re.S)
                names[code] = m.group(1).replace('\\"', '"') if m else None
            eff = re.search(r'effect:\s*\{[^}]*?\ben:\s*"((?:[^"\\]|\\.)*)"', entry, re.S)
            if names["en"]:
                out.append({"kind": kind, **names,
                            "effect_en": eff.group(1).replace('\\"', '"') if eff else None})
    return out


def parse_card(path: Path, sets: dict[str, dict]) -> dict | None:
    src = path.read_text(encoding="utf-8", errors="replace")
    name_blk = block(src, "name")
    name = lang(name_blk, "en")
    if not name:
        return None
    set_key = str(path.parent)
    s = sets.get(set_key) or {}
    category = scalar(src, "category")
    if category == "Pokemon":
        text = pokemon_text(src)
    else:
        text = lang(block(src, "effect"), "en")
    local = path.stem
    return {
        "id": f"{s.get('id')}-{local}" if s.get("id") else f"{path.parent.name}-{local}",
        "name": name, "name_pt": lang(name_blk, "pt"), "name_es": lang(name_blk, "es"),
        "set_id": s.get("id"), "set_name": s.get("name") or path.parent.name,
        "set_abbrev": s.get("abbrev"), "released": s.get("released"),
        "local_id": local, "category": category,
        "trainer_type": scalar(src, "trainerType"),
        "regulation_mark": scalar(src, "regulationMark"),
        "printed_text": text,
        "moves": moves(src) if category == "Pokemon" else [],
    }


def main() -> None:
    if not REPO.exists():
        sys.exit("clone first: git clone --depth 1 https://github.com/tcgdex/cards-database corpus/raw/tcgdex")
    # Pokemon TCG Pocket is a different game with different rules. Its cards
    # share names with real ones — a judge asking about Latias must never get the
    # Pocket printing — so the whole series is excluded, not filtered later.
    EXCLUDE_SERIES = {"Pokémon TCG Pocket"}
    sets = {}
    for f in REPO.glob("*/*.ts"):
        if f.parent.name in EXCLUDE_SERIES:
            continue
        sets[str(f.with_suffix(""))] = parse_set(f)
    print(f"{len(sets)} sets (excluded: {', '.join(sorted(EXCLUDE_SERIES))})")

    db = sqlite3.connect(DB)
    db.executescript(SCHEMA)
    today = time.strftime("%Y-%m-%d")
    n = skipped = 0
    for f in REPO.glob("*/*/*.ts"):
        if f.parent.parent.name in EXCLUDE_SERIES:
            continue
        c = parse_card(f, sets)
        if not c:
            skipped += 1
            continue
        db.execute(
            "INSERT OR REPLACE INTO cards VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (c["id"], c["name"], folded(c["name"]), c["name_pt"], folded(c["name_pt"]),
             c["name_es"], folded(c["name_es"]), c["set_id"], c["set_name"], c["set_abbrev"],
             c["released"], c["local_id"], c["category"], c["trainer_type"],
             c["regulation_mark"], c["printed_text"], None, today))
        for mv in c["moves"]:
            db.execute("INSERT INTO moves VALUES (?,?,?,?,?,?,?,?,?)",
                       (c["id"], mv["kind"], mv["en"], folded(mv["en"]), mv["pt"], folded(mv["pt"]),
                        mv["es"], folded(mv["es"]), mv["effect_en"]))
        n += 1
    db.commit()
    marked = db.execute("select count(*) from cards where regulation_mark is not null").fetchone()[0]
    pt = db.execute("select count(*) from cards where name_pt is not null").fetchone()[0]
    mv = db.execute("select count(*), sum(name_pt is not null) from moves").fetchone()
    print(f"{n} cards -> {DB}  ({skipped} files skipped, {marked} with a regulation mark, {pt} with a Portuguese name)")
    print(f"{mv[0]} Abilities/attacks, {mv[1]} with a Portuguese name")


if __name__ == "__main__":
    main()
