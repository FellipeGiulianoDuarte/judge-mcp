"""Keyword search over the two corpus files.

No embeddings, for now. The corpus is small enough that scored term overlap
mostly works and a wrong result is obvious when you read it.

WHERE THIS APPROACH RUNS OUT, measured 2026-09-05 on the pilot set. Ask "is
additional damage an effect of the attack" and the exception "Alternate attack
costs cannot be modified" scores 20.2 against 12.2 for the rulebook section that
actually answers. Both are about attacks, costs, damage and effects; they share
nearly every content word while being about different things. No threshold or
weighting fixes that — term overlap matches vocabulary, not meaning. Card
interaction questions are where it fails; penalty and tournament questions route
correctly because their vocabulary is distinctive.

That is the signal for adding embeddings, and the benchmark produced it rather
than the decision being made up front.

Cross-language note: judges ask in Portuguese and Spanish; the corpus is English
because the rules are English. Term matching cannot bridge that, so the caller
supplies English search terms alongside the verbatim question — Claude is good at
producing them and the server does not need a translation model.
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter, defaultdict

from corpus import Section, load

# Exceptions beat mechanics when both match: an exception exists precisely
# because the general rule gives the wrong answer for that case.
EXCEPTION_BOOST = 1.6
HEADING_BOOST = 2.5
# Two thresholds. The hand-written files are few and specific, so a weak hit is
# still probably right. The official documents are 272 sections of prose about
# tournaments, so almost any question grazes something — a much higher bar is
# what keeps "penalty for wearing a hat" honest.
MIN_SCORE = 6.0
MIN_SCORE_DOCUMENT = 9.0
MIN_SCORE_PRINCIPLE = 4.0   # general rules are short and use general words; see lookup()
PRINCIPLES_N = 2

DOMAIN_STOP_SHARE = 0.12   # in >12% of a kind's sections -> generic for that kind
MIN_DISTINCTIVE_TERMS = 2  # one shared rare word is a coincidence, not a match
MIN_KIND_SECTIONS = 30     # fewer than this and a kind's stopwords are not learnable
# A share-of-distinctive-terms floor was tried here and reverted: it fixed none
# of the garbage hits and broke Tardiness and tiebreaker routing. The garbage
# hits all had one cause — the question named a card that was not in the corpus
# — and that is fixed by loading the cards, not by scoring. Keyword scoring has
# now been tuned four times; the next change here should be embeddings.
MAX_RESULTS = 4
# Top-N per kind was tried here (2 rulings + 1 mechanic + 2 documents) and
# measured worse: 254 -> 242 right, refusals 33 -> 42, open-question refusals
# doubled. For a ruling-heavy question it swapped two strong rulings for a
# weak mechanic and two weak documents, and the repeat guard then fired more
# often on the two rulings that were left. Diversity diluted the answer.
# Top-N overall is what measured best.

STOPWORDS = {
    "the", "a", "an", "is", "it", "of", "to", "in", "on", "and", "or", "if",
    "can", "do", "does", "i", "my", "you", "your", "that", "this", "what",
    "when", "with", "for", "be", "are", "was", "not", "no", "at", "as", "by",
}


def stem(token: str) -> str:
    """Light suffix stripping so inflections share a key.

    Without it "concession" never matched the handbook's "Concessions" heading,
    and "devolve" never matched the Glossary's "devolved". This is not a real
    stemmer — it strips plural, -ed, -ing and a final -e, and turns a final -y
    into -i so "ability"/"abilities" agree. Collisions ("game"/"gam") are
    harmless because index and query go through the same function.
    """
    t = token
    if len(t) >= 6 and t.endswith("ing"):
        t = t[:-3]
    elif len(t) >= 5 and t.endswith("ed"):
        t = t[:-2]
    elif len(t) >= 4 and t.endswith("s") and not t.endswith(("ss", "us", "is")):
        t = t[:-1]
    if len(t) >= 5 and t.endswith("e"):
        t = t[:-1]
    if len(t) >= 4 and t.endswith("y"):
        t = t[:-1] + "i"
    return t


def normalise(text: str) -> list[str]:
    """Lowercase, strip accents, split on non-letters, stem. 'involução' -> 'involucao'."""
    folded = unicodedata.normalize("NFKD", text.lower())
    folded = "".join(c for c in folded if not unicodedata.combining(c))
    return [stem(t) for t in re.split(r"[^a-z0-9]+", folded) if t and t not in STOPWORDS]


# Embeddings were built and wired here against gemini-embedding-2, then removed
# before being measured. Not on quality - on cost direction. Every lookup would
# have made a call to Google, a per-query cost on the operator that scales with
# adoption, where the connector's whole shape is that the judge's own model pays
# and the server is a flat VPS. If semantic retrieval is revisited it must be a
# LOCAL model on the VPS (sentence-transformers, a few hundred MB, CPU) so the
# marginal cost of a lookup stays zero. The scoring hook below is kept inert.
class Index:
    """Term-overlap scoring with inverse document frequency, plus semantic
    similarity when corpus/data/embeddings.npz exists (corpus/embed.py builds it).

    Keyword scoring alone was measured at its ceiling: five ranking changes, none
    improved the benchmark. The failures share one shape - question and answer
    share meaning but not words. Embeddings are the change built for that shape.
    """

    def __init__(self, sections: list[Section] | None = None):
        self.sections = sections if sections is not None else load()
        self.tokens = [Counter(normalise(s.text)) for s in self.sections]
        self.vectors = None   # see the EMBEDDINGS note above
        # Without length normalisation the rulebook's Glossary wins everything:
        # it is long, so it contains almost every term, so it always matches.
        # Scores are divided by this, which is 1.0 at the average section length
        # and grows slowly with size. The floor is deliberately close to 1: the
        # hand-written exceptions are the shortest things in the corpus, so a
        # generous short-section bonus stacks with EXCEPTION_BOOST and lifts an
        # unrelated exception over the document that actually answers.
        lengths = [max(sum(t.values()), 1) for t in self.tokens]
        mean = sum(lengths) / max(len(lengths), 1)
        self.length_penalty = [max(0.75, 0.75 + 0.25 * (n / mean)) for n in lengths]
        self.headings = [set(normalise(s.heading)) for s in self.sections]
        n = max(len(self.sections), 1)
        seen = Counter(t for doc in self.tokens for t in doc)
        # Rare terms carry the signal. "energy" is everywhere; "devolution" is not.
        self.idf = {t: math.log(1 + n / c) for t, c in seen.items()}
        # Domain stopwords, learned PER SOURCE KIND. Learned over the whole corpus
        # they moved every time the corpus changed shape: adding 1,800 short
        # rulings dropped "penalty", "player", "regional" below the share
        # threshold, and a penalty-guidelines section suddenly cleared the floor
        # on those words alone. What is generic in the Penalty Guidelines does
        # not depend on how many Compendium rulings exist.
        by_kind: dict[str, list[Counter]] = defaultdict(list)
        for sec, toks in zip(self.sections, self.tokens):
            by_kind[sec.kind].append(toks)
        # A kind with only a handful of sections cannot teach us what is generic
        # in it: with 3 mechanics sections, any word in one of them is in 33% and
        # the whole vocabulary became "generic", so every mechanics hit had zero
        # distinctive terms and was filtered out. Below MIN_KIND_SECTIONS, borrow
        # the document kind's set — it is the largest and the same domain.
        self.generic_by_kind: dict[str, set[str]] = {}
        for kind, docs_ in by_kind.items():
            if len(docs_) < MIN_KIND_SECTIONS:
                continue
            cnt = Counter(t for d in docs_ for t in d)
            self.generic_by_kind[kind] = {t for t, c in cnt.items() if c / len(docs_) > DOMAIN_STOP_SHARE}
        fallback = self.generic_by_kind.get("document", set())
        for kind in by_kind:
            self.generic_by_kind.setdefault(kind, fallback)
        # Union kept for callers that want one set (the repeat guard, reports).
        self.generic = set().union(*self.generic_by_kind.values()) if self.generic_by_kind else set()

    def search(self, *parts: str,
               kinds: tuple[str, ...] | None = None,
               docs: tuple[str, ...] | None = None,
               min_score: float | None = None,
               limit: int | None = None) -> list[tuple[Section, float]]:
        query = normalise(" ".join(p for p in parts if p))
        if not query:
            return []
        sims = None   # no semantic scoring in this build; see the note on EMBEDDINGS

        scored = []
        for position, (section, tokens, heading) in enumerate(
                zip(self.sections, self.tokens, self.headings)):
            if kinds and section.kind not in kinds:
                continue
            # None in `docs` means "and the files that belong to no document",
            # so a caller can ask for the rulebook plus the hand-written notes
            # without also getting the tournament handbooks.
            if docs and section.doc not in docs:
                continue
            score = 0.0
            distinctive = 0
            generic_here = self.generic_by_kind.get(section.kind, set())
            for term in set(query):
                if term in tokens:
                    weight = self.idf.get(term, 0.0)
                    score += weight * (HEADING_BOOST if term in heading else 1.0)
                    if term not in generic_here:
                        distinctive += 1
            # One shared word is not a match. The Ability "Mind Hat" scored 20.9
            # against "penalty for wearing a hat" on the word "hat" alone — a
            # short section plus one rare word clears any numeric floor. Two
            # distinctive shared terms is the minimum for a section to be about
            # the question; Tardiness matches on four and is unaffected.
            strong_semantic = sims is not None and float(sims[position]) >= 0.72
            if distinctive < MIN_DISTINCTIVE_TERMS and not strong_semantic:
                continue
            # An exception overrides the general rule ABOUT THE THING IT NAMES.
            # Boost it only when the question shares a term with its heading —
            # "Super Rod" for a Super Rod question. Boosting on any shared body
            # word let a two-entry exceptions file win unrelated card questions
            # on "basic" alone.
            if section.kind == "exceptions":
                if any(t in heading for t in set(query) if t not in self.generic):
                    score *= EXCEPTION_BOOST
                else:
                    score *= 0.5
            score /= self.length_penalty[position]
            if sims is not None:
                # Semantic similarity, scaled onto the keyword range and added.
                # It is what lets "devolving removes Special Conditions" find the
                # rulebook section that says so in different words, and what
                # stops "is additional damage an effect" from landing on an
                # alternate-attack-cost ruling that merely shares its words.
                score += max(float(sims[position]), 0.0) * SEMANTIC_SCALE
            if score > 0:
                scored.append((section, score))
        scored.sort(key=lambda pair: pair[1], reverse=True)
        floor = {"document": MIN_SCORE_DOCUMENT}
        # Five ranking changes were measured against the 530-question benchmark
        # and none improved it: per-kind top-N (-12), a share-of-distinctive-terms
        # floor (broke routing), a reserved rulebook slot (-7), two neutral.
        # The three things that moved the number were content and behaviour,
        # not scoring: loading the Compendium (+14), the repeat guard (+11 of 42
        # in isolation), and auditing the answer key. Top-N overall is where
        # keyword ranking peaks here. The next change to retrieval should be
        # embeddings, not another weight.
        return [(s, sc) for s, sc in scored
                if sc >= (min_score if min_score is not None
                          else floor.get(s.kind, MIN_SCORE))][:limit or MAX_RESULTS]


_index: Index | None = None


def index() -> Index:
    global _index
    if _index is None:
        _index = Index()
    return _index


def lookup(question: str, terms: str = "", cards: list[str] | None = None,
           kinds: tuple[str, ...] | None = None,
           docs: tuple[str, ...] | None = None) -> dict:
    """Return matching sections split by kind, or an honest no_match.

    Returning nothing is a correct answer. A fabricated section is not.
    """
    hits = index().search(question, terms, " ".join(cards or []),
                          kinds=kinds, docs=docs)
    # The general rule, served alongside whatever ranked. Thirteen of the
    # twenty-three benchmark losses to web search were questions the rulebook
    # answers with a general rule (attack order, effects end on the Bench,
    # devolving clears Special Conditions) while six short Compendium rulings
    # about the same card outscored it and the model, told not to use memory,
    # answered "not found". Principles have their own, lower floor and do not
    # compete with rulings for the top-N.
    principles: list[tuple[Section, float]] = []
    if kinds is None or "mechanics" in kinds:
        principles = index().search(question, terms, " ".join(cards or []),
                                    kinds=("mechanics", "exceptions"),
                                    min_score=MIN_SCORE_PRINCIPLE, limit=PRINCIPLES_N)
    if not hits and not principles:
        return {"no_match": True, "mechanics": [], "exceptions": [], "principles": []}
    if not hits:
        hits = principles

    def render(section: Section, score: float) -> dict:
        out = {"kind": section.kind, "heading": section.heading,
               "text": section.body, "score": round(score, 2)}
        if section.citation:
            out["citation"] = section.citation
            out["revised"] = section.revised
        if section.kind == "ruling":
            out["ruling_source"] = section.source
            out["ruling_date"] = section.revised
        if section.overrides:
            out["overrides"] = section.overrides
        if section.needs_review:
            out["unreviewed"] = True
        return out

    # `best` is the highest-scoring hit whatever its kind. The per-kind lists are
    # for a caller that wants them, but taking exceptions first unconditionally
    # lifts a weak, unrelated exception above a strong document — an exception
    # overrides a mechanic about THE SAME THING, not everything else on the page.
    return {
        "no_match": False,
        "principles": [render(s, sc) for s, sc in principles],
        "best": render(*hits[0]),
        "exceptions": [render(s, sc) for s, sc in hits if s.kind == "exceptions"],
        "rulings": [render(s, sc) for s, sc in hits if s.kind == "ruling"],
        "mechanics": [render(s, sc) for s, sc in hits if s.kind == "mechanics"],
        "documents": [render(s, sc) for s, sc in hits if s.kind == "document"],
    }
