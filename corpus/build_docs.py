"""Chunk the Play! Pokémon PDFs into searchable sections.

Output is corpus/data/documents.json, which is GITIGNORED. It holds TPCi's text
verbatim, so it is built on the machine that serves it and never committed.

Chunking is by section number, because that is how these documents are written
and how a judge cites them. "Penalty Guidelines 4.4.2" is a real reference a
person can check; "chunk 37" is not.

    python3 corpus/build_docs.py
"""

from __future__ import annotations

import json
import sys
import re
from pathlib import Path

from fetch import DOCUMENTS, RAW, revision

OUT = Path(__file__).parent / "data/documents.json"

# "4.4.2 Repeated Infractions" at the start of a line. Title must start with a
# capital, or every "3.5 damage counters" mid-sentence becomes a heading.
# Number and title on the SAME line. With \s+ the page number "23" at the top
# of a page joined the next line into a fake heading "23 Competitor with the
# fewest Prize cards"; real_section() rejected it as a page number and the text
# from there to the next real heading — the single-elimination time table — was
# silently dropped.
HEADING = re.compile(r"^(\d+(?:\.\d+){0,3})[ \t]+([A-Z][^\n]{2,80})$", re.M)

# Table-of-contents lines carry dotted leaders: "1.1 Who Is This For? ..... 5"
TOC_LINE = re.compile(r"\.{5,}\s*\d+\s*$", re.M)

MIN_BODY = 40       # below this a "section" is a stray heading or a page artefact
MAX_TOP_LEVEL = 20  # a bare number above this is a page number, not a section


def real_section(number: str) -> bool:
    """A page number and a top-level section look identical on the page.

    "5.2" is always a section. A bare "35" in a 39-page document is the page
    number that leaked onto the heading line — these documents do not have
    thirty-five top-level sections.
    """
    return "." in number or int(number) <= MAX_TOP_LEVEL


def page_text(pdf: Path) -> list[str]:
    from pypdf import PdfReader
    return [p.extract_text() or "" for p in PdfReader(str(pdf)).pages]


def is_contents(text: str) -> bool:
    return len(TOC_LINE.findall(text)) >= 3


def clean(pages: list[str]) -> str:
    """Drop cover and contents pages, and the bare page number each page opens with."""
    kept = []
    for index, text in enumerate(pages):
        if index == 0 or is_contents(text):
            continue
        lines = text.splitlines()
        if lines and lines[0].strip().isdigit():
            lines = lines[1:]
        kept.append("\n".join(lines))
    return "\n".join(kept)


# The rulebook is a consumer document: title-case headings, no section numbers.
# Its own table of contents is the only reliable list of them, so read that and
# split the body on those exact strings rather than guessing what looks like a
# heading ("Grass" and "C M Y K" both do).
TOC_ENTRY = re.compile(r"^(.+?)\s*\.{3,}\s*\d+\s*$", re.M)
NOISE = re.compile(r"WEB RULEBOOK|CMYK|^[A-Z] [A-Z] [A-Z] [A-Z]$|^P\d{4,}")


def unnumbered_sections(pdf: Path, doc: str) -> list[dict]:
    pages = page_text(pdf)
    revised = revision(pdf)
    contents = "\n".join(t for t in pages if is_contents(t))
    headings = [h.strip() for h in TOC_ENTRY.findall(contents)
                if 3 < len(h.strip()) < 70 and not NOISE.search(h)]
    if not headings:
        return []

    body = clean(pages)
    # Where each heading appears in the body, in the order the contents lists them.
    marks: list[tuple[int, str]] = []
    cursor = 0
    for heading in headings:
        # A heading is a line of its own. Matching the bare string found
        # "Special Conditions" mid-sentence in the Evolving paragraph, which
        # started that section three pages early and swallowed Attacking,
        # Pokémon Checkup and the Special Condition entries into one 10,893-char
        # chunk that no query could lift above the score floor.
        at = body.find("\n" + heading + "\n", cursor)
        at = at + 1 if at != -1 else body.find(heading, cursor)
        if at == -1:
            continue
        marks.append((at, heading))
        cursor = at + len(heading)

    out = []
    for index, (at, heading) in enumerate(marks):
        end = marks[index + 1][0] if index + 1 < len(marks) else len(body)
        text = re.sub(r"[ \t]+", " ", body[at + len(heading):end]).strip()
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = NOISE.sub("", text).strip()
        if len(text) < MIN_BODY:
            continue
        for sub_title, sub_text in split_subheadings(heading, text):
            out.append({"doc": doc, "section": sub_title, "title": sub_title,
                        "text": sub_text, "revised": revised})
    return out


