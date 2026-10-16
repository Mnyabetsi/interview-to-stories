"""Turns a stakeholder interview transcript into a structured backlog draft using Claude."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass

import anthropic

MODELS = {
    "claude-opus-5-5": "Claude Opus 5.5 (best quality)",
    "claude-sonnet-5-5": "Claude Sonnet 5.5 (faster, cheaper)",
    "claude-haiku-5-5": "Claude Haiku 5.5 (cheapest)",
}
DEFAULT_MODEL = "claude-opus-5-5"

# USD per 1M tokens (input, output). Thinking tokens are billed as output.
PRICES = {
    "claude-opus-5-5": (4.00, 20.00),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-haiku-5-5": (0.10, 0.50),
}

# Server-side refusal fallback is not available for Haiku 5.5.
SUPPORTS_FALLBACK = {"claude-opus-5-5", "claude-sonnet-5-5"}

LANGUAGES = {"English": "English", "Deutsch": "German", "Français": "French"}

PRIORITIES = ["Must", "Should", "Could", "Won't"]
NFR_CATEGORIES = [
    "Security", "Privacy", "Accessibility", "Performance", "Availability",
    "Usability", "Compliance", "Integration", "Maintainability", "Other",
]

_quotes = {"type": "array", "items": {"type": "string"}}

BACKLOG_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "summary", "personas", "epics", "stories",
        "non_functional_requirements", "open_questions", "assumptions", "out_of_scope",
    ],
    "properties": {
        "summary": {"type": "string"},
        "personas": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["name", "description"],
                "properties": {"name": {"type": "string"}, "description": {"type": "string"}},
            },
        },
        "epics": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "title", "goal"],
                "properties": {
                    "id": {"type": "string"},
                    "title": {"type": "string"},
                    "goal": {"type": "string"},
                },
            },
        },
        "stories": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "id", "epic_id", "title", "persona", "i_want", "so_that", "statement",
                    "acceptance_criteria", "priority", "priority_rationale",
                    "source_quotes", "notes",
                ],
                "properties": {
                    "id": {"type": "string"},
                    "epic_id": {"type": "string"},
                    "title": {"type": "string"},
                    "persona": {"type": "string"},
                    "i_want": {"type": "string"},
                    "so_that": {"type": "string"},
                    "statement": {"type": "string"},
                    "acceptance_criteria": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["given", "when", "then"],
                            "properties": {
                                "given": {"type": "string"},
                                "when": {"type": "string"},
                                "then": {"type": "string"},
                            },
                        },
                    },
                    "priority": {"type": "string", "enum": PRIORITIES},
                    "priority_rationale": {"type": "string"},
                    "source_quotes": _quotes,
                    "notes": {"type": "string"},
                },
            },
        },
        "non_functional_requirements": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "category", "requirement", "source_quotes"],
                "properties": {
                    "id": {"type": "string"},
                    "category": {"type": "string", "enum": NFR_CATEGORIES},
                    "requirement": {"type": "string"},
                    "source_quotes": _quotes,
                },
            },
        },
        "open_questions": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["question", "why_it_matters", "ask_whom", "related_ids"],
                "properties": {
                    "question": {"type": "string"},
                    "why_it_matters": {"type": "string"},
                    "ask_whom": {"type": "string"},
                    "related_ids": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        "assumptions": {"type": "array", "items": {"type": "string"}},
        "out_of_scope": {"type": "array", "items": {"type": "string"}},
    },
}

SYSTEM_PROMPT = """You are an experienced Scrum Product Owner and IREB-certified Requirements Engineer \
working for a software company that builds applications for public-sector organisations.

You turn a stakeholder interview transcript into a first backlog draft that the Product Owner will \
review. Quality bar:

