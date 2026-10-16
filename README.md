# 🧭 Interview → User Stories

**Turn a stakeholder interview into a traceable backlog draft in about a minute.**

Paste an interview transcript and get:
- **Personas and epics**
- **User stories** with Gherkin acceptance criteria and a suggested MoSCoW priority, plus the reason for it
- **Non-functional requirements** (security, privacy, accessibility, …)
- **Open questions** grouped by the stakeholder to ask, plus **assumptions** and **out-of-scope** items
- Exports to **Markdown**, **Jira CSV** and **JSON**

The AI writes the draft. A Product Owner reviews it and makes the decisions.

> 🔗 **Live demo:** https://interview-to-stories.streamlit.app
> 📄 **Product brief:** [docs/PRODUCT_BRIEF.md](docs/PRODUCT_BRIEF.md)

<!-- Add a screenshot or GIF here: docs/screenshot.png -->

---

## Why this exists

I built this as a Product Owner portfolio project. After every stakeholder interview, a PO spends
hours writing stories, acceptance criteria and follow-up questions, and details get lost along the way.
This tool produces the first draft. It also checks that draft against two things POs care about:

1. **Traceability.** Every story and NFR cites *verbatim* quotes from the transcript. A
   deterministic check (no AI) confirms each quote really appears in the interview:
   ✅ exact · 🟡 paraphrased · ❌ not found. This catches invented requirements.
2. **INVEST quality.** Rule-based checks flag stories that are vague ("fast", "user-friendly"),
   describe a solution instead of a need, have no clear benefit, lack acceptance criteria or are
   too large. Each story gets a 0–100 score, so you can review the weakest ones first.

The design reflects public-sector work: data protection (Swiss nDSG), accessibility and multilingual
teams. Output is available in **English, German or French**, and source quotes stay in the
original language.

## How it works

```
transcript ──► Claude (structured JSON output) ──► backlog draft
                                                     │
                     rule-based quality checks ◄─────┘
                     (INVEST heuristics + quote grounding)
                                                     │
                     PO review in the UI ────────────┴──► Markdown / Jira CSV / JSON
```

- `generator.py`: one Claude API call with a JSON schema (structured outputs), so the response
  always has the expected shape
- `quality.py`: deterministic INVEST and traceability checks
- `export.py`: Markdown, Jira-importable CSV and JSON
- `analytics.py`: optional anonymous usage tracking (PostHog)
- `app.py`: Streamlit UI with an editable priority table and a PO review checklist
- `eval.py`: runs all sample transcripts and reports quality metrics
- `coverage.py`: checks the backlog against a human-written answer key of expected requirements

## Run it locally

Requires Python 3.10+ and an [Anthropic API key](https://console.anthropic.com/).

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
export ANTHROPIC_API_KEY=sk-ant-...
streamlit run app.py
```

You can also skip the environment variable and paste your key under **Try it yourself → Settings**.

## Evaluate

```bash
python eval.py              # generate backlogs for all samples, then evaluate
python eval.py --use-saved  # re-evaluate saved backlogs only (cheaper)
```

This runs every transcript in `samples/`, saves the backlogs to `samples/outputs/` (the app's
**See an example** mode shows them without an API call) and writes
[`eval_results.md`](eval_results.md). It checks three things:

1. **Traceability (no AI):** is every cited quote really in the transcript?
2. **Story quality (no AI):** INVEST rule checks, scored 0–100 per story.
3. **Coverage, or "did it miss anything?":** each sample has an answer key in `samples/expected/`
   listing what a careful PO should capture (requirements, NFRs, open questions, scope, goals),
   written from the transcript before any backlog was generated. Claude acts as a strict reviewer
   and must cite backlog item IDs as evidence. Code rejects verdicts that cite IDs that don't exist,
   and every verdict is saved in `samples/outputs/*.coverage.json` for human review.

### Results (3 synthetic Swiss public-sector interviews, Claude Opus 5.5, medium effort)

| Metric | Target | Result |
|---|---|---|
| Expected requirements found | ≥ 90% | **98%** (47 of 48; the 48th partly found) |
| Quotes found verbatim in transcript | ≥ 95% | **100%** (149 of 149) |
| Average story quality score | ≥ 80 | **97** (51 stories; lowest 87) |
| Stories with ≥ 2 acceptance criteria | ≥ 90% | **98%** |
| Cost per transcript | < $0.25 | **$0.30** ❌ (try Sonnet 5.5 to lower it) |
| Time per transcript | n/a | ~2 minutes |

**Limitations:** three short, synthetic interviews are a small test set, and the answer keys were
written by the same author as the transcripts. The coverage reviewer is itself an AI, so its
verdicts are spot-checked by hand. Real interviews are messier, so treat these numbers as a baseline.

Unit tests (no API key needed): `pytest`

## Deploy for free (Streamlit Community Cloud)

1. Push this folder to a public GitHub repo.
2. Go to [share.streamlit.io](https://share.streamlit.io), choose **New app** and pick the repo
   with `app.py` as the entry point.
3. Optional: under **Settings → Secrets**, add the values from `.streamlit/secrets.toml.example`.
   - With no key, visitors use their own API key.
   - With `ANTHROPIC_API_KEY` and `APP_PASSWORD`, people who have the access code (e.g. a recruiter) can
     use your key. Set a monthly spend limit in the Anthropic Console.
4. Commit the files in `samples/outputs/` so visitors can browse example results for free.

## Usage analytics (optional)

Set `POSTHOG_KEY` to record anonymous usage in PostHog: which examples and tabs visitors open, what
they download, and how long they spend on each tab. Share links like `…/?ref=codecompass` to see which
application's link was opened. No names, no tracking cookies, no transcript text. Details and
ready-made PostHog queries: [docs/ANALYTICS.md](docs/ANALYTICS.md).

## Cost

One transcript (~1,000–1,500 words) costs about **$0.25–0.35** with Claude Opus 5.5 at medium effort
(measured average: $0.30), and less with Sonnet or Haiku. The coverage check in `eval.py` adds about
$0.06 per transcript. The app shows the estimated cost of every run.

## Privacy

Use synthetic or anonymised transcripts. The app stores nothing. Transcript text is sent to the
Claude API only to generate the draft. The sample interviews in `samples/` are fictional.

## Roadmap

- [ ] Push stories directly to Jira / Azure DevOps via API
- [ ] Merge several interviews and highlight conflicting needs
- [ ] Audio upload with automatic transcription
- [ ] Team-specific Definition of Ready checks
- [ ] Inline editing of story text before export
