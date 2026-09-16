from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import DoctorOut, DoctorWithNextSlot, SlotOut
from app.services import doctors as doctors_service
from app.services import slots as slots_service

router = APIRouter(tags=["doctors"])


@router.get("/specialties", response_model=list[str])
async def get_specialties(db: AsyncSession = Depends(get_db)):
    return await doctors_service.list_specialties(db)


@router.get("/doctors", response_model=list[DoctorWithNextSlot])
async def get_doctors(specialty: str | None = None, db: AsyncSession = Depends(get_db)):
    return await doctors_service.list_doctors(db, specialty)


@router.get("/doctors/{doctor_id}", response_model=DoctorOut)
async def get_doctor(doctor_id: int, db: AsyncSession = Depends(get_db)):
    return await doctors_service.get_doctor(db, doctor_id)


@router.get("/doctors/{doctor_id}/slots", response_model=list[SlotOut])
async def get_doctor_slots(
    doctor_id: int,
    day: date | None = Query(default=None, alias="date"),
    patient_id: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    await doctors_service.get_doctor(db, doctor_id)
    return await slots_service.get_available_slots(db, doctor_id, day=day, patient_id=patient_id)
