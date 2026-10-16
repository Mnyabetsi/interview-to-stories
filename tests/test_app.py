"""Smoke-tests the Streamlit UI headlessly, without calling the Claude API."""

from streamlit.testing.v1 import AppTest

from test_quality_and_export import TRANSCRIPT, backlog_with, make_story


def test_example_mode_renders_a_saved_result_without_api_key():
    at = AppTest.from_file("../app.py").run(timeout=30)
    assert not at.exception
    labels = {m.label for m in at.metric}
    assert "Stories" in labels  # a saved example is shown by default
    assert not [t for t in at.text_input if "key" in t.label.lower()]  # no key field in example mode


def test_live_mode_renders_results_from_session_state():
    backlog = backlog_with(make_story(), make_story(id="US-2", title="Track status", priority="Should"))
    backlog["open_questions"] = [{"question": "Are paper submissions still accepted?", "why_it_matters": "Affects scope",
                                  "ask_whom": "Monika Keller", "related_ids": ["US-1"]}]
    at = AppTest.from_file("../app.py")
    at.session_state["mode"] = "Try it yourself"
    at.session_state["run"] = {"id": "t", "backlog": backlog, "transcript": TRANSCRIPT,
                               "meta": {"model": "claude-opus-5-5", "seconds": 42, "cost": 0.08, "tokens": 9000}}
    at.run(timeout=30)
    assert not at.exception
    labels = {m.label: m.value for m in at.metric}
    assert labels["Stories"] == "2"
    assert labels["Quotes OK"] == "100%"
    assert any("API key" in t.label for t in at.text_input)


def test_hosted_key_is_never_shown_and_requires_access_code(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-owner-key-for-tests")
    monkeypatch.setenv("APP_PASSWORD", "recruiter-code")
    at = AppTest.from_file("../app.py")
    at.session_state["mode"] = "Try it yourself"
    at.run(timeout=30)
    assert not at.exception
    labels = [t.label for t in at.text_input]
    assert labels == ["Access code", "Or use your own Anthropic API key"]
    assert all(t.value in ("", None) for t in at.text_input)
    rendered = " ".join(str(e.value) for e in at.markdown) + " ".join(str(e.value) for e in at.caption)
    assert "fake-owner-key-for-tests" not in rendered
