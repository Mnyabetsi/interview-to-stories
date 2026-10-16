# Product Brief: Interview → User Stories

## Problem
After a stakeholder interview, a Product Owner can spend 1–3 hours turning notes into a usable
backlog: user stories, acceptance criteria, non-functional requirements and the questions
that still need answers. The work is repetitive, and important details get lost along the way.
In the public sector it's harder still. There are many stakeholder groups, legal constraints
(data protection, accessibility, retention rules) and multilingual input (DE/FR/IT/EN).

## Target user
A Scrum Product Owner or Requirements Engineer who works with customers and turns their
needs into a sprint-ready backlog.

## Job to be done
> When I finish a stakeholder interview, I want a first draft of a structured, traceable backlog
> so I can spend my time on clarification and prioritisation instead of typing.

## Product principles
1. **Traceable.** Every story and NFR must cite verbatim quotes from the transcript. The app
   checks that those quotes actually appear in the transcript and flags any that don't.
2. **The PO decides.** The tool drafts and the PO edits, prioritises and owns the result. The AI's
   priority is only a suggestion.
3. **Surface what's unknown.** Open questions, assumptions and contradictions are first-class
   outputs. They are not hidden inside stories.
4. **Privacy by default.** Nothing is stored server-side. Users are told not to paste
   personal data, in line with Switzerland's data protection law (nDSG/revFADP).

## MVP scope

| In scope (v1) | Out of scope (later) |
|---|---|
| Paste or upload a transcript (.txt / .md / .vtt) | Audio → transcript |
| Personas, epics, user stories with Gherkin acceptance criteria | Direct push to Jira / Azure DevOps API |
| Non-functional requirements (security, accessibility, …) | Multi-interview merge and de-duplication |
| Open questions, assumptions, out-of-scope items | Story-point estimation |
| Rule-based INVEST quality checks + quote grounding check | Team-specific Definition of Ready |
| Output in English, German or French | Fine-tuned / on-prem model |
| Export: Markdown, Jira-compatible CSV, JSON | User accounts, history |

## Success metrics
| Metric | Target | How measured | Result (3 sample interviews) |
|---|---|---|---|
| Expected requirements found | ≥ 90% | `eval.py` coverage check against answer keys | 98% |
| Quote grounding rate | ≥ 95% of cited quotes found verbatim | `eval.py` | 100% |
| Average story quality score | ≥ 80 / 100 | `quality.py` rule checks | 97 |
| Stories with ≥ 2 acceptance criteria | ≥ 90% | `eval.py` | 98% |
| Time from transcript to reviewed backlog draft | < 15 min (vs. ~90 min manual) | Self-timed on sample transcripts | Not yet measured |
| Cost per transcript | < USD 0.25 | Token usage reported in the app | USD 0.30 (missed) |

## Backlog for this tool (dogfooding)
- **US-1:** As a PO, I want to paste an interview transcript so that I can get a first backlog draft without retyping notes.
- **US-2:** As a PO, I want every story linked to verbatim quotes so that I can trace requirements back to the stakeholder.
- **US-3:** As a PO, I want quotes that don't appear in the transcript flagged so that I can catch hallucinations before they reach the team.
- **US-4:** As a PO, I want INVEST quality warnings per story so that I know which stories need refinement.
- **US-5:** As a PO, I want open questions grouped per stakeholder so that I can plan my follow-up conversation.
- **US-6:** As a PO, I want to export to Jira CSV so that I can import the draft into the team backlog.
- **US-7:** As a PO in a Swiss multilingual context, I want the output in DE/FR/EN so that it matches my team's language.
- **US-8 (later):** As a PO, I want to merge several interviews so that I can see overlapping and conflicting needs.

## Risks and mitigations
| Risk | Mitigation |
|---|---|
| The AI invents requirements | Quote grounding check; ungrounded items are flagged in red |
| Users paste confidential or personal data | Privacy warning in UI; no storage; bring-your-own API key |
| Output looks "done" and is not reviewed | Positioned as a *draft*; PO review checklist shown in the app |
| API cost | Cost per run shown in the app; model selector |
