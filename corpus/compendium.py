"""Load the Pokémon Rulings Compendium for inference.

This is the ruling layer the corpus was missing. The rulebook is a beginner
document; the questions judges ask each other — can you use a search Ability
when every copy is provably in the discard, does "least remaining HP" target an
undamaged Pokémon — are answered by rulings, and the Compendium is where TPCi's
rulings are collected. Loaded for inference only, never for training, and never
redistributed: corpus/data/compendium.json is gitignored.

Cloudflare rejects a bare HTTP client, so this drives a real browser. One pass
over ~190 category pages, at a polite pace.

    python3 corpus/compendium.py            # full load
    python3 corpus/compendium.py --check    # print the homepage count + date only
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

OUT = Path(__file__).parent / "data/compendium.json"
BASE = "https://compendium.pokegym.net"
CATEGORIES = ["1-errata", "2-meta-rulings", "3-attacks", "4-abilities",
              "5-trainers", "6-energy", "7-gameplay", "8-team-battle"]
PAUSE = 1.5

SOURCE = re.compile(r"Source:\s*(.+?)\s*(?:\((\d{4}-\d{2}-\d{2})\))?\s*$", re.S)


def fetch_page(url: str):
    from scrapling.fetchers import StealthyFetcher
    page = StealthyFetcher.fetch(url, headless=True, network_idle=True)
    if page.status != 200:
        raise RuntimeError(f"{page.status} for {url}")
    return page


def fetch_text(url: str) -> str:
    return fetch_page(url).get_all_text(ignore_tags=("script", "style", "nav", "footer"))


POST_ID = re.compile(r"\bpost-(\d+)\b")


TRAILING = {"View relevant cards", "|", "Share ruling"}


def parse_rulings(page, category: str) -> list[dict]:
    """One <article class="ruling post-NNNN"> per ruling, ten per page.

    Inside, in order: a tag block ("Trainers", "»", "Roto-Stick", "|", ...),
    then the body, then "Source:" and the source text. The tag block ends one
    line after the last "»" — structural, so it does not matter how long a
    question is or whether it ends in "?".

    Most rulings are a question line followed by an answer. Errata and
    meta-rulings are a single statement: "The original text for Sacred Ash
    was ..." with no question. For those the heading is the tag (the card
    name), which is what a lookup for "Sacred Ash" should hit.
    """
    out = []
    for art in page.css("article.ruling"):
        m = POST_ID.search(art.attrib.get("class", ""))
        rid = m.group(1) if m else None
        lines = [l.strip() for l in art.get_all_text(ignore_tags=("script", "style")).splitlines() if l.strip()]
        src_i = next((i for i, l in enumerate(lines) if l.startswith("Source:")), None)
        if src_i is None:
            continue
        arrows = [i for i in range(src_i) if lines[i] == "»"]
        if not arrows:
            continue
        body_start = arrows[-1] + 2
        body = lines[body_start:src_i]
        if not body:
            continue
        tags = " ".join(l for l in lines[:body_start] if l not in ("»", "|"))
        source_lines = [l for l in lines[src_i:] if l not in TRAILING]
        source_text = re.sub(r"\s+", " ", " ".join(source_lines).replace("Source:", "", 1)).strip()
        date = re.search(r"\((\d{4}-\d{2}-\d{2})\)", source_text)
        if len(body) >= 2:
            question, answer = body[0], " ".join(body[1:])
        else:
            # Single statement — errata, meta-rulings. The heading is the most
            # specific tag: the card name for errata ("Sacred Ash"), the topic for
            # a meta-ruling ("*Attacks in General"). Never the category's own
            # name — a heading of "Meta-Rulings" on every meta-ruling matches
            # nothing anyone asks.
            cat_name = category.split("-", 1)[1].replace("-", " ").lower()
            tag_lines = [lines[i + 1] for i in arrows if i + 1 < body_start]
            specific = [t for t in tag_lines if t.lower() not in (cat_name, "meta rulings", "errata")]
            question, answer = (specific[0] if specific else tag_lines[-1]), body[0]
        out.append({
            "id": rid, "category": category, "tags": tags,
            "question": question, "answer": answer,
            "source": source_text, "date": date.group(1) if date else None,
        })
    return out


def homepage_state() -> dict:
    """The two numbers the Compendium publishes on its front page."""
    t = fetch_text(BASE + "/")
    # The date sits on the line after "Latest update:", so allow whitespace.
    m = re.search(r"currently ([\d,]+) rulings\.\s*Latest update:\s*([A-Za-z]+ \d{1,2}, \d{4})", t)
    if not m:
        sys.exit("homepage layout changed — freshness check needs updating")
    count, updated = m.groups()
    return {"rulings": int(count.replace(",", "")), "latest_update": updated}


def load_all(limit_pages: int | None = None, only: list[str] | None = None) -> list[dict]:
    rulings = []
    seen = set()
    for cat in (only or CATEGORIES):
        page_no, pages_here = 1, 0
        while True:
            url = f"{BASE}/category/{cat}/" + (f"page/{page_no}/" if page_no > 1 else "")
            try:
                page = fetch_page(url)
            except Exception as exc:
                print(f"  {cat} p{page_no}: {exc} — stopping this category", file=sys.stderr)
                break
            found = parse_rulings(page, cat)
            new = [r for r in found if r["id"] not in seen]
            for r in new:
                seen.add(r["id"])
            rulings += new
            pages_here += 1
            print(f"\r  {cat:16} page {page_no:3}  +{len(new):2}  total {len(rulings)}", end="", flush=True)
            # Stop on the END of a category — an empty page or the 404 above —
            # never on "nothing new here". A page whose ten rulings were all seen
            # under another category (Energy rulings are mostly also Attacks
            # rulings) is not the end; stopping there skipped its later pages.
            if not found or (limit_pages and pages_here >= limit_pages):
                break
            page_no += 1
            time.sleep(PAUSE)
        print()
    return rulings


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="print the homepage count and date")
    ap.add_argument("--stale", action="store_true",
                    help="exit 1 if the homepage count or date differs from the local file")
    ap.add_argument("--limit-pages", type=int, default=None, help="per category, for testing")
    ap.add_argument("--only", nargs="*", default=None,
                    help="reload just these categories and merge by id into the existing file")
    args = ap.parse_args()
    if args.check:
        t = fetch_text(BASE + "/")
        # The date sits on the line after "Latest update:", so allow whitespace.
        m = re.search(r"currently ([\d,]+) rulings\.\s*Latest update:\s*([A-Za-z]+ \d{1,2}, \d{4})", t)
        if not m:
            sys.exit("homepage layout changed — freshness check needs updating")
        count, updated = m.groups()
        print(json.dumps({"rulings": int(count.replace(",", "")), "latest_update": updated}))
        return
    live = homepage_state()
    rulings = load_all(args.limit_pages, args.only)
    if args.only and OUT.exists():
        existing = json.loads(OUT.read_text(encoding="utf-8"))
        existing = existing["rulings"] if isinstance(existing, dict) else existing
        by_id = {r["id"]: r for r in existing}
        by_id.update({r["id"]: r for r in rulings})       # reloaded categories win
        rulings = list(by_id.values())
        print(f"merged into existing file: {len(rulings)} total")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    # Record what the homepage said at build time, so --stale can compare later.
    OUT.write_text(json.dumps({"_meta": {**live, "built": time.strftime("%Y-%m-%d")},
                               "rulings": rulings}, ensure_ascii=False, indent=1), encoding="utf-8")
    dated = sum(1 for r in rulings if r["date"])
    print(f"\n{len(rulings)} rulings -> {OUT}  ({dated} dated; gitignored, inference only)")


if __name__ == "__main__":
    main()
