from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import NotFoundError
from app.models import Doctor, Slot, SlotStatus
from app.utils import utc_now


async def list_doctors(db: AsyncSession, specialty: str | None = None) -> list[dict]:
    stmt = select(Doctor)
    if specialty:
        stmt = stmt.where(Doctor.specialty == specialty)
    doctors = (await db.execute(stmt.order_by(Doctor.name))).scalars().all()

    next_slot_stmt = (
        select(Slot.doctor_id, func.min(Slot.start_datetime))
        .where(Slot.status == SlotStatus.open, Slot.start_datetime > utc_now())
        .group_by(Slot.doctor_id)
    )
    next_slot_by_doctor = {row[0]: row[1] for row in (await db.execute(next_slot_stmt)).all()}

    return [
        {**doctor.__dict__, "next_available_slot": next_slot_by_doctor.get(doctor.id)}
        for doctor in doctors
    ]


async def get_doctor(db: AsyncSession, doctor_id: int) -> Doctor:
    doctor = await db.get(Doctor, doctor_id)
    if not doctor:
        raise NotFoundError(f"Doctor {doctor_id} not found")
    return doctor


async def list_specialties(db: AsyncSession) -> list[str]:
    rows = (await db.execute(select(Doctor.specialty).distinct().order_by(Doctor.specialty))).all()
    return [r[0] for r in rows]
