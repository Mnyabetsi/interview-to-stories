"""Streamlit UI: Interview → User Stories."""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

import analytics
from export import gherkin, story_sentence, to_jira_csv, to_json, to_markdown
from generator import (DEFAULT_MODEL, LANGUAGES, MODELS, PRIORITIES, GenerationError,
                       generate_backlog)
from quality import BacklogReport, check_backlog
from settings import secret

# Shown in the footer. Fill in to put your name on the app.
AUTHOR_NAME = ""
AUTHOR_LINKS = {"LinkedIn": "", "GitHub": ""}

SAMPLES_DIR = Path(__file__).parent / "samples"
OUTPUTS_DIR = SAMPLES_DIR / "outputs"
EXAMPLE, LIVE = "See an example", "Try it yourself"

QUOTE_ICON = {"grounded": ":green[:material/check_circle:]", "partial": ":orange[:material/error:]",
              "missing": ":red[:material/cancel:]"}
QUOTE_HELP = {"grounded": "found word for word", "partial": "only partly matches", "missing": "not found in transcript"}
SEVERITY_ICON = {"error": ":red[:material/error:]", "warning": ":orange[:material/warning:]",
                 "info": ":blue[:material/info:]"}
PRIORITY_COLOR = {"Must": "red", "Should": "orange", "Could": "blue", "Won't": "gray"}

st.set_page_config(page_title="Interview → User Stories", page_icon="🧭", layout="wide",
                   initial_sidebar_state="collapsed")
analytics.start_session()

# Colours inherit from the active theme (light or dark), so these styles work in both.
st.html("""<style>
.hero { padding: 0.5rem 0 0.25rem; margin-bottom: 0.75rem; }
.hero .topline { display: flex; justify-content: space-between; align-items: baseline; gap: 1rem; flex-wrap: wrap; }
.hero .eyebrow { font-weight: 600; font-size: 0.8rem; letter-spacing: 0.08em; text-transform: uppercase; opacity: 0.65; }
.hero .theme-hint { font-size: 0.8rem; opacity: 0.6; }
.hero h1 { font-size: 2.6rem; line-height: 1.15; margin: 0.35rem 0 0.6rem; padding: 0; }
.hero p { font-size: 1.1rem; opacity: 0.8; max-width: 46rem; margin: 0; }
.step-num { display: inline-flex; align-items: center; justify-content: center; width: 1.7rem; height: 1.7rem;
            border-radius: 50%; background: color-mix(in srgb, currentColor 10%, transparent);
            font-weight: 700; font-size: 0.85rem; margin-bottom: 0.4rem; }
.step-title { font-weight: 600; margin-bottom: 0.15rem; }
.step-text { opacity: 0.75; font-size: 0.92rem; }
.footer { opacity: 0.55; font-size: 0.85rem; text-align: center; padding: 2rem 0 1rem; }
</style>""")


def sample_info(path: Path) -> tuple[str, str]:
    """Title and organisation from the first two lines of a sample transcript."""
    lines = path.read_text(encoding="utf-8").splitlines()
    return lines[0].split(":", 1)[-1].strip(), lines[1].strip()


def api_key_input() -> str:
    """Returns the API key to use, without ever displaying the owner's key."""
    hosted_key, access_code = secret("ANTHROPIC_API_KEY"), secret("APP_PASSWORD")
    if hosted_key and not access_code:
        st.caption(":material/check: Ready. An API key is configured for this app.")
        return hosted_key
    if hosted_key:
        code = st.text_input("Access code", type="password", help="Ask the app owner for an access code.",
                             key="access_code", on_change=lambda: analytics.track(
                                 "access_code_entered", valid=st.session_state.access_code == access_code))
        if code and code == access_code:
            st.caption(":material/check: Access code accepted.")
            return hosted_key
        if code:
            st.caption(":red[That access code isn't valid.]")
        return st.text_input("Or use your own Anthropic API key", type="password",
                             help="Used only for this session and never stored.")
    return st.text_input("Your Anthropic API key", type="password",
                         help="Get one at console.anthropic.com. Used only for this session and never stored.")


