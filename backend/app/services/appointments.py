from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.errors import ConflictError, NotFoundError, ValidationError
from app.models import (
    VALID_APPOINTMENT_TRANSITIONS,
    Appointment,
    AppointmentStatus,
    Patient,
    Slot,
    SlotStatus,
)
from app.utils import utc_now

_WITH_RELATIONS = selectinload(Appointment.slot), selectinload(Appointment.doctor), selectinload(Appointment.patient)


async def book_appointment(db: AsyncSession, slot_id: int, patient_id: int, reason: str) -> Appointment:
    slot = await db.get(Slot, slot_id)
    if not slot:
        raise NotFoundError(f"Slot {slot_id} not found")
    patient = await db.get(Patient, patient_id)
    if not patient:
        raise NotFoundError(f"Patient {patient_id} not found")

    # The BEGIN IMMEDIATE behavior configured on the engine (see database.py) means this
    # session's transaction already holds SQLite's write lock by the time the SELECT
    # above ran, so no concurrent request can slip in between this check and the INSERT
    # below. The UNIQUE constraint on appointments.slot_id is kept as a second,
    # DB-enforced guarantee that survives even if that locking strategy ever changes.
    if slot.status != SlotStatus.open:
        raise ConflictError(f"Slot {slot_id} is no longer available")

    appointment = Appointment(slot_id=slot_id, patient_id=patient_id, doctor_id=slot.doctor_id, reason=reason)
    slot.status = SlotStatus.booked
    db.add(appointment)

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError(f"Slot {slot_id} was just booked by someone else") from exc

    result = await db.execute(
        select(Appointment).where(Appointment.id == appointment.id).options(*_WITH_RELATIONS)
    )
    return result.scalar_one()


async def _get_appointment(db: AsyncSession, appointment_id: int) -> Appointment:
    result = await db.execute(
        select(Appointment).where(Appointment.id == appointment_id).options(*_WITH_RELATIONS)
    )
    appointment = result.scalar_one_or_none()
    if not appointment:
        raise NotFoundError(f"Appointment {appointment_id} not found")
    return appointment


async def cancel_appointment(db: AsyncSession, appointment_id: int, enforce_window: bool) -> Appointment:
    appointment = await _get_appointment(db, appointment_id)
    _assert_transition(appointment.status, AppointmentStatus.cancelled)

    if enforce_window:
        cutoff = appointment.slot.start_datetime - timedelta(minutes=settings.cancellation_window_minutes)
        if utc_now() > cutoff:
            raise ConflictError(
                f"Cancellations must be made at least {settings.cancellation_window_minutes} minutes "
                "before the appointment. Please contact the clinic directly."
            )

    appointment.status = AppointmentStatus.cancelled
    appointment.cancelled_at = utc_now()
    appointment.slot.status = SlotStatus.open
    await db.commit()
    return await _get_appointment(db, appointment_id)


async def set_appointment_status(db: AsyncSession, appointment_id: int, new_status: AppointmentStatus) -> Appointment:
    appointment = await _get_appointment(db, appointment_id)
    _assert_transition(appointment.status, new_status)
    appointment.status = new_status
    if new_status == AppointmentStatus.cancelled:
        appointment.cancelled_at = utc_now()
        appointment.slot.status = SlotStatus.open
    await db.commit()
    return await _get_appointment(db, appointment_id)


def _assert_transition(current: AppointmentStatus, new: AppointmentStatus) -> None:
    allowed = VALID_APPOINTMENT_TRANSITIONS.get(current, set())
    if new not in allowed:
        raise ValidationError(f"Cannot move appointment from '{current.value}' to '{new.value}'")


async def list_patient_appointments(db: AsyncSession, patient_id: int, upcoming: bool | None = None) -> list[Appointment]:
    stmt = select(Appointment).where(Appointment.patient_id == patient_id).options(*_WITH_RELATIONS)
    result = await db.execute(stmt)
    appointments = list(result.scalars().all())
    if upcoming is True:
        appointments = [a for a in appointments if a.slot.start_datetime >= utc_now() and a.status == AppointmentStatus.confirmed]
    elif upcoming is False:
        appointments = [a for a in appointments if not (a.slot.start_datetime >= utc_now() and a.status == AppointmentStatus.confirmed)]
    return sorted(appointments, key=lambda a: a.slot.start_datetime, reverse=upcoming is False)


async def list_doctor_schedule(db: AsyncSession, doctor_id: int, day) -> list[Appointment]:
    from datetime import datetime

    start = datetime.combine(day, datetime.min.time())
    end = start + timedelta(days=1)
    stmt = (
        select(Appointment)
        .join(Slot, Appointment.slot_id == Slot.id)
        .where(Appointment.doctor_id == doctor_id, Slot.start_datetime >= start, Slot.start_datetime < end)
        .options(*_WITH_RELATIONS)
    )
    result = await db.execute(stmt)
    return sorted(result.scalars().all(), key=lambda a: a.slot.start_datetime)
