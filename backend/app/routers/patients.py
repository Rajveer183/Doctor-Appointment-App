from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import PatientCreate, PatientOut
from app.services import patients as patients_service

router = APIRouter(tags=["patients"])


@router.get("/patients", response_model=list[PatientOut])
async def get_patients(db: AsyncSession = Depends(get_db)):
    return await patients_service.list_patients(db)


@router.get("/patients/{patient_id}", response_model=PatientOut)
async def get_patient(patient_id: int, db: AsyncSession = Depends(get_db)):
    return await patients_service.get_patient(db, patient_id)


@router.post("/patients", response_model=PatientOut, status_code=201)
async def create_patient(payload: PatientCreate, db: AsyncSession = Depends(get_db)):
    return await patients_service.create_patient(db, payload.name, payload.email, payload.phone)
