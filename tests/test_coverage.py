from pathlib import Path

from coverage import CoverageReport, apply_guards, build_judge_message, index_backlog, load_expected
from test_quality_and_export import backlog_with, make_story

EXPECTED_DIR = Path(__file__).parent.parent / "samples" / "expected"


def test_every_sample_has_a_valid_answer_key():
    transcripts = sorted((EXPECTED_DIR.parent).glob("*.txt"))
    for t in transcripts:
        items = load_expected(EXPECTED_DIR / f"{t.stem}.md")
        assert len(items) >= 8, t.stem
        assert any(i.kind == "requirement" for i in items)


def test_index_gives_citable_ids_to_all_backlog_parts():
    backlog = backlog_with(make_story(), nfrs=[{"id": "NFR-1", "category": "Privacy", "requirement": "Swiss hosting",
                                                "source_quotes": []}])
    backlog["open_questions"] = [{"question": "Paper?", "why_it_matters": "Scope", "ask_whom": "Head", "related_ids": []}]
    backlog["assumptions"] = ["Architects have PDFs"]
    index = index_backlog(backlog)
    assert {"SUMMARY", "E1", "US-1", "NFR-1", "OQ-1", "A-1"} <= set(index)
    assert "[US-1]" in build_judge_message(backlog, load_expected(EXPECTED_DIR / "01_building_permit_portal.md"))


def test_guards_reject_invented_evidence_and_fill_missing_verdicts():
    backlog = backlog_with(make_story())
    expected = load_expected(EXPECTED_DIR / "01_building_permit_portal.md")[:3]
    raw = [
        {"id": "R1", "verdict": "covered", "evidence": ["US-1"], "explanation": "ok"},
        {"id": "R2", "verdict": "covered", "evidence": ["US-99"], "explanation": "cites a story that doesn't exist"},
    ]  # R3 has no verdict at all
    verdicts = {v.item.id: v for v in apply_guards(raw, backlog, expected)}
    assert verdicts["R1"].verdict == "covered"
    assert verdicts["R2"].verdict == "missing"
    assert verdicts["R3"].verdict == "missing"
    report = CoverageReport(list(verdicts.values()))
    assert report.counts == {"covered": 1, "partial": 0, "missing": 2}
    assert round(report.found_rate, 2) == 0.33
