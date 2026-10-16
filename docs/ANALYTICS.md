# Usage analytics

The app can record **anonymous** usage in [PostHog](https://posthog.com) (EU region) so you can see
how visitors, for example recruiters, use the demo. It is off unless `POSTHOG_KEY` is set.

## Privacy by design
- Each visit gets a random ID. No names, no logins, no tracking cookies, no person profiles.
- Transcript text, API keys and access codes are never sent.
- A notice in the footer tells visitors that anonymous usage is recorded.
- Action events are sent from the server with GeoIP disabled. Time-on-page heartbeats are sent from
  the browser, so **turn on "Discard client IP data"** in your PostHog project settings so visitors'
  IP addresses aren't stored.

## Setup
1. In PostHog, open **Settings → Project** and copy the **Project API key** (starts with `phc_`).
2. Add it to `.streamlit/secrets.toml` (local) or Streamlit Cloud → **Settings → Secrets** (online):
   ```toml
   POSTHOG_KEY = "phc_..."
   POSTHOG_HOST = "https://eu.i.posthog.com"
   ```
3. In the same PostHog settings, turn on **Discard client IP data**.

Testing locally without sending anything: set `POSTHOG_KEY = "debug"` and events are printed to the
terminal instead.

## One link per application
Add `?ref=` to the app link you share, for example:

```
https://YOUR-APP.streamlit.app/?ref=codecompass
https://YOUR-APP.streamlit.app/?ref=linkedin-profile
https://YOUR-APP.streamlit.app/?ref=cv
```

Every event carries that `ref`, so you can see which application's link was opened. Visits without a
`ref` show as `direct`.

## What is recorded

| Event | When | Useful properties |
|---|---|---|
| `session_started` | The app is opened | `ref` |
| `example_selected` | An example interview is picked | `example` |
| `interview_opened` | "Read the interview" is expanded | `example` |
| `tab_viewed` | A results tab is opened | `tab` |
| `story_details_opened` | A story's details are expanded | `story`, `backlog` |
| `epic_filtered`, `order_changed` | Story filters are used | `epic`, `order` |
| `priority_changed` | A priority is edited | `backlog` |
| `checklist_ticked` | A review checklist item is ticked | `item`, `checked` |
| `download` | A file is downloaded | `format` |
| `mode_changed` | "See an example" ↔ "Try it yourself" | `mode` |
| `access_code_entered` | An access code is entered (never the code itself) | `valid` |
| `backlog_generated` / `generation_failed` | A live backlog is created / fails | `stories`, `cost_usd`, `seconds`, `error` |
| `heartbeat` | Every 30 s while the page is **visible** (max. 30 min) | `tab`, `example`, `mode` |

Every event also has `seconds_in_session`.

## Reading the data in PostHog
- **Live view:** *Activity* shows events as they arrive. Filter by `ref` to follow one application link.
- **Visits per link:** *Product analytics → New insight → Trends*, event `session_started`,
  breakdown by `ref`.
- **What visitors do:** *Funnel* with `session_started` → `tab_viewed` → `mode_changed` →
  `backlog_generated`.
- **Where time is spent:** *Trends*, event `heartbeat`, breakdown by `tab` (or `example`). Each
  heartbeat is 30 seconds of visible time.
- **Visit length per link:** *SQL* insight:
  ```sql
  SELECT properties.ref AS link, distinct_id AS visit,
         max(toInt(properties.seconds_in_session)) AS seconds
  FROM events
  WHERE timestamp > now() - INTERVAL 30 DAY
  GROUP BY link, visit
  ORDER BY seconds DESC
  ```

## Limits
- Scrolling and reading within a tab isn't tracked, only which tab is open and for how long.
- Ad blockers may block the browser heartbeats; action events (sent from the server) still arrive.
- A refreshed page counts as a new visit.
