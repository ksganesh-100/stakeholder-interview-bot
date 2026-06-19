"""Tool definitions and prompt builders.

The interview agent has exactly one tool: `save_summary`. The model calls it
when it has gathered enough to wrap up, producing the structured JSON we
aggregate across stakeholders. Using a tool (rather than parsing free text)
guarantees the output matches the schema.

This module also builds the cross-stakeholder synthesis prompt used by the
admin "AI strategy compass" endpoint.
"""
import json
from typing import Any

# ── Interview tool ────────────────────────────────────────────────────────────

SAVE_SUMMARY_TOOL = {
    "name": "save_summary",
    "description": (
        "Save the final structured summary of the stakeholder interview. "
        "Call this exactly once, at the very end of the conversation, after you "
        "have explored the stakeholder's situation, problems, the implications of "
        "those problems, and what a good outcome would look like. Capture the "
        "stakeholder's own words and specifics (numbers, time, cost, decisions) "
        "where given."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "stakeholder_role": {
                "type": "string",
                "description": "The stakeholder's role and what their team does.",
            },
            "situation": {
                "type": "string",
                "description": "A concise narrative of their current situation, "
                "responsibilities, and how work flows today.",
            },
            "problems": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Distinct pain points, frictions, or inefficiencies they raised.",
            },
            "implications": {
                "type": "array",
                "items": {"type": "string"},
                "description": "What those problems cost them — time, money, quality, "
                "missed/slow decisions, risk, morale. Be specific where they were.",
            },
            "desired_outcomes": {
                "type": "array",
                "items": {"type": "string"},
                "description": "What 'good' would look like if the problems were solved — "
                "the payoff they described or implied.",
            },
        },
        "required": [
            "stakeholder_role",
            "situation",
            "problems",
            "implications",
            "desired_outcomes",
        ],
    },
}

INTERVIEW_TOOLS = [SAVE_SUMMARY_TOOL]


# ── Synthesis prompt ────────────────────────────────────────────────────────────

SYNTHESIS_SYSTEM_PROMPT = (
    "You are a senior AI strategy consultant. You are given the structured "
    "discovery summaries from several stakeholder interviews conducted before an "
    "AI strategy engagement. Synthesise them into a single cross-cutting view — "
    "an 'AI strategy compass' — that the engagement team will use to prioritise. "
    "Look for patterns across stakeholders, not just a restatement of each one. "
    "Be concrete and decision-useful. Ground every AI opportunity in problems and "
    "implications that stakeholders actually raised. You must respond by calling "
    "the save_synthesis tool."
)

SAVE_SYNTHESIS_TOOL = {
    "name": "save_synthesis",
    "description": "Save the cross-stakeholder AI strategy synthesis.",
    "input_schema": {
        "type": "object",
        "properties": {
            "engagement_overview": {
                "type": "string",
                "description": "2-4 sentences framing the engagement based on what "
                "stakeholders collectively said.",
            },
            "common_problems": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Problems that recur across multiple stakeholders.",
            },
            "cross_cutting_implications": {
                "type": "array",
                "items": {"type": "string"},
                "description": "The business impact that shows up across the organisation.",
            },
            "shared_desired_outcomes": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Outcomes multiple stakeholders want.",
            },
            "ai_opportunities": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "rationale": {"type": "string"},
                        "stakeholders_affected": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["title", "rationale", "stakeholders_affected"],
                },
                "description": "Prioritised AI opportunities grounded in the discovery.",
            },
            "quick_wins": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Low-effort, high-signal actions to start with.",
            },
            "open_questions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Gaps or questions to resolve before committing to a roadmap.",
            },
        },
        "required": [
            "engagement_overview",
            "common_problems",
            "cross_cutting_implications",
            "shared_desired_outcomes",
            "ai_opportunities",
            "quick_wins",
            "open_questions",
        ],
    },
}


def build_synthesis_user_message(interviews: list[dict[str, Any]]) -> str:
    """Render completed interview summaries into a single prompt payload.

    `interviews` is a list of {name, role, summary} dicts.
    """
    blocks = []
    for i, item in enumerate(interviews, start=1):
        summary = json.dumps(item["summary"], indent=2, ensure_ascii=False)
        blocks.append(
            f"### Stakeholder {i}: {item['name']} ({item['role']})\n{summary}"
        )
    joined = "\n\n".join(blocks)
    return (
        f"Here are {len(interviews)} stakeholder discovery summaries from this "
        f"engagement.\n\n{joined}\n\n"
        "Synthesise them into the AI strategy compass by calling save_synthesis."
    )
