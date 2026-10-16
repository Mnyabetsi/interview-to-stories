"""Optional, anonymous usage analytics sent to PostHog.

Turned on only when the POSTHOG_KEY secret is set ("debug" prints events instead of sending them);
otherwise every function here does nothing. Each browser session gets a random ID: no cookies, no
names, no person profiles. Action events are sent from the server with GeoIP disabled; time-on-page
heartbeats come from the browser (see heartbeat()). Transcript text, API keys and access codes are
never sent.

Every event carries:
- ref: the ?ref=... value of the link the visitor opened (e.g. one link per job application)
- seconds_in_session: time since the visitor opened the app
"""

from __future__ import annotations

import json
import re
import time
import uuid

import streamlit as st
from posthog import Posthog

from settings import secret

DEFAULT_HOST = "https://eu.i.posthog.com"
HEARTBEAT_SECONDS = 30
MAX_SESSION_SECONDS = 30 * 60  # stop heartbeats after 30 minutes of an open tab


@st.cache_resource(show_spinner=False)
def _posthog(key: str, host: str) -> Posthog:
    return Posthog(key, host=host, disable_geoip=True)


class _PrintClient:
    """Used when POSTHOG_KEY is "debug": prints events to the terminal instead of sending them."""

    def capture(self, event: str, **kwargs) -> None:
        props = {k: v for k, v in kwargs.get("properties", {}).items() if not k.startswith("$")}
        print(f"[analytics] {event} {props}", flush=True)


def get_client() -> Posthog | _PrintClient | None:
    key = secret("POSTHOG_KEY")
    if key == "debug":
        return _PrintClient()
    return _posthog(key, secret("POSTHOG_HOST") or DEFAULT_HOST) if key else None


def enabled() -> bool:
    return get_client() is not None


def clean_ref(value: str | None) -> str:
    return re.sub(r"[^a-z0-9_-]", "", (value or "").lower())[:40] or "direct"


def start_session() -> None:
    """Call on every run; records 'session_started' once per browser session."""
    if "analytics_id" in st.session_state:
        return
    st.session_state.analytics_id = str(uuid.uuid4())
    st.session_state.analytics_start = time.time()
    st.session_state.analytics_ref = clean_ref(st.query_params.get("ref"))
    track("session_started")


def track(event: str, **properties) -> None:
    client = get_client()
    if client is None or "analytics_id" not in st.session_state:
        return
    client.capture(
        event,
        distinct_id=st.session_state.analytics_id,
        properties={
            "ref": st.session_state.analytics_ref,
            "seconds_in_session": round(time.time() - st.session_state.analytics_start),
            "$process_person_profile": False,
            **properties,
        },
    )


def track_widget(event: str, key: str, prop: str, only_if_true: bool = False, **extra) -> None:
    """Callback helper: sends the widget's new value from session state."""
    value = st.session_state.get(key)
    if only_if_true and not value:
        return
    track(event, **{prop: clean_label(value) if isinstance(value, str) else value}, **extra)


def clean_label(label: str) -> str:
    """Removes ':material/icon:' prefixes so tab names read cleanly in reports."""
    return re.sub(r":material/\w+:\s*", "", label).strip()


def heartbeat(**context_keys: str) -> None:
    """Sends a 'heartbeat' event every 30 s while the page is visible, with the current value of each
    given session-state key (e.g. tab="results_tab"). Counting heartbeats shows where time is spent.

    The timer runs in the visitor's browser (a zero-height component), not as a Streamlit rerun, so it
    never interferes with the app's widgets. It pauses while the browser tab is hidden. Because these
    requests come from the browser, PostHog receives the visitor's IP address: turn on "Discard client
    IP data" in the PostHog project settings so it isn't stored.
    """
    key = secret("POSTHOG_KEY")
    if not key or "analytics_id" not in st.session_state:
        return
    context = {}
    for prop, state_key in context_keys.items():
        value = st.session_state.get(state_key)
        context[prop] = clean_label(value) if isinstance(value, str) else value
    payload = {
        "api_key": key,
        "event": "heartbeat",
        "distinct_id": st.session_state.analytics_id,
        "properties": {"ref": st.session_state.analytics_ref, "$process_person_profile": False,
                       "$geoip_disable": True, **context},
    }
    config = {
        "payload": payload,
        "url": (secret("POSTHOG_HOST") or DEFAULT_HOST).rstrip("/") + "/i/v0/e/",
        "debug": key == "debug",
        "secondsAtRender": round(time.time() - st.session_state.analytics_start),
        "intervalMs": HEARTBEAT_SECONDS * 1000,
        "maxSeconds": MAX_SESSION_SECONDS,
    }
    st.iframe(f"""<script>
const c = {json.dumps(config)};
const loadedAt = Date.now();
setInterval(() => {{
  if (document.visibilityState !== "visible") return;
  const seconds = c.secondsAtRender + Math.round((Date.now() - loadedAt) / 1000);
  if (seconds > c.maxSeconds) return;
  const body = {{...c.payload, properties: {{...c.payload.properties, seconds_in_session: seconds}}}};
  if (c.debug) {{ console.log("[analytics] heartbeat", JSON.stringify(body.properties)); return; }}
  fetch(c.url, {{method: "POST", headers: {{"Content-Type": "application/json"}},
                 body: JSON.stringify(body), keepalive: true}}).catch(() => {{}});
}}, c.intervalMs);
</script>""", height=1)
