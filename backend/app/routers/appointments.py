from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import AppointmentCreate, AppointmentOut
from app.services import appointments as appointments_service

router = APIRouter(tags=["appointments"])


@router.post("/appointments", response_model=AppointmentOut, status_code=201)
async def create_appointment(payload: AppointmentCreate, db: AsyncSession = Depends(get_db)):
    return await appointments_service.book_appointment(db, payload.slot_id, payload.patient_id, payload.reason)


@router.patch("/appointments/{appointment_id}/cancel", response_model=AppointmentOut)
async def cancel_appointment(appointment_id: int, db: AsyncSession = Depends(get_db)):
    """Patient-facing cancel — rejected inside the cancellation window."""
    return await appointments_service.cancel_appointment(db, appointment_id, enforce_window=True)


@router.get("/patients/{patient_id}/appointments", response_model=list[AppointmentOut])
async def get_patient_appointments(patient_id: int, upcoming: bool | None = None, db: AsyncSession = Depends(get_db)):
    return await appointments_service.list_patient_appointments(db, patient_id, upcoming)
