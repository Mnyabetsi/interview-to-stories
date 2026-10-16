"""Export a backlog to Markdown, Jira-compatible CSV and JSON."""

from __future__ import annotations

import csv
import io
import json

# MoSCoW -> Jira default priority scheme
JIRA_PRIORITY = {"Must": "Highest", "Should": "High", "Could": "Medium", "Won't": "Lowest"}


def story_sentence(story: dict) -> str:
    if story.get("statement"):
        return story["statement"]
    article = "an" if story["persona"][:1].lower() in "aeiou" else "a"
    return f"As {article} {story['persona']}, I want {story['i_want']}, so that {story['so_that']}."


def gherkin(ac: dict) -> str:
    return f"Given {ac['given']}\nWhen {ac['when']}\nThen {ac['then']}"


def to_markdown(backlog: dict, title: str = "Backlog draft") -> str:
    lines = [f"# {title}", "", backlog.get("summary", ""), ""]

    if backlog.get("personas"):
        lines += ["## Personas", ""]
        lines += [f"- **{p['name']}**: {p['description']}" for p in backlog["personas"]]
        lines.append("")

    stories_by_epic: dict[str, list[dict]] = {}
    for s in backlog.get("stories", []):
        stories_by_epic.setdefault(s.get("epic_id", ""), []).append(s)

    epics = backlog.get("epics", [])
    known_epic_ids = {e["id"] for e in epics}
    orphan = [s for eid, ss in stories_by_epic.items() if eid not in known_epic_ids for s in ss]
    sections = [(f"{e['id']}: {e['title']}", e.get("goal", ""), stories_by_epic.get(e["id"], [])) for e in epics]
    if orphan:
        sections.append(("Other stories", "", orphan))

    lines += ["## User stories", ""]
    for heading, goal, stories in sections:
        lines += [f"### {heading}", ""]
        if goal:
            lines += [f"_{goal}_", ""]
        for s in stories:
            lines += [
                f"#### {s['id']}: {s['title']}  `{s['priority']}`",
                "",
                story_sentence(s),
                "",
                "**Acceptance criteria**",
                "",
            ]
            for ac in s.get("acceptance_criteria", []):
                lines += ["```gherkin", gherkin(ac), "```"]
            lines.append("")
            if s.get("source_quotes"):
                lines += ["**Source quotes**", ""] + [f"> {q}" for q in s["source_quotes"]] + [""]
            lines.append(f"**Priority rationale:** {s.get('priority_rationale', '')}")
            if s.get("notes"):
                lines.append(f"  \n**Notes:** {s['notes']}")
            lines.append("")

    if backlog.get("non_functional_requirements"):
        lines += ["## Non-functional requirements", "", "| ID | Category | Requirement |", "|---|---|---|"]
        lines += [f"| {n['id']} | {n['category']} | {n['requirement']} |" for n in backlog["non_functional_requirements"]]
        lines.append("")

    if backlog.get("open_questions"):
        lines += ["## Open questions", ""]
        for q in backlog["open_questions"]:
            related = f" (re: {', '.join(q['related_ids'])})" if q.get("related_ids") else ""
            lines.append(f"- [ ] **{q['question']}**{related}. Ask: {q['ask_whom']}. _{q['why_it_matters']}_")
        lines.append("")

    for key, heading in (("assumptions", "Assumptions"), ("out_of_scope", "Out of scope")):
        if backlog.get(key):
            lines += [f"## {heading}", ""] + [f"- {item}" for item in backlog[key]] + [""]

    return "\n".join(lines)


def to_jira_csv(backlog: dict) -> str:
    """CSV for Jira's 'Import issues from CSV' wizard. Epics are imported as labels for portability."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Summary", "Issue Type", "Priority", "Labels", "Description"])
    epic_titles = {e["id"]: e["title"] for e in backlog.get("epics", [])}
    for s in backlog.get("stories", []):
        criteria = "\n\n".join(gherkin(ac) for ac in s.get("acceptance_criteria", []))
        quotes = "\n".join(f"bq. {q}" for q in s.get("source_quotes", []))
        description = (
            f"{story_sentence(s)}\n\nh3. Acceptance criteria\n{{code:gherkin}}\n{criteria}\n{{code}}\n\n"
            f"h3. Source quotes\n{quotes}\n\n*Priority rationale:* {s.get('priority_rationale', '')}"
        )
        if s.get("notes"):
            description += f"\n\n*Notes:* {s['notes']}"
        epic_label = epic_titles.get(s.get("epic_id", ""), s.get("epic_id", "")).replace(" ", "-")
        writer.writerow([f"{s['id']} {s['title']}", "Story", JIRA_PRIORITY.get(s["priority"], "Medium"),
                         epic_label, description])
    return buffer.getvalue()


def to_json(backlog: dict) -> str:
    return json.dumps(backlog, indent=2, ensure_ascii=False)