samples = {p.stem: (p, *sample_info(p)) for p in sorted(SAMPLES_DIR.glob("*.txt"))}

# ---------- Hero ----------
st.markdown("""<div class="hero">
<div class="topline"><div class="eyebrow">Product Owner toolkit · AI-assisted requirements engineering</div><div class="theme-hint">◐ Switch light / dark: ⋮ menu, top right</div></div>
<h1>Interview → User Stories</h1>
<p>Turn a stakeholder interview into a traceable backlog draft: user stories with acceptance criteria,
non-functional requirements and the open questions to ask next.</p>
</div>""", unsafe_allow_html=True)

steps = [
    ("Paste an interview", "A transcript or notes from a stakeholder conversation, in English, German or French."),
    ("Claude drafts the backlog", "Stories, Gherkin criteria, NFRs and open questions, each linked to verbatim quotes."),
    ("You review and decide", "Built-in INVEST and quote checks show what needs attention. Export to Jira or Markdown."),
]
for col, (n, (title, text)) in zip(st.columns(3), enumerate(steps, 1)):
    with col.container(border=True, height="stretch"):
        st.markdown(f'<div class="step-num">{n}</div><div class="step-title">{title}</div>'
                    f'<div class="step-text">{text}</div>', unsafe_allow_html=True)

st.space("medium")
mode = st.segmented_control("Mode", [EXAMPLE, LIVE], default=EXAMPLE, key="mode", label_visibility="collapsed",
                            on_change=analytics.track_widget, args=("mode_changed", "mode", "mode")) or EXAMPLE

# ---------- Input ----------
run = None
if mode == EXAMPLE:
    stem = st.pills("Example interview", list(samples), default=next(iter(samples), None), key="sample",
                    format_func=lambda s: samples[s][1],
                    on_change=analytics.track_widget, args=("example_selected", "sample", "example")) or next(iter(samples), None)
    if stem:
        path, title, org = samples[stem]
        transcript = path.read_text(encoding="utf-8")
        with st.expander(f"Read the interview · {org}", icon=":material/description:", key=f"read_{stem}",
                         on_change=analytics.track_widget, args=("interview_opened", f"read_{stem}", "opened", True),
                         kwargs={"example": stem}):
            with st.container(height=360, border=False):
                st.markdown("\n\n".join(line for line in transcript.splitlines() if line.strip()))
        saved = OUTPUTS_DIR / f"{stem}.json"
        if saved.exists():
            data = json.loads(saved.read_text(encoding="utf-8"))
            run = {"id": stem, "backlog": data["backlog"], "transcript": transcript, "meta": data.get("meta", {})}
        else:
            st.info("No saved result for this interview yet. Run `python eval.py` to create one, or switch to "
                    "**Try it yourself**.")
