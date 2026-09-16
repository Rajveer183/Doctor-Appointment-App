from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import ConflictError, NotFoundError
from app.models import Patient


async def list_patients(db: AsyncSession) -> list[Patient]:
    result = await db.execute(select(Patient).order_by(Patient.name))
    return list(result.scalars().all())


async def get_patient(db: AsyncSession, patient_id: int) -> Patient:
    patient = await db.get(Patient, patient_id)
    if not patient:
        raise NotFoundError(f"Patient {patient_id} not found")
    return patient


async def create_patient(db: AsyncSession, name: str, email: str, phone: str) -> Patient:
    patient = Patient(name=name, email=email, phone=phone)
    db.add(patient)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError(f"A patient with email {email} already exists") from exc
    await db.refresh(patient)
    return patient
