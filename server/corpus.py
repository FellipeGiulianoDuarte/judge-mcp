"""Load the two corpus files into searchable sections.

Both files are Markdown with `## ` headings. The heading is the search key — it
names the thing people ask about. HTML comments are editor notes and are stripped
before anything is indexed, so nothing marked NEEDS REVIEW leaks into an answer
as if it were prose.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

CORPUS_DIR = Path(__file__).parent.parent / "corpus"
COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
META_LINE = re.compile(r"^(Source|Overrides):\s*(.*)$", re.MULTILINE)


DOCUMENTS = CORPUS_DIR / "data/documents.json"
COMPENDIUM = CORPUS_DIR / "data/compendium.json"


@dataclass(frozen=True)
class Section:
    kind: str                    # "exceptions" | "mechanics" | "document"
    heading: str
    body: str
    overrides: str | None = None
    source: str | None = None
    needs_review: bool = False
    doc: str | None = None       # documents only: which handbook
    number: str | None = None    # documents only: the citable section number
    revised: str | None = None   # documents only: LAST REVISION on the PDF

    @property
    def text(self) -> str:
        return f"{self.heading}\n{self.body}"

    @property
    def citation(self) -> str | None:
        if self.doc and self.number:
            return f"{self.doc} {self.number}"
        return None


def _parse(path: Path, kind: str) -> list[Section]:
    if not path.exists():
        return []
    raw = COMMENT.sub("", path.read_text(encoding="utf-8"))
    sections = []
    for chunk in re.split(r"^## ", raw, flags=re.MULTILINE)[1:]:
        heading, _, body = chunk.partition("\n")
        meta = dict(META_LINE.findall(body))
        clean = META_LINE.sub("", body).strip()
        sections.append(Section(
            kind=kind,
            heading=heading.strip(),
            body=clean,
            overrides=meta.get("Overrides"),
            source=meta.get("Source"),
            needs_review="NEEDS REVIEW" in body,
        ))
    return sections


def _documents() -> list[Section]:
    """Official text, chunked by corpus/build_docs.py. Absent until it is run."""
    if not DOCUMENTS.exists():
        return []
    return [
        Section(kind="document", heading=row["title"], body=row["text"],
                doc=row["doc"], number=row["section"], revised=row["revised"])
        for row in json.loads(DOCUMENTS.read_text(encoding="utf-8"))
    ]


def _rulings() -> list[Section]:
    """Compendium rulings, loaded for inference. Absent until corpus/compendium.py runs.

    Each ruling is a question judges actually asked and TPCi's answer, so the
    heading is the question — that is what a new question will resemble. The
    ruling's own source and date ride along; a 2000 WotC chat ruling and a 2026
    TPCi Rules Team ruling are both official, but a reader should see which.
    """
    if not COMPENDIUM.exists():
        return []
    data = json.loads(COMPENDIUM.read_text(encoding="utf-8"))
    rows = data["rulings"] if isinstance(data, dict) else data   # both shapes
    return [
        Section(kind="ruling", heading=r["question"], body=r["answer"],
                source=r.get("source"), doc="compendium",
                number=r.get("tags") or r["category"], revised=r.get("date"))
        for r in rows
        if r.get("question") and r.get("answer")
    ]


def load() -> list[Section]:
    """Exceptions first — callers that truncate should keep them."""
    return (_parse(CORPUS_DIR / "exceptions.md", "exceptions")
            + _parse(CORPUS_DIR / "mechanics.md", "mechanics")
            + _rulings()
            + _documents())


if __name__ == "__main__":
    from collections import Counter

    sections = load()
    print(Counter(s.kind for s in sections))
    for s in sections:
        if s.kind == "document":
            continue
        flag = " [NEEDS REVIEW]" if s.needs_review else ""
        print(f"{s.kind:11} {s.heading}{flag}")
