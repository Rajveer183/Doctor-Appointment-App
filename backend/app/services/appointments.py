from datetime import datetime, timedelta

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
from app.utils import local_now

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

    # A patient can't be in two places at once — block overlap against *any* doctor's
    # confirmed appointment, not just this one (covers "different doctors at the same
    # time" too). There's no UNIQUE constraint that can express "no overlapping time
    # range", so this relies entirely on the BEGIN IMMEDIATE transaction lock above for
    # race-safety: two concurrent booking requests for the same patient serialize
    # instead of both passing this check before either commits.
    overlap_stmt = (
        select(Appointment)
        .join(Slot, Appointment.slot_id == Slot.id)
        .where(
            Appointment.patient_id == patient_id,
            Appointment.status == AppointmentStatus.confirmed,
            Slot.start_datetime < slot.end_datetime,
            Slot.end_datetime > slot.start_datetime,
        )
    )
    conflicting = (await db.execute(overlap_stmt)).scalars().first()
    if conflicting:
        with_whom = "this doctor" if conflicting.doctor_id == slot.doctor_id else "another doctor"
        raise ConflictError(f"You already have an appointment with {with_whom} that overlaps with this time slot.")

    # A patient can't hold two separate appointments with the same doctor on the same
    # calendar day, even at non-overlapping times (e.g. 9am and 3pm) — one visit per
    # doctor per day.
    day_start = datetime.combine(slot.start_datetime.date(), datetime.min.time())
    day_end = day_start + timedelta(days=1)
    same_day_stmt = (
        select(Appointment)
        .join(Slot, Appointment.slot_id == Slot.id)
        .where(
            Appointment.patient_id == patient_id,
            Appointment.doctor_id == slot.doctor_id,
            Appointment.status == AppointmentStatus.confirmed,
            Slot.start_datetime >= day_start,
            Slot.start_datetime < day_end,
        )
    )
    same_day_conflict = (await db.execute(same_day_stmt)).scalars().first()
    if same_day_conflict:
        raise ConflictError("You already have an appointment with this doctor on this day.")

    # Defense in depth: two confirmed appointments for the same doctor should never
    # overlap in time anyway, since slots for one doctor are generated without overlap
    # and each slot can back at most one appointment (UNIQUE constraint). This check
    # doesn't rely on either of those holding — it independently guarantees the rule
    # even if slot generation or the schema ever changes.
    doctor_overlap_stmt = (
        select(Appointment)
        .join(Slot, Appointment.slot_id == Slot.id)
        .where(
            Slot.doctor_id == slot.doctor_id,
            Appointment.status == AppointmentStatus.confirmed,
            Slot.start_datetime < slot.end_datetime,
            Slot.end_datetime > slot.start_datetime,
        )
    )
    doctor_conflict = (await db.execute(doctor_overlap_stmt)).scalars().first()
    if doctor_conflict:
        raise ConflictError("This doctor already has another appointment at that time.")

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


async def get_appointment(db: AsyncSession, appointment_id: int) -> Appointment:
    return await _get_appointment(db, appointment_id)


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
        if local_now() > cutoff:
            raise ConflictError(
                f"Cancellations must be made at least {settings.cancellation_window_minutes} minutes "
                "before the appointment. Please contact the clinic directly."
            )

    appointment.status = AppointmentStatus.cancelled
    appointment.cancelled_at = local_now()
    appointment.slot.status = SlotStatus.open
    await db.commit()
    return await _get_appointment(db, appointment_id)


async def set_appointment_status(db: AsyncSession, appointment_id: int, new_status: AppointmentStatus) -> Appointment:
    appointment = await _get_appointment(db, appointment_id)
    _assert_transition(appointment.status, new_status)
    appointment.status = new_status
    if new_status == AppointmentStatus.cancelled:
        appointment.cancelled_at = local_now()
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
        appointments = [a for a in appointments if a.slot.start_datetime >= local_now() and a.status == AppointmentStatus.confirmed]
    elif upcoming is False:
        appointments = [a for a in appointments if not (a.slot.start_datetime >= local_now() and a.status == AppointmentStatus.confirmed)]
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
