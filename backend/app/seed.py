"""Seed script: wipes and repopulates the SQLite DB with demo data.

Run with: python -m app.seed
"""
import asyncio
from datetime import date, datetime, time, timedelta

from app.database import Base, SessionLocal, engine
from app.models import Appointment, AppointmentStatus, Doctor, DoctorAvailability, Patient, Slot, SlotStatus
from app.utils import local_now

DOCTORS = [
    dict(name="Dr. Ananya Rao", specialty="Cardiology", experience_years=12,
         consultation_duration_minutes=30,
         bio="Interventional cardiologist focused on preventive heart care and hypertension management."),
    dict(name="Dr. Arjun Desai", specialty="Cardiology", experience_years=20,
         consultation_duration_minutes=30,
         bio="Senior cardiologist with two decades of experience in arrhythmia and heart failure care."),
    dict(name="Dr. Vikram Mehta", specialty="Dermatology", experience_years=8,
         consultation_duration_minutes=20,
         bio="Dermatologist specializing in acne, eczema, and skin cancer screening."),
    dict(name="Dr. Priya Nair", specialty="Pediatrics", experience_years=15,
         consultation_duration_minutes=20,
         bio="Pediatrician passionate about childhood development and preventive vaccination care."),
    dict(name="Dr. Rohan Kapoor", specialty="Orthopedics", experience_years=10,
         consultation_duration_minutes=30,
         bio="Orthopedic surgeon treating sports injuries, joint pain, and fractures."),
    dict(name="Dr. Sana Sheikh", specialty="General Physician", experience_years=6,
         consultation_duration_minutes=15,
         bio="General physician providing everyday primary care and checkups for the whole family."),
]

PATIENTS = [
    dict(name="Ravi Kumar", email="ravi.kumar@example.com", phone="9820011122"),
    dict(name="Meera Iyer", email="meera.iyer@example.com", phone="9820011123"),
    dict(name="Kabir Singh", email="kabir.singh@example.com", phone="9820011124"),
    dict(name="Ayesha Khan", email="ayesha.khan@example.com", phone="9820011125"),
    dict(name="Ishaan Verma", email="ishaan.verma@example.com", phone="9820011126"),
    dict(name="Divya Menon", email="divya.menon@example.com", phone="9820011127"),
    dict(name="Aditya Joshi", email="aditya.joshi@example.com", phone="9820011128"),
]

# Mon-Fri, 09:00-13:00 and 14:00-17:00 (lunch break), for every doctor.
WEEKDAY_BLOCKS = [(time(9, 0), time(13, 0)), (time(14, 0), time(17, 0))]

PAST_DAYS = 7
FUTURE_DAYS = 14


async def seed() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as db:
        doctors = [Doctor(**d) for d in DOCTORS]
        db.add_all(doctors)
        await db.flush()

        for doctor in doctors:
            for dow in range(5):  # Mon-Fri
                for start, end in WEEKDAY_BLOCKS:
                    db.add(DoctorAvailability(doctor_id=doctor.id, day_of_week=dow, start_time=start, end_time=end))

        patients = [Patient(**p) for p in PATIENTS]
        db.add_all(patients)
        await db.flush()

        today = date.today()
        all_slots: list[Slot] = []
        for doctor in doctors:
            duration = timedelta(minutes=doctor.consultation_duration_minutes)
            for offset in range(-PAST_DAYS, FUTURE_DAYS):
                day = today + timedelta(days=offset)
                if day.weekday() >= 5:
                    continue
                for start, end in WEEKDAY_BLOCKS:
                    cursor = datetime.combine(day, start)
                    block_end = datetime.combine(day, end)
                    while cursor + duration <= block_end:
                        all_slots.append(
                            Slot(doctor_id=doctor.id, start_datetime=cursor, end_datetime=cursor + duration)
                        )
                        cursor += duration
        db.add_all(all_slots)
        await db.flush()

        now = local_now()
        past_slots = [s for s in all_slots if s.end_datetime < now]
        future_slots = [s for s in all_slots if s.start_datetime > now + timedelta(hours=2)]

        reasons = ["Follow-up consultation", "Routine checkup", "New symptoms", "Second opinion", "Prescription renewal"]

        # A handful of completed / no-show appointments in the past, for dashboard + history views.
        for i, slot in enumerate(past_slots[:5]):
            patient = patients[i % len(patients)]
            status = AppointmentStatus.no_show if i == 2 else AppointmentStatus.completed
            slot.status = SlotStatus.booked
            db.add(Appointment(
                slot_id=slot.id, patient_id=patient.id, doctor_id=slot.doctor_id,
                status=status, reason=reasons[i % len(reasons)],
                created_at=slot.start_datetime - timedelta(days=1),
            ))

        # A handful of confirmed upcoming appointments, so listings/cancel flows have data.
        for i, slot in enumerate(future_slots[:6]):
            patient = patients[(i + 2) % len(patients)]
            slot.status = SlotStatus.booked
            db.add(Appointment(
                slot_id=slot.id, patient_id=patient.id, doctor_id=slot.doctor_id,
                status=AppointmentStatus.confirmed, reason=reasons[i % len(reasons)],
                created_at=local_now() - timedelta(hours=i + 1),
            ))

        # A couple of blocked slots (doctor unavailable), independent of bookings.
        for slot in future_slots[20:22]:
            slot.status = SlotStatus.blocked

        await db.commit()

    print(f"Seeded {len(doctors)} doctors, {len(patients)} patients, {len(all_slots)} slots.")


if __name__ == "__main__":
    asyncio.run(seed())