- Write user stories as "As a <persona>, I want <capability>, so that <benefit>". Split them so each \
one is Independent, Negotiable, Valuable, Estimable, Small and Testable (INVEST). One capability per \
story; prefer several small stories over one large one.
- Fill "persona", "i_want" and "so_that" with the parts of the story, and "statement" with the \
full grammatical sentence in the output language ("As a…, I want…, so that…" / "Als … möchte \
ich …, damit …" / "En tant que…, je veux…, afin de…").
- Use the stakeholders' real roles as personas (e.g. "permit clerk", "applicant"), never "user".
- Write 2-5 acceptance criteria per story in Given/When/Then form. They must be concrete and \
testable: no vague words such as "fast", "easy", "user-friendly", "intuitive" or "etc.". If the \
transcript gives no number, do not invent one - add an open question instead.
- Every story and non-functional requirement must cite 1-3 short source quotes copied VERBATIM \
from the transcript (exact wording, no paraphrasing, no speaker labels, no ellipses). This is how \
the Product Owner traces requirements back to stakeholders, and quotes are checked automatically.
- Only include requirements the transcript supports. Things you infer but nobody said belong in \
"assumptions"; things that are unclear, missing or contradictory belong in "open_questions". \
Explicitly name contradictions between speakers.
- Suggest a MoSCoW priority with a one-sentence rationale grounded in what stakeholders said. \
The Product Owner makes the final call.
- Capture legal and public-sector constraints (data protection, accessibility, retention, \
audit trails, multilingual requirements) as non-functional requirements when mentioned.
- Use IDs E1, E2... for epics, US-1, US-2... for stories, NFR-1, NFR-2... for non-functional \
requirements.
- Use "notes" for dependencies or splitting hints; leave it empty if there are none."""


@dataclass
class GenerationResult:
    data: dict
    model: str
    input_tokens: int
    output_tokens: int
    seconds: float
    fell_back: bool

    @property
    def cost_usd(self) -> float:
        price_in, price_out = PRICES.get(self.model, PRICES[DEFAULT_MODEL])
        return (self.input_tokens * price_in + self.output_tokens * price_out) / 1_000_000


class GenerationError(Exception):
    """A user-presentable error from the generation step."""


def generate_backlog(
    transcript: str,
    *,
    model: str = DEFAULT_MODEL,
    language: str = "English",
    effort: str = "medium",
    context: str = "",
    api_key: str | None = None,
) -> GenerationResult:
    if not transcript.strip():
        raise GenerationError("The transcript is empty.")

    user_message = (
        f"Write all output text in {LANGUAGES.get(language, language)}, but keep source quotes "
        "in the original language of the transcript.\n\n"
        + (f"<project_context>\n{context.strip()}\n</project_context>\n\n" if context.strip() else "")
        + f"<transcript>\n{transcript.strip()}\n</transcript>"
    )
    return request_json(SYSTEM_PROMPT, user_message, BACKLOG_SCHEMA,
                        model=model, effort=effort, api_key=api_key)


def request_json(
    system: str,
    user_message: str,
    schema: dict,
    *,
    model: str = DEFAULT_MODEL,
    effort: str = "medium",
    api_key: str | None = None,
) -> GenerationResult:
    """Sends one request with a JSON-schema output format and returns the parsed object."""
    client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
    request = dict(
        model=model,
        max_tokens=32000,
        system=system,
        output_config={
            "effort": effort,
            "format": {"type": "json_schema", "schema": schema},
        },
        messages=[{"role": "user", "content": user_message}],
    )
    if model in SUPPORTS_FALLBACK:
        request["betas"] = ["server-side-fallback-2026-07-01"]
        request["fallbacks"] = "default"

    started = time.monotonic()
    try:
        with client.beta.messages.stream(**request) as stream:
            message = stream.get_final_message()
    except anthropic.AuthenticationError:
        raise GenerationError("The API key was rejected. Check it in the sidebar.")
    except anthropic.PermissionDeniedError:
        raise GenerationError("This API key doesn't have access to the selected model.")
    except anthropic.NotFoundError:
        raise GenerationError(f"Model '{model}' was not found.")
    except anthropic.RateLimitError:
        raise GenerationError("Rate limit reached. Wait a minute and try again.")
    except anthropic.BadRequestError as e:
        raise GenerationError(f"The request was rejected: {e.message}")
    except anthropic.APIStatusError as e:
        raise GenerationError(f"Claude API error ({e.status_code}). Try again later.")
    except anthropic.APIConnectionError:
        raise GenerationError("Could not reach the Claude API. Check your internet connection.")
    seconds = time.monotonic() - started

    if message.stop_reason == "refusal":
        raise GenerationError("Claude declined this request.")
    if message.stop_reason == "max_tokens":
        raise GenerationError("The response was too long to fit in one reply. Try a shorter transcript.")

    # Text emitted before a fallback switch point belongs to the declined attempt; keep only the last.
    text, fell_back = "", False
    for block in message.content:
        if block.type == "fallback":
            text, fell_back = "", True
        elif block.type == "text":
            text += block.text

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        raise GenerationError("Claude returned output that could not be parsed. Please try again.")

    return GenerationResult(
        data=data,
        model=message.model,
        input_tokens=message.usage.input_tokens,
        output_tokens=message.usage.output_tokens,
        seconds=seconds,
        fell_back=fell_back,
    )
