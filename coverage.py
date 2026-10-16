"""Coverage check: did the generated backlog capture the requirements a human PO expected?

Each sample transcript can have an answer key in samples/expected/<name>.md, written by a person
from the transcript alone. Claude acts as a strict reviewer: for every expected item it decides
whether the backlog covers it, and must cite the backlog item IDs as evidence. Plain code then
verifies that the cited IDs exist; a verdict without valid evidence counts as missed. Every
verdict is saved, so a person can audit the grading.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from generator import DEFAULT_MODEL, GenerationResult, request_json

KINDS = ["requirement", "nfr", "open_question", "scope", "goal"]
VERDICTS = ["covered", "partial", "missing"]
_ITEM_RE = re.compile(r"^- \[(?P<id>[A-Za-z]+\d+)\] \((?P<kind>[a-z_]+)\) (?P<text>.+)$")


@dataclass
class ExpectedItem:
    id: str
    kind: str
    text: str


@dataclass
class ItemVerdict:
    item: ExpectedItem
    verdict: str
    evidence: list[str]
    explanation: str


@dataclass
class CoverageReport:
    verdicts: list[ItemVerdict]
    judge: GenerationResult | None = None
    counts: dict[str, int] = field(default_factory=dict)

    def __post_init__(self):
        self.counts = {v: sum(x.verdict == v for x in self.verdicts) for v in VERDICTS}

    @property
    def found_rate(self) -> float:
        return self.counts["covered"] / len(self.verdicts) if self.verdicts else 0.0

    @property
    def found_or_partial_rate(self) -> float:
        return (self.counts["covered"] + self.counts["partial"]) / len(self.verdicts) if self.verdicts else 0.0


def load_expected(path: Path) -> list[ExpectedItem]:
    items = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = _ITEM_RE.match(line.strip())
        if m:
            if m["kind"] not in KINDS:
                raise ValueError(f"{path.name}: unknown kind '{m['kind']}' in line: {line}")
            items.append(ExpectedItem(m["id"], m["kind"], m["text"].strip()))
    if len({i.id for i in items}) != len(items):
        raise ValueError(f"{path.name}: duplicate IDs")
    return items


def index_backlog(backlog: dict) -> dict[str, str]:
    """Gives every part of the backlog a citable ID and a one-paragraph text."""
    index = {"SUMMARY": backlog.get("summary", "")}
    for e in backlog.get("epics", []):
        index[e["id"]] = f"Epic: {e['title']}. Goal: {e['goal']}"
    for s in backlog.get("stories", []):
        criteria = " | ".join(f"Given {a['given']} When {a['when']} Then {a['then']}"
                              for a in s.get("acceptance_criteria", []))
        statement = s.get("statement") or f"As a {s['persona']}, I want {s['i_want']}, so that {s['so_that']}."
        index[s["id"]] = f"Story: {s['title']}. {statement} Acceptance criteria: {criteria}. Notes: {s.get('notes', '')}"
    for n in backlog.get("non_functional_requirements", []):
        index[n["id"]] = f"NFR ({n['category']}): {n['requirement']}"
    for i, q in enumerate(backlog.get("open_questions", []), 1):
        index[f"OQ-{i}"] = f"Open question: {q['question']} Why: {q['why_it_matters']} Ask: {q['ask_whom']}"
    for i, a in enumerate(backlog.get("assumptions", []), 1):
        index[f"A-{i}"] = f"Assumption: {a}"
    for i, x in enumerate(backlog.get("out_of_scope", []), 1):
        index[f"X-{i}"] = f"Out of scope: {x}"
    return index


JUDGE_SYSTEM = """You are a strict senior Product Owner reviewing a backlog draft against an answer key \
of items a careful PO would expect after a stakeholder interview.

For each expected item decide:
- "covered": the backlog clearly captures the essential point of the item. Wording may differ, the \
backlog may be in a different language, and the point may be spread over several backlog items.
- "partial": the backlog captures part of the item but misses an essential element (for example \
the rule but not the condition, or the feature but not the constraint).
- "missing": the backlog does not capture the item.

Rules: judge only what is written in the backlog, do not give credit for what it "probably means". \
Cite the IDs of the backlog items that provide the evidence (empty list for "missing"). Explain \
each verdict in one short sentence, naming what is missing for "partial". Return one verdict for \
every expected item."""

JUDGE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["verdicts"],
    "properties": {
        "verdicts": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "verdict", "evidence", "explanation"],
                "properties": {
                    "id": {"type": "string"},
                    "verdict": {"type": "string", "enum": VERDICTS},
                    "evidence": {"type": "array", "items": {"type": "string"}},
                    "explanation": {"type": "string"},
                },
            },
        }
    },
}


def build_judge_message(backlog: dict, expected: list[ExpectedItem]) -> str:
    backlog_text = "\n".join(f"[{k}] {v}" for k, v in index_backlog(backlog).items())
    expected_text = "\n".join(f"[{i.id}] ({i.kind}) {i.text}" for i in expected)
    return f"<backlog>\n{backlog_text}\n</backlog>\n\n<expected_items>\n{expected_text}\n</expected_items>"


def apply_guards(raw_verdicts: list[dict], backlog: dict, expected: list[ExpectedItem]) -> list[ItemVerdict]:
    """Deterministic checks on the reviewer's output: cited IDs must exist, every item gets a verdict."""
    valid_ids = set(index_backlog(backlog))
    by_id = {v["id"]: v for v in raw_verdicts}
    results = []
    for item in expected:
        v = by_id.get(item.id)
        if v is None:
            results.append(ItemVerdict(item, "missing", [], "No verdict returned by the reviewer."))
            continue
        evidence = [e for e in v["evidence"] if e in valid_ids]
        verdict, explanation = v["verdict"], v["explanation"]
        if verdict != "missing" and not evidence:
            verdict, explanation = "missing", f"Counted as missing: no valid evidence cited. ({explanation})"
        results.append(ItemVerdict(item, verdict, evidence, explanation))
    return results


def check_coverage(
    backlog: dict,
    expected: list[ExpectedItem],
    *,
    model: str = DEFAULT_MODEL,
    effort: str = "medium",
    api_key: str | None = None,
) -> CoverageReport:
    judge = request_json(JUDGE_SYSTEM, build_judge_message(backlog, expected), JUDGE_SCHEMA,
                         model=model, effort=effort, api_key=api_key)
    return CoverageReport(apply_guards(judge.data["verdicts"], backlog, expected), judge)
