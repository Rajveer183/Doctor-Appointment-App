from collections import Counter
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Appointment, AppointmentStatus, Slot, SlotStatus
from app.utils import utc_now


def _time_bucket(dt: datetime) -> str:
    if dt.hour < 12:
        return "morning"
    if dt.hour < 17:
        return "afternoon"
    return "evening"


async def _preferred_bucket(db: AsyncSession, patient_id: int | None) -> str | None:
    """Infer the patient's usual time-of-day from their past confirmed/completed visits."""
    if not patient_id:
        return None
    stmt = (
        select(Slot.start_datetime)
        .join(Appointment, Appointment.slot_id == Slot.id)
        .where(
            Appointment.patient_id == patient_id,
            Appointment.status.in_([AppointmentStatus.completed, AppointmentStatus.confirmed]),
        )
    )
    rows = (await db.execute(stmt)).scalars().all()
    if not rows:
        return None
    counts = Counter(_time_bucket(dt) for dt in rows)
    return counts.most_common(1)[0][0]


async def get_available_slots(
    db: AsyncSession,
    doctor_id: int,
    day: date | None = None,
    patient_id: int | None = None,
    only_open: bool = True,
) -> list[dict]:
    stmt = select(Slot).where(Slot.doctor_id == doctor_id)
    if only_open:
        stmt = stmt.where(Slot.status == SlotStatus.open, Slot.start_datetime > utc_now())
    if day:
        start = datetime.combine(day, datetime.min.time())
        stmt = stmt.where(Slot.start_datetime >= start, Slot.start_datetime < start + timedelta(days=1))
    stmt = stmt.order_by(Slot.start_datetime)

    slots = (await db.execute(stmt)).scalars().all()

    # Base ordering is always soonest-first: patients scanning a list expect the nearest
    # appointment on top, and burying it behind a "preference" heuristic would be surprising.
    # The preference boost only decides which single upcoming slot gets highlighted as
    # "recommended" in the UI, not the sort order itself.
    preferred_bucket = await _preferred_bucket(db, patient_id)
    recommended_id: int | None = None
    if slots:
        recommended_id = slots[0].id
        if preferred_bucket:
            for slot in slots:
                if _time_bucket(slot.start_datetime) == preferred_bucket:
                    recommended_id = slot.id
                    break

    return [{**slot.__dict__, "recommended": slot.id == recommended_id} for slot in slots]
