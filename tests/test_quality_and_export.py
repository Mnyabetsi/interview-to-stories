import csv
import io
from pathlib import Path

from export import to_jira_csv, to_markdown
from quality import check_backlog, check_quote, find_vague_terms, normalize

TRANSCRIPT = (Path(__file__).parent.parent / "samples" / "01_building_permit_portal.txt").read_text(encoding="utf-8")


def make_story(**overrides):
    story = {
        "id": "US-1", "epic_id": "E1", "title": "Block incomplete submissions",
        "persona": "architect", "i_want": "to be told which required documents are missing before I submit",
        "so_that": "my application is not delayed by a completeness letter",
        "acceptance_criteria": [
            {"given": "a neighbour consent is required", "when": "I submit without it", "then": "submission is blocked and the missing document is named"},
            {"given": "all required documents are attached", "when": "I submit", "then": "I receive a confirmation with a reference number"},
        ],
        "priority": "Must", "priority_rationale": "Biggest time saver for the permit clerk.",
        "source_quotes": ["If the form simply doesn't let them submit without the neighbour consent, I save hours every week."],
        "notes": "",
    }
    story.update(overrides)
    return story


def backlog_with(*stories, nfrs=()):
    return {"summary": "", "personas": [], "epics": [{"id": "E1", "title": "Online submission", "goal": "g"}],
            "stories": list(stories), "non_functional_requirements": list(nfrs),
            "open_questions": [], "assumptions": [], "out_of_scope": []}


def test_exact_quote_is_grounded_despite_curly_apostrophes_and_whitespace():
    nt = normalize(TRANSCRIPT)
    assert check_quote("If the form simply doesn’t let them   submit", nt).status == "grounded"


def test_slightly_altered_quote_is_partial_and_invented_quote_is_missing():
    nt = normalize(TRANSCRIPT)
    assert check_quote("Six out of ten applications are missing something, like a signature.", nt).status == "partial"
    assert check_quote("We want the portal to use blockchain for every permit.", nt).status == "missing"


def test_clean_story_scores_high():
    report = check_backlog(backlog_with(make_story()), TRANSCRIPT)
    assert report.stories["US-1"].score >= 90
    assert report.grounding_rate == 1.0
    assert report.ac_coverage == 1.0


def test_vague_untested_story_is_penalised():
    bad = make_story(
        i_want="a fast and user-friendly upload button",
        so_that="faster",
        acceptance_criteria=[{"given": "a plan", "when": "I upload it", "then": "it is quick"}],
        source_quotes=["Uploads must finish in two seconds."],
    )
    report = check_backlog(backlog_with(bad), TRANSCRIPT).stories["US-1"]
    criteria = {i.criterion for i in report.issues}
    assert {"N", "V", "E", "T", "Traceability"} <= criteria
    assert report.score < 50


def test_vague_terms_match_whole_words_only():
    assert find_vague_terms("It should be fast and easy") == ["easy", "fast"]
    assert find_vague_terms("breakfast is someone's task") == []


def test_story_without_acceptance_criteria_is_an_error():
    report = check_backlog(backlog_with(make_story(acceptance_criteria=[])), TRANSCRIPT).stories["US-1"]
    assert any(i.severity == "error" and i.criterion == "T" for i in report.issues)


def test_nfr_quotes_are_checked():
    nfr = {"id": "NFR-1", "category": "Privacy", "requirement": "Data stored in Switzerland",
           "source_quotes": ["Data has to stay in Switzerland"]}
    report = check_backlog(backlog_with(make_story(), nfrs=[nfr]), TRANSCRIPT)
    assert report.nfr_quotes["NFR-1"][0].status == "grounded"


def test_exports_contain_story_and_parse_as_csv():
    backlog = backlog_with(make_story())
    md = to_markdown(backlog)
    assert "#### US-1: Block incomplete submissions" in md
    assert "Given a neighbour consent is required" in md
    rows = list(csv.DictReader(io.StringIO(to_jira_csv(backlog))))
    assert rows[0]["Summary"] == "US-1 Block incomplete submissions"
    assert rows[0]["Priority"] == "Highest"
    assert rows[0]["Labels"] == "Online-submission"


def test_story_sentence_uses_statement_or_correct_article():
    from export import story_sentence
    assert story_sentence(make_story()).startswith("As an architect, I want")
    assert story_sentence(make_story(statement="Als Architekt möchte ich …")) == "Als Architekt möchte ich …"
