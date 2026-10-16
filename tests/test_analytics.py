"""Analytics must be silent without a key, anonymous with one, and never send secrets."""

import pytest
from streamlit.testing.v1 import AppTest

import analytics


class FakePostHog:
    def __init__(self):
        self.events = []

    def capture(self, event, **kwargs):
        self.events.append((event, kwargs))


@pytest.fixture
def fake(monkeypatch):
    client = FakePostHog()
    monkeypatch.setattr(analytics, "get_client", lambda: client)
    return client


def test_no_key_means_no_tracking(monkeypatch):
    monkeypatch.delenv("POSTHOG_KEY", raising=False)
    assert analytics.get_client() is None
    at = AppTest.from_file("../app.py").run(timeout=30)
    assert not at.exception
    assert "anonymous usage" not in " ".join(str(m.value) for m in at.markdown)


def test_session_start_is_anonymous_and_tagged_with_ref(fake):
    at = AppTest.from_file("../app.py")
    at.query_params["ref"] = "CodeCompass!"
    at.run(timeout=30)
    assert not at.exception
    event, kwargs = fake.events[0]
    assert event == "session_started"
    props = kwargs["properties"]
    assert props["ref"] == "codecompass"
    assert props["$process_person_profile"] is False
    assert len(kwargs["distinct_id"]) == 36  # random UUID, not a person
    assert "anonymous usage" in " ".join(str(m.value) for m in at.markdown)


def test_switching_mode_and_entering_access_code_never_sends_the_code(fake, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-owner-key-for-tests")
    monkeypatch.setenv("APP_PASSWORD", "recruiter-code")
    at = AppTest.from_file("../app.py")
    at.session_state["mode"] = "Try it yourself"
    at.run(timeout=30)
    at.text_input(key="access_code").input("recruiter-code").run(timeout=30)
    assert not at.exception
    names = [e for e, _ in fake.events]
    assert "access_code_entered" in names
    sent = repr(fake.events)
    assert "recruiter-code" not in sent and "fake-owner-key-for-tests" not in sent
    code_event = next(k for e, k in fake.events if e == "access_code_entered")
    assert code_event["properties"]["valid"] is True


def test_labels_are_cleaned_and_refs_sanitised():
    assert analytics.clean_label(":material/shield: Non-functional") == "Non-functional"
    assert analytics.clean_ref(None) == "direct"
    assert analytics.clean_ref("Code Compass/<script>") == "codecompassscript"
