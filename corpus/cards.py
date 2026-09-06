"""Build the card table from TCGdex into SQLite.

Card text and images are not redistributed here — this script fetches them onto
the machine that runs it. What it stores is a local cache, rebuilt on demand.

WHAT THIS TABLE IS NOT: a source for what a card does. `printed_text` is the text
on the physical card, and for any reprinted card that is not what you play with —
the newest printing's text replaces it on every earlier one, because a card is
identified by its name. Super Rod (Neo Genesis, 2000) prints a coin-flip effect and
is played as the 2023 "shuffle up to 3". Governing text lives in
corpus/exceptions.md. Never answer "what does this card do" from this table alone.

Why not trust TCGdex's own `legal` field: it answers "right now" only. A judge
asking about an event two weeks ago, or about the fifteen days between the paper
and digital rotation dates, needs a date-aware answer. So the mark is stored and
server/legality.py computes from it. TCGdex's `legal` is kept alongside as a
cross-check — when the two disagree, one of them is wrong and you want to know.

    python3 corpus/cards.py --sets sv02,sv03      # a few sets
    python3 corpus/cards.py --all                 # everything, slow
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API = "https://api.tcgdex.net/v2/en"
DB = Path(__file__).parent / "cards.sqlite"
PAUSE = 0.1          # be a polite guest on a free community API
RETRIES = 3

SCHEMA = """
CREATE TABLE IF NOT EXISTS cards (
    id              TEXT PRIMARY KEY,   -- e.g. sv02-188
    name            TEXT NOT NULL,
    name_folded     TEXT NOT NULL,      -- lowercase, accents stripped, for matching
    set_id          TEXT,
    set_name        TEXT,
    local_id        TEXT,               -- collector number within the set
    category        TEXT,               -- Pokemon | Trainer | Energy
    trainer_type    TEXT,
    regulation_mark TEXT,               -- NULL on cards older than the marks
    printed_text    TEXT,               -- what the card in their hand says
    tcgdex_legal    TEXT,               -- their verdict, as JSON, for cross-checking
    fetched_on      TEXT
);
CREATE INDEX IF NOT EXISTS cards_by_name ON cards (name_folded);
"""


def folded(text: str) -> str:
    import unicodedata
    n = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in n if not unicodedata.combining(c))


def get(path: str) -> object:
    for attempt in range(RETRIES):
        try:
            with urllib.request.urlopen(f"{API}/{path}", timeout=30) as r:
                return json.loads(r.read())
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt == RETRIES - 1:
                raise SystemExit(f"TCGdex unreachable at {path}: {exc}")
            time.sleep(2 ** attempt)
    return None


def build(set_ids: list[str] | None, db_path: Path = DB) -> int:
    db = sqlite3.connect(db_path)
    db.executescript(SCHEMA)
    today = time.strftime("%Y-%m-%d")

    sets = get("sets")
    assert isinstance(sets, list)
    wanted = [s for s in sets if set_ids is None or s["id"] in set_ids]
    if set_ids and len(wanted) != len(set_ids):
        missing = set(set_ids) - {s["id"] for s in wanted}
        print(f"unknown set ids: {', '.join(sorted(missing))}", file=sys.stderr)

    written = 0
    for index, s in enumerate(wanted, 1):
        detail = get(f"sets/{s['id']}")
        assert isinstance(detail, dict)
        stubs = detail.get("cards", [])
        print(f"[{index}/{len(wanted)}] {s['name']}: {len(stubs)} cards", flush=True)
        for stub in stubs:
            card = get(f"cards/{stub['id']}")
            assert isinstance(card, dict)
            db.execute(
                "INSERT OR REPLACE INTO cards VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (card["id"], card["name"], folded(card["name"]),
                 card.get("set", {}).get("id"), card.get("set", {}).get("name"),
                 card.get("localId"), card.get("category"), card.get("trainerType"),
                 card.get("regulationMark"), card.get("effect"),
                 json.dumps(card.get("legal")), today))
            written += 1
            time.sleep(PAUSE)
        db.commit()
    db.close()
    return written


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--sets", help="comma-separated set ids, e.g. sv02,sv03")
    g.add_argument("--all", action="store_true", help="every set — thousands of requests")
    ap.add_argument("--db", type=Path, default=DB)
    args = ap.parse_args()

    ids = None if args.all else [s.strip() for s in args.sets.split(",")]
    n = build(ids, args.db)
    print(f"\n{n} cards -> {args.db}")


if __name__ == "__main__":
    main()
