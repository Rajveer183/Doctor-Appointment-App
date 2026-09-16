from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import AppointmentOut, AppointmentStatusUpdate
from app.services import appointments as appointments_service

router = APIRouter(tags=["dashboard"])


@router.get("/doctors/{doctor_id}/schedule", response_model=list[AppointmentOut])
async def get_doctor_schedule(doctor_id: int, day: date, db: AsyncSession = Depends(get_db)):
    return await appointments_service.list_doctor_schedule(db, doctor_id, day)


@router.patch("/appointments/{appointment_id}/status", response_model=AppointmentOut)
async def update_appointment_status(appointment_id: int, payload: AppointmentStatusUpdate, db: AsyncSession = Depends(get_db)):
    """Doctor/admin path: completes, marks no-show, or cancels — bypasses the patient cancellation window."""
    return await appointments_service.set_appointment_status(db, appointment_id, payload.status)