else:
    left, right = st.columns([3, 2], gap="large")
    with left:
        start = st.selectbox("Start from", ["Blank", *samples], format_func=lambda s: "Blank" if s == "Blank" else
                             f"Sample: {samples[s][1]}")
        upload = st.file_uploader("Upload a transcript (.txt, .md, .vtt)", type=["txt", "md", "vtt"])
        initial = (upload.read().decode("utf-8", errors="replace") if upload
                   else samples[start][0].read_text(encoding="utf-8") if start != "Blank" else "")
        transcript = st.text_area("Interview transcript", initial, height=340, key=f"transcript_{start}_{bool(upload)}",
                                  placeholder="Paste the interview transcript here…")
        st.caption(":material/lock: Use anonymised or synthetic transcripts. Nothing is stored; the text is "
                   "sent to the Claude API only to create the draft.")
    with right:
        with st.container(border=True):
            st.markdown("**Settings**")
            language = st.selectbox("Output language", list(LANGUAGES))
            context = st.text_area("Project context (optional)", height=90,
                                   placeholder="e.g. Web portal for a mid-sized Swiss municipality, launch in Q3.")
            api_key = api_key_input()
            with st.expander("Advanced"):
                model = st.selectbox("Model", list(MODELS), format_func=MODELS.get,
                                     index=list(MODELS).index(DEFAULT_MODEL))
                effort = st.select_slider("Thinking effort", ["low", "medium", "high"], value="medium",
                                          help="Higher effort is slower and costs more.")
            clicked = st.button("Generate backlog", type="primary", icon=":material/auto_awesome:",
                                disabled=not transcript.strip(), width="stretch")
        if clicked:
            if not api_key:
                analytics.track("generate_blocked", reason="no key")
                st.error("Enter an access code or your own API key first.")
            else:
                with st.spinner("Claude is drafting your backlog. This usually takes 1–2 minutes…"):
                    try:
                        result = generate_backlog(transcript, model=model, language=language,
                                                  effort=effort, context=context, api_key=api_key)
                        st.session_state["live_count"] = st.session_state.get("live_count", 0) + 1
                        st.session_state["run"] = {
                            "id": f"live{st.session_state['live_count']}", "backlog": result.data,
                            "transcript": transcript,
                            "meta": {"model": result.model, "seconds": result.seconds, "cost": result.cost_usd,
                                     "tokens": result.input_tokens + result.output_tokens,
                                     "fell_back": result.fell_back},
                        }
                        analytics.track("backlog_generated", model=result.model, language=language,
                                        started_from="upload" if upload else start,
                                        stories=len(result.data.get("stories", [])),
                                        seconds=round(result.seconds), cost_usd=round(result.cost_usd, 3))
                    except GenerationError as e:
                        analytics.track("generation_failed", error=str(e))
                        st.error(str(e))
    run = st.session_state.get("run")

# Time-on-page tracking (no-op without a PostHog key). Placed here so it also runs when there are no results yet.
analytics.heartbeat(mode="mode", example="sample", tab="results_tab")

if not run:
    st.stop()

# ---------- Results ----------
backlog, meta = run["backlog"], run["meta"]
report: BacklogReport = check_backlog(backlog, run["transcript"])
stories = backlog.get("stories", [])
run_id = run.get("id", "run")

st.divider()
st.subheader("Backlog draft")
with st.container(border=True):
    st.markdown(f":gray[**Summary**]  \n{backlog.get('summary', '')}")

m = st.columns(5)
m[0].metric("Stories", report.story_count, border=True)
m[1].metric("Avg. quality", f"{report.average_score:.0f}", border=True,
            help="Rule-based INVEST and traceability score, 0–100")
m[2].metric("Quotes OK", f"{report.grounding_rate:.0%}", border=True,
            help=f"{report.quote_counts['grounded']} exact · {report.quote_counts['partial']} partial · "
                 f"{report.quote_counts['missing']} not found")
m[3].metric("Questions", len(backlog.get("open_questions", [])), border=True)
if meta.get("cost") is not None:
    m[4].metric("Cost", f"${meta['cost']:.2f}", border=True,
                help=f"{meta.get('model')} · {meta.get('tokens', 0):,} tokens · {meta.get('seconds', 0):.0f}s")
if meta.get("fell_back"):
    st.info(f"The first model declined, so the result was produced by {meta['model']}.")

tabs = st.tabs([":material/view_agenda: Stories", ":material/low_priority: Prioritise",
                ":material/shield: Non-functional", ":material/help: Open questions",
                ":material/groups: Personas & epics", ":material/download: Export"],
               key="results_tab", on_change=analytics.track_widget, args=("tab_viewed", "results_tab", "tab"))
epic_titles = {e["id"]: e["title"] for e in backlog.get("epics", [])}

