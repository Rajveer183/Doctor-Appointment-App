"""Tool schemas + dispatch for the chatbot. Every tool is a thin wrapper around an
existing service-layer function — no booking/cancellation/lookup logic is duplicated
here, so the chatbot can never behave differently from the REST API for the same action.
"""
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import AppError
from app.services import appointments as appointments_service
from app.services import doctors as doctors_service
from app.services import slots as slots_service

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_doctors",
            "description": (
                "Search for doctors, optionally filtered by specialty. Call this before booking to find "
                "a doctor's id. The next_available_slot field is informational only (for display) — it is "
                "NOT a slot_id and cannot be booked directly. Always call get_available_slots to get a "
                "real, bookable slot_id before calling book_appointment."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "specialty": {
                        "type": "string",
                        "description": "e.g. Cardiology, Dermatology, Pediatrics, Orthopedics, General Physician. Omit to list all doctors.",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_available_slots",
            "description": "Get open appointment slots for a specific doctor on a specific date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "doctor_id": {"type": "integer"},
                    "date": {"type": "string", "description": "Date in YYYY-MM-DD format"},
                },
                "required": ["doctor_id", "date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "book_appointment",
            "description": (
                "Book an appointment for the current patient in a specific open slot. slot_id MUST be "
                "an id you obtained from a get_available_slots call in this conversation — never guess "
                "or reuse an id from search_doctors. Always restate the doctor, date, and time and get "
                "explicit confirmation from the patient before calling this."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "slot_id": {"type": "integer", "description": "The slot id from get_available_slots"},
                    "reason": {"type": "string", "description": "Brief reason for the visit"},
                },
                "required": ["slot_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_appointment",
            "description": (
                "Cancel an existing confirmed appointment for the current patient. "
                "Always confirm which appointment with the patient before calling this."
            ),
            "parameters": {
                "type": "object",
                "properties": {"appointment_id": {"type": "integer"}},
                "required": ["appointment_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_my_appointments",
            "description": "List the current patient's own appointments.",
            "parameters": {
                "type": "object",
                "properties": {
                    "upcoming": {
                        "type": "boolean",
                        "description": "true for upcoming confirmed appointments only, false for past/other only, omit for all",
                    }
                },
            },
        },
    },
]


def _iso(dt) -> str | None:
    return dt.isoformat() if dt else None


async def execute_tool(db: AsyncSession, name: str, arguments: dict, patient_id: int) -> dict | list:
    """patient_id is injected from the request context, never taken from the LLM's
    arguments — the model can't book or cancel on behalf of someone else."""
    try:
        if name == "search_doctors":
            doctors = await doctors_service.list_doctors(db, arguments.get("specialty"))
            return [
                {
                    "id": d["id"],
                    "name": d["name"],
                    "specialty": d["specialty"],
                    "experience_years": d["experience_years"],
                    "next_available_slot": _iso(d["next_available_slot"]),
                }
                for d in doctors
            ]

        if name == "get_available_slots":
            day = date.fromisoformat(arguments["date"])
            slots = await slots_service.get_available_slots(db, arguments["doctor_id"], day=day)
            return [{"id": s["id"], "start_datetime": _iso(s["start_datetime"])} for s in slots]

        if name == "book_appointment":
            appt = await appointments_service.book_appointment(
                db, arguments["slot_id"], patient_id, arguments.get("reason", "")
            )
            return {
                "success": True,
                "appointment_id": appt.id,
                "doctor": appt.doctor.name,
                "start_datetime": _iso(appt.slot.start_datetime),
            }

        if name == "cancel_appointment":
            appt = await appointments_service.cancel_appointment(db, arguments["appointment_id"], enforce_window=True)
            return {"success": True, "appointment_id": appt.id, "status": appt.status.value}

        if name == "list_my_appointments":
            upcoming = arguments.get("upcoming")
            appts = await appointments_service.list_patient_appointments(db, patient_id, upcoming)
            return [
                {
                    "id": a.id,
                    "doctor": a.doctor.name,
                    "status": a.status.value,
                    "start_datetime": _iso(a.slot.start_datetime),
                }
                for a in appts
            ]

        return {"error": f"Unknown tool '{name}'"}
    except AppError as exc:
        return {"success": False, "error": exc.message}
