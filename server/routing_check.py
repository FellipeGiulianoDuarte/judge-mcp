"""The nine routing cases every ranking change must pass. Exit 1 on any miss.

Kept as a file so the gate before a benchmark run is the same check every
time, and so a truncated display can never fail an assertion again.

`known_miss` marks a case the current ranking does not satisfy on purpose.
Two of them, same cause: under top-N overall, four short Compendium rulings
take every slot on a general mechanics question, so the rulebook section that
answers "can a Fossil be put into play during setup" (Restored Pokemon) and
the Pokemon Checkup mechanic do not place. Two fixes were measured against the
530-question benchmark - per-kind top-N (-12) and a reserved rulebook slot
(-7) - and both lost more elsewhere than they gained here. The misses are
accepted, printed with a ~ so they stay visible, and are not gate failures.
The model still sees the card text and related rulings on these; what it
does not see is the general rule stated plainly.
"""
import sys

import repeat_guard
from lookup import lookup

R = (None, "rulebook", "compendium")
K = ("exceptions", "mechanics", "ruling", "document")
CASES = [
    ("jogador chegou 12 minutos atrasado", "player arrived late tardiness match start",
     {"docs": ("penalty-guidelines",)}, "5.2", False),
    ("como calcula resistance no tiebreak?", "tiebreaker resistance opponent win percentage standings",
     {"docs": ("tournament-rules-handbook", "tcg-tournament-handbook")}, "5.3.3.1", False),
    ("can a Fossil be put into play during setup", "fossil setup basic pokemon active bench",
     {"kinds": K, "docs": R}, "Restored", True),    # known miss: see below
    ("KO por veneno ativa a habilidade?", "poison knock out checkup trigger ability",
     {"kinds": K, "docs": R}, "Checkup", True),          # known miss under top-N overall
    ("Super Rod from Neo Genesis how many cards", "Super Rod errata printing text",
     {"kinds": K, "docs": R}, "Super Rod", False),
    ("Quilava Ability search Ethan Adventure all copies in discard",
     "search deck public knowledge all copies discard pile no effect", {"kinds": K, "docs": R}, "Bonded", False),
    ("attack knocks out least remaining HP undamaged pokemon", "least remaining HP knocked out undamaged",
     {"kinds": K, "docs": R}, "Bring Down", False),
    ("penalty for wearing a hat at a Regional", "hat clothing dress code apparel",
     {"docs": ("penalty-guidelines",)}, "NO MATCH", False),
    ("penalty for wearing a hat at a Regional", "hat clothing dress code apparel", {}, "NO MATCH", False),
]


def heads(r: dict) -> str:
    return " | ".join((h.get("citation") or h["heading"])
                      for k in ("exceptions", "rulings", "mechanics", "documents") for h in r.get(k, []))


def main() -> int:
    repeat_guard.reset()
    required = passed = 0
    for q, t, kw, want, known_miss in CASES:
        repeat_guard.reset()
        r = lookup(q, t, **kw)
        got = "NO MATCH" if r["no_match"] else heads(r)
        hit = (want == "NO MATCH") == r["no_match"] and (r["no_match"] or want.lower() in got.lower())
        tag = "ok " if hit else ("~  " if known_miss else "X  ")
        print(f"{tag}{got[:96]}")
        if not known_miss:
            required += 1
            passed += hit
    print(f"{passed}/{required} required cases pass")
    return 0 if passed == required else 1


if __name__ == "__main__":
    sys.exit(main())
