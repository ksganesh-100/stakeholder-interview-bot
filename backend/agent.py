"""The SPIN interview agent.

Holds the consultant persona / system prompt and a single function, `run_turn`,
that advances one stakeholder turn: it sends the running transcript to Claude,
handles the optional `save_summary` tool call, and returns the assistant's reply
plus (when finished) the structured summary.

The transcript is owned by the caller (the FastAPI layer persists it to the DB);
this module stays stateless so it works the same locally and on the server.
"""
import os
from typing import Any, Optional

from anthropic import Anthropic

from tools import (
    INTERVIEW_TOOLS,
    SAVE_SYNTHESIS_TOOL,
    SYNTHESIS_SYSTEM_PROMPT,
    build_synthesis_user_message,
)

MODEL = os.environ.get("INTERVIEW_MODEL", "claude-sonnet-4-6")
SYNTHESIS_MODEL = os.environ.get("SYNTHESIS_MODEL", "claude-sonnet-4-6")
MAX_TOKENS = 1024

# Turn at which we start nudging the agent to wrap up, and the hard ceiling.
WRAP_UP_AFTER_TURN = 9
MAX_TURNS = 12

_client: Optional[Anthropic] = None


def get_client() -> Anthropic:
    """Lazily build the Anthropic client so import never requires a key."""
    global _client
    if _client is None:
        _client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


def system_prompt(stakeholder_name: str, stakeholder_role: str) -> str:
    """Build the consultant system prompt for one stakeholder."""
    return f"""You are a warm, sharp pre-engagement consultant running a short discovery \
conversation with {stakeholder_name}, whose role is "{stakeholder_role}". You are \
gathering input ahead of an AI strategy engagement. Several of their colleagues are \
being interviewed too; their answers will be combined to shape the strategy.

Run the conversation using the SPIN structure, but make it feel like a real, \
flowing conversation — never a form or a checklist:

1. SITUATION — understand what they do, their role, their team, and how work flows today.
2. PROBLEM — uncover the friction, inefficiencies, or things that don't work well.
3. IMPLICATION — explore what those problems actually cost: time, money, quality, \
slow or poor decisions, risk, missed opportunities, morale.
4. NEED-PAYOFF — get them to articulate what "good" would look like if this were solved, \
and why that would matter.

Rules of the conversation:
- Ask exactly ONE question at a time. Never list multiple questions or use bullets.
- Always briefly acknowledge or reflect back what they just said before asking the next \
thing. Sound genuinely interested, not scripted.
- Move through the SPIN stages naturally based on their answers — don't announce the stages.
- Probe for specifics and numbers when they're vague ("roughly how many hours a week?", \
"what does that delay cost you?"), but stay conversational.
- Keep your messages short — usually 1-3 sentences. You are guiding, not lecturing.
- This should take about 8 to 12 exchanges. Around exchange 9-10, begin steering toward \
the need-payoff stage and a graceful close.

Wrapping up:
- When you have a clear picture across all four stages, thank them warmly, let them know \
their input will help shape the strategy, and then call the `save_summary` tool with the \
structured summary. Capture their own words and any specifics they gave.
- Do not call `save_summary` until you have genuinely covered situation, problems, \
implications, and desired outcomes.
- After you call `save_summary`, send a brief, warm closing message."""


def _serialize(content: Any) -> list[dict[str, Any]]:
    """Convert SDK content blocks to plain JSON-safe dicts for storage/replay.

    The Anthropic API accepts these dicts as input on the next turn, so the
    transcript round-trips cleanly through the JSON database column.
    """
    out = []
    for block in content:
        out.append(block.model_dump() if hasattr(block, "model_dump") else block)
    return out


def _wrap_up_nudge(turn_count: int) -> Optional[dict[str, Any]]:
    """A system-style reminder injected late in the conversation to force a close."""
    if turn_count >= MAX_TURNS:
        text = (
            "[Internal note: this conversation has run long. Wrap up now — give a warm "
            "closing line and call save_summary with everything gathered so far.]"
        )
    elif turn_count >= WRAP_UP_AFTER_TURN:
        text = (
            "[Internal note: you're near the end of the conversation. If you have enough "
            "across all four SPIN stages, move toward need-payoff and prepare to wrap up "
            "and call save_summary soon.]"
        )
    else:
        return None
    return {"role": "user", "content": text}


def run_turn(
    transcript: list[dict[str, Any]],
    stakeholder_name: str,
    stakeholder_role: str,
    turn_count: int,
) -> dict[str, Any]:
    """Advance one assistant turn.

    `transcript` already includes the latest user message. Returns:
        {
          "reply": str,                 # assistant text to show
          "transcript": list,           # updated transcript to persist
          "done": bool,                 # True once save_summary was called
          "summary": dict | None,       # structured summary when done
        }
    """
    client = get_client()
    system = system_prompt(stakeholder_name, stakeholder_role)

    # Work on a copy; only persist real conversation turns, not the transient nudge.
    messages = list(transcript)
    nudge = _wrap_up_nudge(turn_count)
    if nudge:
        messages = messages + [nudge]

    summary: Optional[dict[str, Any]] = None
    reply_text = ""

    # Agentic loop: the model may emit text and/or call save_summary.
    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system,
            tools=INTERVIEW_TOOLS,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": _serialize(response.content)})

        for block in response.content:
            if block.type == "text":
                reply_text += block.text

        if response.stop_reason != "tool_use":
            break

        # Handle tool calls (only save_summary exists).
        tool_results = []
        for block in response.content:
            if block.type == "tool_use" and block.name == "save_summary":
                summary = dict(block.input)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": "Summary saved. Thank the stakeholder and close warmly.",
                    }
                )
        messages.append({"role": "user", "content": tool_results})

    # Persist everything except the transient nudge message.
    persisted = [m for m in messages if m is not nudge]

    return {
        "reply": reply_text.strip(),
        "transcript": persisted,
        "done": summary is not None,
        "summary": summary,
    }


def run_synthesis(interviews: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate completed interview summaries into the AI strategy compass.

    `interviews` is a list of {name, role, summary} dicts.
    """
    client = get_client()
    response = client.messages.create(
        model=SYNTHESIS_MODEL,
        max_tokens=2048,
        system=SYNTHESIS_SYSTEM_PROMPT,
        tools=[SAVE_SYNTHESIS_TOOL],
        tool_choice={"type": "tool", "name": "save_synthesis"},
        messages=[{"role": "user", "content": build_synthesis_user_message(interviews)}],
    )
    for block in response.content:
        if block.type == "tool_use" and block.name == "save_synthesis":
            return dict(block.input)
    raise RuntimeError("Synthesis model did not return a save_synthesis tool call.")
