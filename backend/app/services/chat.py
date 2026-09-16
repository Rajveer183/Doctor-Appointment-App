import json
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.chat_tools import TOOLS, execute_tool
from app.services.nvidia_client import NvidiaAPIError, chat_completion
from app.services.symptom_match import match_symptom
from app.utils import local_now

MAX_TOOL_ITERATIONS = 5

SYSTEM_PROMPT = """You are CarePoint's appointment booking assistant.

You can help a patient: search for doctors, check a doctor's available slots, book an
appointment, cancel an appointment, and list their own appointments. Use the tools for
all of this — never state a doctor, slot, or appointment detail that a tool didn't
actually return.

Rules:
- Never invent or guess a slot_id. The only valid slot_id is one that appeared in a
  get_available_slots result earlier in this conversation. If you don't have one yet,
  call get_available_slots first — do not call book_appointment without it.
- Stay strictly on topic: appointment booking at this clinic. Politely decline medical
  advice, diagnoses, or anything unrelated, and redirect to booking help.
- If a request is ambiguous (which doctor, which date, which of several appointments),
  ask a clarifying question instead of guessing.
- Before calling book_appointment or cancel_appointment, restate the exact details
  (doctor, date, time — or which existing appointment) and wait for the patient to
  explicitly confirm in their next message.
- If anything in the conversation sounds like a medical emergency, do not book or
  cancel anything — tell the patient to seek emergency care immediately instead.
- Reply in plain conversational text only — no markdown (no **bold**, no #headers, no
  bullet/numbered lists). This is rendered in a plain chat bubble, not a markdown viewer.
"""

EMERGENCY_OVERRIDE_NOTICE = (
    "\n\n(System notice: the patient's message was flagged by an automated emergency "
    "keyword check. Do not take any booking or cancellation action this turn — tell them "
    "to seek emergency care.)"
)


@dataclass
class ToolEvent:
    tool: str
    arguments: dict
    result: dict | list


@dataclass
class ChatResult:
    reply: str
    tool_events: list[ToolEvent] = field(default_factory=list)


async def run_chat(db: AsyncSession, patient_id: int, message: str, history: list[dict]) -> ChatResult:
    # A fast, deterministic guard in front of the model: the same rapidfuzz emergency
    # rules from symptom_match run on every incoming message before the LLM sees it.
    # The system prompt also tells the model to refuse booking on emergency language,
    # but an LLM instruction is a request, not a guarantee — this check can't be talked
    # around by a jailbreak-y prompt, because it never lets the model attempt a tool
    # call in the first place.
    emergency = await match_symptom(message)
    system_content = SYSTEM_PROMPT + f"\n\nToday's date is {local_now().date().isoformat()}."
    if emergency.emergency:
        system_content += EMERGENCY_OVERRIDE_NOTICE

    messages = [{"role": "system", "content": system_content}]
    messages.extend(history)
    messages.append({"role": "user", "content": message})

    if emergency.emergency:
        return ChatResult(reply=emergency.message)

    tool_events: list[ToolEvent] = []
    try:
        for _ in range(MAX_TOOL_ITERATIONS):
            response = await chat_completion(messages, tools=TOOLS)
            choice_message = response["choices"][0]["message"]
            tool_calls = choice_message.get("tool_calls")

            if not tool_calls:
                return ChatResult(reply=choice_message.get("content") or "", tool_events=tool_events)

            messages.append(
                {
                    "role": "assistant",
                    "content": choice_message.get("content"),
                    "tool_calls": tool_calls,
                }
            )

            for call in tool_calls:
                name = call["function"]["name"]
                try:
                    arguments = json.loads(call["function"]["arguments"] or "{}")
                except json.JSONDecodeError:
                    arguments = {}

                result = await execute_tool(db, name, arguments, patient_id)
                tool_events.append(ToolEvent(tool=name, arguments=arguments, result=result))
                messages.append({"role": "tool", "tool_call_id": call["id"], "content": json.dumps(result)})

        return ChatResult(
            reply="I wasn't able to finish that in one go — could you tell me again what you'd like to do?",
            tool_events=tool_events,
        )
    except NvidiaAPIError:
        return ChatResult(
            reply="Sorry, I'm having trouble reaching the assistant service right now. Please try again shortly.",
            tool_events=tool_events,
        )