# Prioritise first, so its edits apply to every other tab and to the exports.
with tabs[1]:
    st.caption("The AI suggests a priority. You decide: change it here and every view and export follows.")
    overview = [{"ID": s["id"], "Story": s["title"], "Epic": epic_titles.get(s["epic_id"], s["epic_id"]),
                 "Priority": s["priority"], "Quality": report.stories[s["id"]].score} for s in stories]
    edited = st.data_editor(
        overview, hide_index=True, disabled=["ID", "Story", "Epic", "Quality"], key=f"prio_{run_id}",
        on_change=lambda: analytics.track("priority_changed", backlog=run_id),
        column_config={
            "Priority": st.column_config.SelectboxColumn(options=PRIORITIES, required=True),
            "Quality": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d"),
        },
    )
    for s, row in zip(stories, edited):
        s["priority"] = row["Priority"]

with tabs[0]:
    filters = st.columns([3, 2])
    epic_choice = filters[0].pills("Epic", ["All", *epic_titles], default="All", key=f"epic_{run_id}",
                                   format_func=lambda e: "All epics" if e == "All" else epic_titles[e],
                                   on_change=analytics.track_widget, args=("epic_filtered", f"epic_{run_id}", "epic")) or "All"
    order = filters[1].segmented_control("Order", ["Backlog order", "Needs attention first"], default="Backlog order",
                                         key=f"order_{run_id}", on_change=analytics.track_widget,
                                         args=("order_changed", f"order_{run_id}", "order")) or "Backlog order"
    shown = [s for s in stories if epic_choice == "All" or s["epic_id"] == epic_choice]
    if order != "Backlog order":
        shown.sort(key=lambda s: report.stories[s["id"]].score)
    for s in shown:
        r = report.stories[s["id"]]
        with st.container(border=True):
            with st.container(horizontal=True, vertical_alignment="center"):
                st.markdown(f"**{s['id']} · {s['title']}**", width="content")
                st.badge(s["priority"], color=PRIORITY_COLOR.get(s["priority"], "gray"))
                q_color = "green" if r.score >= 90 else "orange" if r.score >= 70 else "red"
                st.badge(f"Quality {r.score}", color=q_color, icon=":material/verified:")
                if any(q.status == "missing" for q in r.quotes):
                    st.badge("Unverified quote", color="red", icon=":material/report:")
                if s["epic_id"] in epic_titles:
                    st.badge(epic_titles[s["epic_id"]], color="gray")
            st.markdown(f"> {story_sentence(s)}")
            details_key = f"details_{run_id}_{s['id']}"
            with st.expander("Acceptance criteria, sources and checks", key=details_key,
                             on_change=analytics.track_widget, args=("story_details_opened", details_key, "opened", True),
                             kwargs={"story": s["id"], "backlog": run_id}):
                left, right = st.columns([3, 2], gap="medium")
                with left:
                    st.markdown("**Acceptance criteria**")
                    for ac in s.get("acceptance_criteria", []):
                        st.code(gherkin(ac), language="gherkin")
                    st.markdown(f"**Why this priority:** {s.get('priority_rationale', '')}")
                    if s.get("notes"):
                        st.markdown(f"**Notes:** {s['notes']}")
                with right:
                    st.markdown("**Source quotes**")
                    for qc in r.quotes:
                        st.markdown(f"{QUOTE_ICON[qc.status]} _“{qc.quote}”_", help=QUOTE_HELP[qc.status])
                    st.markdown("**Quality checks**")
                    if not r.issues:
                        st.markdown(":green[:material/check_circle:] No issues found")
                    for issue in r.issues:
                        st.markdown(f"{SEVERITY_ICON[issue.severity]} **{issue.criterion}**: {issue.message}")

with tabs[2]:
    for nfr in backlog.get("non_functional_requirements", []):
        with st.container(border=True):
            with st.container(horizontal=True, vertical_alignment="center"):
                st.markdown(f"**{nfr['id']}**", width="content")
                st.badge(nfr["category"], color="violet")
            st.markdown(nfr["requirement"])
            for qc in report.nfr_quotes.get(nfr["id"], []):
                st.caption(f"{QUOTE_ICON[qc.status]} “{qc.quote}”")
    if not backlog.get("non_functional_requirements"):
        st.write("No non-functional requirements were identified.")

