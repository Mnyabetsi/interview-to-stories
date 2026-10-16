"""Keeps tests away from real secrets: settings come only from environment variables set by a test."""

import os

import pytest

import analytics
import settings


@pytest.fixture(autouse=True)
def isolate_secrets(monkeypatch):
    def env_only(name: str) -> str:
        return os.environ.get(name, "")

    monkeypatch.setattr(settings, "secret", env_only)
    monkeypatch.setattr(analytics, "secret", env_only)
    for name in ("ANTHROPIC_API_KEY", "APP_PASSWORD", "POSTHOG_KEY", "POSTHOG_HOST"):
        monkeypatch.delenv(name, raising=False)

    def no_real_client(*args, **kwargs):
        pytest.fail("A test tried to create a real PostHog client.")

    monkeypatch.setattr(analytics, "_posthog", no_real_client)
