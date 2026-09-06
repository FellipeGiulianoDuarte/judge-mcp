"""Is this printing legal in this format, on this date?

Not a model question. Four values decide it: the printing's regulation mark, the
format, the date, and whether the event is paper or digital. A query gets it right
every time; prose retrieval gets reprints and rotation dates wrong.

Two things this deliberately keeps apart:

  legality        — can the card be played
  governing text  — what the card does, which may not be what it says

They are independent. A 2000 Super Rod is legal in Expanded AND is played with
2023 errata text. Governing text lives in corpus/exceptions.md, not here.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Literal

Format = Literal["standard", "expanded", "unlimited", "glc"]

_DATA = json.loads((Path(__file__).parent.parent / "corpus/data/formats.json").read_text())
FORMATS: dict = _DATA["formats"]


def _iso(value: str | date | None) -> date:
    if value is None:
        return date.today()
    return value if isinstance(value, date) else date.fromisoformat(value)


def rotation_in_force(fmt: Format, on: date, digital: bool) -> dict | None:
    """The most recent rotation that had taken effect by `on`.

    Paper and digital rotate on different days — fifteen apart in 2026 — so a
    question about an event inside that window has two different right answers.
    """
    key = "effective_digital" if digital else "effective_paper"
    applicable = [
        r for r in FORMATS.get(fmt, {}).get("rotations", [])
        if _iso(r[key]) <= on
    ]
    return max(applicable, key=lambda r: _iso(r[key])) if applicable else None


def is_legal(
    mark: str | None,
    fmt: Format,
    on: str | date | None = None,
    digital: bool = False,
    card_name: str | None = None,
) -> dict:
    """Return a verdict plus the reason, so the answer can explain itself.

    `mark` is the regulation mark printed at the card's bottom left, or None for
    cards old enough to predate marks.
    """
    on = _iso(on)
    spec = FORMATS.get(fmt)
    if spec is None:
        return {"legal": None, "reason": f"Unknown format {fmt!r}.", "as_of": on.isoformat()}

    if card_name and card_name in spec.get("banned", []):
        return {"legal": False, "reason": f"{card_name} is banned in {fmt}.",
                "as_of": on.isoformat()}

    if spec.get("everything_legal"):
        return {"legal": True, "reason": f"Every card is legal in {fmt}.",
                "as_of": on.isoformat()}

    if "_todo" in spec:
        return {"legal": None,
                "reason": f"Legality data for {fmt} is not loaded yet.",
                "as_of": on.isoformat()}

    rotation = rotation_in_force(fmt, on, digital)
    if rotation is None:
        return {"legal": None,
                "reason": f"No {fmt} rotation data covering {on.isoformat()}.",
                "as_of": on.isoformat()}

    where = "digital play" if digital else "in-person events"
    if mark is None:
        return {"legal": False,
                "reason": f"This printing has no regulation mark, so it is not "
                          f"legal in {fmt} for {where}.",
                "as_of": on.isoformat()}

    mark = mark.upper()
    if mark in rotation["legal_marks"]:
        return {"legal": True,
                "reason": f"Regulation mark {mark} is legal in {fmt} for {where}.",
                "as_of": on.isoformat(), "source": rotation.get("source")}
    if mark in rotation.get("rotated_out", []):
        effective = rotation["effective_digital" if digital else "effective_paper"]
        return {"legal": False,
                "reason": f"Regulation mark {mark} left {fmt} on {effective} "
                          f"for {where}.",
                "as_of": on.isoformat(), "source": rotation.get("source")}
    if spec.get("future_marks_legal") and mark > max(rotation["legal_marks"]):
        return {"legal": True,
                "reason": f"Regulation mark {mark} is newer than the last rotation, "
                          f"so it is legal in {fmt}.",
                "as_of": on.isoformat()}
    return {"legal": False,
            "reason": f"Regulation mark {mark} is not in the {fmt} legal set "
                      f"({', '.join(rotation['legal_marks'])}).",
            "as_of": on.isoformat(), "source": rotation.get("source")}


def all_formats(mark: str | None, on: str | date | None = None,
                digital: bool = False, card_name: str | None = None) -> dict:
    return {f: is_legal(mark, f, on, digital, card_name)  # type: ignore[arg-type]
            for f in ("standard", "expanded", "unlimited")}