with tabs[3]:
    by_whom: dict[str, list[dict]] = {}
    for q in backlog.get("open_questions", []):
        by_whom.setdefault(q["ask_whom"], []).append(q)
    cols = st.columns(2, gap="medium")
    for i, (whom, questions) in enumerate(by_whom.items()):
        with cols[i % 2].container(border=True):
            st.markdown(f"**Ask {whom}**")
            for q in questions:
                related = f" `{', '.join(q['related_ids'])}`" if q.get("related_ids") else ""
                st.markdown(f"- {q['question']}{related}  \n  :gray[{q['why_it_matters']}]")
    for key, heading in (("assumptions", "Assumptions to validate"), ("out_of_scope", "Out of scope")):
        if backlog.get(key):
            with st.container(border=True):
                st.markdown(f"**{heading}**")
                st.markdown("\n".join(f"- {item}" for item in backlog[key]))

with tabs[4]:
    left, right = st.columns(2, gap="large")
    with left:
        st.markdown("#### Personas")
        for p in backlog.get("personas", []):
            with st.container(border=True):
                st.markdown(f"**{p['name']}**  \n{p['description']}")
    with right:
        st.markdown("#### Epics")
        for e in backlog.get("epics", []):
            count = sum(s["epic_id"] == e["id"] for s in stories)
            with st.container(border=True):
                st.markdown(f"**{e['id']} · {e['title']}** :gray[({count} stories)]  \n{e['goal']}")

with tabs[5]:
    left, right = st.columns([2, 3], gap="large")
    with left:
        st.markdown("**Before you share this draft**")
        for item in [
            "Stories with low quality scores are fixed or removed",
            "Unverified quotes are checked against the interview",
            "Priorities reflect my judgement, not just the AI's suggestion",
            "Open questions are scheduled with the right stakeholder",
            "Assumptions are confirmed or turned into questions",
            "NFRs are reviewed with the team (security, accessibility, data protection)",
        ]:
            st.checkbox(item, key=f"check_{run_id}_{item}", on_change=analytics.track_widget,
                        args=("checklist_ticked", f"check_{run_id}_{item}", "checked"), kwargs={"item": item})
    with right:
        st.markdown("**Download**")
        with st.container(horizontal=True):
            st.download_button("Markdown", to_markdown(backlog), "backlog.md", "text/markdown",
                               icon=":material/description:", on_click=analytics.track,
                               args=("download",), kwargs={"format": "markdown", "backlog": run_id})
            st.download_button("Jira CSV", to_jira_csv(backlog), "backlog_jira.csv", "text/csv",
                               icon=":material/table:", help="Import via Jira → Filters → Import issues from CSV.",
                               on_click=analytics.track, args=("download",), kwargs={"format": "jira_csv", "backlog": run_id})
            st.download_button("JSON", to_json(backlog), "backlog.json", "application/json",
                               icon=":material/data_object:", on_click=analytics.track,
                               args=("download",), kwargs={"format": "json", "backlog": run_id})
        with st.expander("Preview Markdown"):
            st.markdown(to_markdown(backlog))

links = " · ".join(f'<a href="{url}" target="_blank">{name}</a>' for name, url in AUTHOR_LINKS.items() if url)
by = f"Built by {AUTHOR_NAME}" + (f" · {links}" if links else "") if AUTHOR_NAME else "A Product Owner portfolio project"
privacy = ("<br>This demo records anonymous usage statistics (no tracking cookies, no personal data) "
           "to see which features are used." if analytics.enabled() else "")
st.markdown(f'<div class="footer">{by} · The AI drafts, the PO decides.{privacy}</div>', unsafe_allow_html=True)
