"""Download the Play! Pokémon rules documents.

These are the documents TPCi publishes for judges to read. They are not
redistributed here — this fetches them onto the machine that runs it, into
corpus/raw/, which is gitignored.

pokemon.com sits behind bot protection that rejects a bare scripted request and
rate-limits rapid ones. So: browser headers, one at a time, with a pause. If it
still refuses, the script says which files to download by hand — clicking the
link in a browser is how a judge gets them anyway.

    python3 corpus/fetch.py
    python3 corpus/fetch.py --check     # report revision dates, download nothing
"""

from __future__ import annotations

import argparse
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

RAW = Path(__file__).parent / "raw"
BASE = ("https://www.pokemon.com/static-assets/content-assets/cms2/pdf/"
        "play-pokemon/rules")
TCG_BASE = ("https://www.pokemon.com/static-assets/content-assets/cms2/pdf/"
            "trading-card-game/rulebook")
LANDING_PLAY = ("https://www.pokemon.com/us/play-pokemon/about/"
                "tournaments-rules-and-resources/")

# The three handbooks say how an EVENT runs and what the penalties are. The
# rulebook says how the GAME works — without it the corpus cannot answer a card
# question at all, which is how it got left out and why that showed up as the
# model refusing every mechanics question it had been getting right.
DOCUMENTS = {
    "rulebook": ("rulebook", "pbl_rulebook_en"),
    "tournament-rules-handbook": ("play", "play-pokemon-tournament-rules-handbook-en"),
    "tcg-tournament-handbook": ("play", "play-pokemon-tcg-tournament-handbook-en"),
    "penalty-guidelines": ("play", "play-pokemon-penalty-guidelines-en"),
}
LANDINGS = {"play": LANDING_PLAY, "rulebook": "https://www.pokemon.com/us/pokemon-tcg/rules"}
BASES = {"play": BASE, "rulebook": TCG_BASE}

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 "
                   "Safari/537.36"),
    "Accept": "application/pdf,*/*",
    "Accept-Language": "en-US,en;q=0.9",
}

PAUSE = 4.0      # between documents; back-to-back requests get blocked
RETRIES = 3


def revision(pdf: Path) -> str | None:
    """The 'LAST REVISION: <date>' line these documents carry on page 1.

    This is the freshness signal: re-fetch when it moves, not on a timer.
    """
    try:
        from pypdf import PdfReader
        head = (PdfReader(str(pdf)).pages[0].extract_text() or "")
    except Exception:
        return None
    # Handbooks say "LAST REVISION: September 1, 2026"; the rulebook says
    # "LAST UPDATED: JULY 2026" on its cover. Both are the freshness signal.
    for pattern in (r"LAST REVISION:?\s*([A-Za-z]+ \d{1,2},? \d{4})",
                    r"LAST UPDATED:?\s*([A-Za-z]+,? \d{4})"):
        found = re.search(pattern, head, re.I)
        if found:
            return found.group(1).strip()
    return None


def download(slug: str, where: str, stem: str) -> Path | None:
    target = RAW / f"{stem}.pdf"
    request = urllib.request.Request(
        f"{BASES[where]}/{stem}.pdf",
        headers={**HEADERS, "Referer": LANDINGS[where]})
    for attempt in range(RETRIES):
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                body = response.read()
        except (urllib.error.URLError, TimeoutError) as exc:
            print(f"  {slug}: {exc}")
            body = b""
        if body.startswith(b"%PDF"):
            RAW.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
            print(f"  {slug}: {len(body):,} bytes, revised {revision(target) or 'unknown'}")
            return target
        wait = PAUSE * (attempt + 2)
        print(f"  {slug}: blocked (got {len(body)} bytes of HTML), waiting {wait:.0f}s")
        time.sleep(wait)
    print(f"  {slug}: FAILED — download it by hand from {LANDINGS[where]}\n"
          f"             and save it as corpus/raw/{stem}.pdf")
    return None


def check() -> None:
    """What is on disk, and how old."""
    for slug, (_, stem) in DOCUMENTS.items():
        pdf = RAW / f"{stem}.pdf"
        if not pdf.exists():
            print(f"  {slug:28} missing")
        else:
            print(f"  {slug:28} revised {revision(pdf) or 'unknown'}  "
                  f"({pdf.stat().st_size:,} bytes)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="report what is on disk")
    args = ap.parse_args()
    if args.check:
        check()
        return
    for index, (slug, (where, stem)) in enumerate(DOCUMENTS.items()):
        if index:
            time.sleep(PAUSE)
        download(slug, where, stem)


if __name__ == "__main__":
    main()