# Headings inside the rulebook's "Playing the Game" chapter that the contents
# page does not list. Each becomes its own section so "devolve", "Checkup" or
# "Removing Special Conditions" can be found without the whole chapter's
# vocabulary diluting the score. Numbered turn steps ("4) Pokémon Checkup")
# are matched by pattern; the rest by exact line.
SUBHEADINGS = {
    "Special Conditions", "Asleep", "Burned", "Poisoned", "Paralyzed", "Confused",
    "Removing Special Conditions", "Other Effects",
}
# One numbered step per line. "1) Poisoned 2) Burned 3) Asleep 4) Paralyzed" is
# the Checkup order, not a heading.
STEP_HEADING = re.compile(r"^\d\) [A-Z](?:(?!\d\))[^\n]){3,60}$")


def split_subheadings(title: str, text: str) -> list[tuple[str, str]]:
    lines = text.split("\n")
    cuts = [i for i, line in enumerate(lines)
            if line.strip() in SUBHEADINGS or STEP_HEADING.match(line.strip())]
    if not cuts:
        return [(title, text)]
    out = []
    bounds = [0] + cuts + [len(lines)]
    for start, end in zip(bounds, bounds[1:]):
        chunk = lines[start:end]
        if start == 0:
            sub_title, body_lines = title, chunk
        else:
            sub_title = re.sub(r"^\d\) ", "", chunk[0].strip())
            body_lines = chunk[1:]
        body = "\n".join(body_lines).strip()
        if len(body) >= MIN_BODY:
            out.append((sub_title, body))
    return out


def sections(pdf: Path, doc: str) -> list[dict]:
    body = clean(page_text(pdf))
    revised = revision(pdf)
    marks = list(HEADING.finditer(body))
    out = []
    for index, match in enumerate(marks):
        start = match.end()
        end = marks[index + 1].start() if index + 1 < len(marks) else len(body)
        text = re.sub(r"[ \t]+", " ", body[start:end]).strip()
        text = re.sub(r"\n{3,}", "\n\n", text)
        if len(text) < MIN_BODY or not real_section(match.group(1)):
            continue
        out.append({
            "doc": doc,
            "section": match.group(1),
            "title": match.group(2).strip(),
            "text": text,
            "revised": revised,
        })
    return out


def main() -> None:
    everything = []
    for doc, (_, stem) in DOCUMENTS.items():
        pdf = RAW / f"{stem}.pdf"
        if not pdf.exists():
            print(f"{doc:28} missing — run corpus/fetch.py")
            continue
        found = (unnumbered_sections(pdf, doc) if doc == "rulebook"
                 else sections(pdf, doc))
        chars = sum(len(s["text"]) for s in found)
        print(f"{doc:28} {len(found):4} sections, {chars:,} chars, "
              f"revised {revision(pdf)}")
        everything.extend(found)

    if not everything:
        # Running this from a checkout without corpus/raw/ once wrote an empty
        # file over a documents.json that was symlinked from another checkout.
        sys.exit("no sections built — corpus/raw/ has no PDFs here; not overwriting "
                 f"{OUT}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(everything, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n{len(everything)} sections -> {OUT}  (gitignored: TPCi text)")


if __name__ == "__main__":
    main()
