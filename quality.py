"""Rule-based quality checks for a generated backlog: INVEST heuristics and quote grounding.

These checks are deterministic (no AI) so the Product Owner can trust them as a second opinion
on the model's output.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher

VAGUE_TERMS = [
    # English
    "fast", "quick", "quickly", "easy", "easily", "simple", "simply", "user-friendly",
    "intuitive", "efficient", "flexible", "appropriate", "adequate", "seamless", "robust",
    "modern", "as soon as possible", "etc", "and/or", "several", "some", "many", "normally",
    # German
    "schnell", "einfach", "benutzerfreundlich", "intuitiv", "effizient", "flexibel",
    "angemessen", "möglichst", "usw", "einige", "mehrere", "normalerweise",
    # French
    "rapide", "rapidement", "facile", "facilement", "intuitif", "convivial", "efficace",
    "plusieurs", "certains", "normalement",
]
_VAGUE_RE = re.compile(
    r"(?<![\w-])(" + "|".join(re.escape(t) for t in sorted(VAGUE_TERMS, key=len, reverse=True)) + r")(?![\w-])",
    re.IGNORECASE,
)
SOLUTION_TERMS = re.compile(
    r"\b(button|dropdown|drop-down|checkbox|click|popup|pop-up|modal|database|"
    r"Schaltfläche|Knopf|klicken|bouton|cliquer)\b",
    re.IGNORECASE,
)
STORY_REF = re.compile(r"\bUS-\d+\b")

PARTIAL_MATCH_THRESHOLD = 0.8
PENALTY = {"error": 25, "warning": 10, "info": 3}


@dataclass
class Issue:
    severity: str  # "error" | "warning" | "info"
    criterion: str  # INVEST letter or "Traceability"
    message: str


@dataclass
class QuoteCheck:
    quote: str
    status: str  # "grounded" | "partial" | "missing"
    similarity: float


@dataclass
class StoryReport:
    story_id: str
    score: int
    issues: list[Issue] = field(default_factory=list)
    quotes: list[QuoteCheck] = field(default_factory=list)


@dataclass
class BacklogReport:
    stories: dict[str, StoryReport]
    nfr_quotes: dict[str, list[QuoteCheck]]
    story_count: int
    average_score: float
    grounding_rate: float
    quote_counts: dict[str, int]
    ac_coverage: float  # share of stories with >= 2 acceptance criteria


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.translate(str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "„": '"',
                                         "«": '"', "»": '"', "–": "-", "—": "-", "…": "..."}))
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip(" \"'.,;:!?-")


def check_quote(quote: str, normalized_transcript: str) -> QuoteCheck:
    q = normalize(quote)
    if not q:
        return QuoteCheck(quote, "missing", 0.0)
    if q in normalized_transcript:
        return QuoteCheck(quote, "grounded", 1.0)
    # Anchor on the longest exact overlap, then measure how much of the quote the surrounding
    # passage covers (ignoring tiny fragments such as " the ").
    anchor = SequenceMatcher(None, normalized_transcript, q, autojunk=False).find_longest_match(
        0, len(normalized_transcript), 0, len(q))
    start = max(0, anchor.a - anchor.b - 20)
    window = normalized_transcript[start:start + len(q) + 40]
    blocks = SequenceMatcher(None, window, q, autojunk=False).get_matching_blocks()
    similarity = sum(b.size for b in blocks if b.size >= 4) / len(q)
    status = "partial" if similarity >= PARTIAL_MATCH_THRESHOLD else "missing"
    return QuoteCheck(quote, status, round(similarity, 2))


def find_vague_terms(text: str) -> list[str]:
    return sorted({m.group(1).lower() for m in _VAGUE_RE.finditer(text)})


def _word_overlap(a: str, b: str) -> float:
    wa, wb = set(re.findall(r"\w{4,}", a.lower())), set(re.findall(r"\w{4,}", b.lower()))
    return len(wa & wb) / len(wb) if wb else 0.0


def check_story(story: dict, normalized_transcript: str) -> StoryReport:
    issues: list[Issue] = []
    i_want, so_that = story.get("i_want", ""), story.get("so_that", "")
    criteria = story.get("acceptance_criteria", [])

    # I - Independent
    refs = sorted(set(STORY_REF.findall(f"{i_want} {so_that} {story.get('notes', '')}")) - {story.get("id")})
    if refs:
        issues.append(Issue("info", "I", f"References {', '.join(refs)}; check whether it can be delivered independently."))

    # N - Negotiable
    solution_words = sorted({m.lower() for m in SOLUTION_TERMS.findall(i_want)})
    if solution_words:
        issues.append(Issue("warning", "N", f"Describes a solution rather than a need ({', '.join(solution_words)})."))

    # V - Valuable
    if len(so_that.split()) < 4:
        issues.append(Issue("warning", "V", "The 'so that' benefit is missing or too short to show value."))
    elif _word_overlap(i_want, so_that) > 0.7:
        issues.append(Issue("warning", "V", "The benefit mostly repeats the capability; state the outcome instead."))

    # E - Estimable
    vague_want = find_vague_terms(i_want)
    if vague_want:
        issues.append(Issue("warning", "E", f"Vague wording makes this hard to estimate: {', '.join(vague_want)}."))

    # S - Small
    if len(criteria) > 6:
        issues.append(Issue("warning", "S", f"{len(criteria)} acceptance criteria; consider splitting the story."))
    if re.search(r"\b(and|und|et)\b", i_want, re.IGNORECASE):
        issues.append(Issue("info", "S", "The capability contains 'and'; it may combine two stories."))

    # T - Testable
    if not criteria:
        issues.append(Issue("error", "T", "No acceptance criteria."))
    elif len(criteria) < 2:
        issues.append(Issue("info", "T", "Only one acceptance criterion; consider edge cases and error paths."))
    for n, ac in enumerate(criteria, 1):
        if not all(ac.get(k, "").strip() for k in ("given", "when", "then")):
            issues.append(Issue("error", "T", f"Acceptance criterion {n} is missing a Given, When or Then."))
        vague = find_vague_terms(" ".join(ac.get(k, "") for k in ("given", "when", "then")))
        if vague:
            issues.append(Issue("warning", "T", f"Acceptance criterion {n} uses untestable wording: {', '.join(vague)}."))

    # Traceability
    quotes = [check_quote(q, normalized_transcript) for q in story.get("source_quotes", [])]
    if not quotes:
        issues.append(Issue("error", "Traceability", "No source quote; this story can't be traced to the interview."))
    for qc in quotes:
        if qc.status == "missing":
            issues.append(Issue("error", "Traceability", f"Quote not found in transcript: “{qc.quote}”"))
        elif qc.status == "partial":
            issues.append(Issue("warning", "Traceability", f"Quote only partly matches the transcript ({qc.similarity:.0%}): “{qc.quote}”"))

    score = max(0, 100 - sum(PENALTY[i.severity] for i in issues))
    return StoryReport(story.get("id", "?"), score, issues, quotes)


def check_backlog(backlog: dict, transcript: str) -> BacklogReport:
    normalized_transcript = normalize(transcript)
    stories = {s.get("id", f"#{n}"): check_story(s, normalized_transcript)
               for n, s in enumerate(backlog.get("stories", []), 1)}
    nfr_quotes = {nfr.get("id", f"#{n}"): [check_quote(q, normalized_transcript) for q in nfr.get("source_quotes", [])]
                  for n, nfr in enumerate(backlog.get("non_functional_requirements", []), 1)}

    all_quotes = [q for r in stories.values() for q in r.quotes] + [q for qs in nfr_quotes.values() for q in qs]
    counts = {status: sum(q.status == status for q in all_quotes) for status in ("grounded", "partial", "missing")}
    story_list = backlog.get("stories", [])

    return BacklogReport(
        stories=stories,
        nfr_quotes=nfr_quotes,
        story_count=len(stories),
        average_score=round(sum(r.score for r in stories.values()) / len(stories), 1) if stories else 0.0,
        grounding_rate=counts["grounded"] / len(all_quotes) if all_quotes else 0.0,
        quote_counts=counts,
        ac_coverage=(sum(len(s.get("acceptance_criteria", [])) >= 2 for s in story_list) / len(story_list)
                     if story_list else 0.0),
    )
