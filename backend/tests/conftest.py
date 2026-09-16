from datetime import timedelta

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import Base, get_db
from app.main import app
from app.models import Doctor, Patient, Slot, SlotStatus
from app.utils import utc_now


def _apply_sqlite_pragmas(engine):
    """Mirror the BEGIN IMMEDIATE / WAL setup from app.database so tests exercise
    the same locking behavior as production, against an isolated test DB file."""

    @event.listens_for(engine.sync_engine, "connect")
    def _pragmas(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
        dbapi_connection.isolation_level = None

    @event.listens_for(engine.sync_engine, "begin")
    def _begin_immediate(conn):
        conn.exec_driver_sql("BEGIN IMMEDIATE")


@pytest_asyncio.fixture
async def client_with_seed():
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        _apply_sqlite_pragmas(engine)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

        async def override_get_db():
            async with SessionLocal() as session:
                yield session

        app.dependency_overrides[get_db] = override_get_db

        async with SessionLocal() as db:
            doctor = Doctor(
                name="Dr. Test", specialty="General Physician", bio="",
                experience_years=1, consultation_duration_minutes=30,
            )
            db.add(doctor)
            await db.flush()

            patient_a = Patient(name="Patient A", email="patient.a@example.com", phone="1")
            patient_b = Patient(name="Patient B", email="patient.b@example.com", phone="2")
            db.add_all([patient_a, patient_b])
            await db.flush()

            start = utc_now() + timedelta(days=1)
            slot = Slot(doctor_id=doctor.id, start_datetime=start, end_datetime=start + timedelta(minutes=30), status=SlotStatus.open)
            db.add(slot)
            await db.commit()

            ids = {
                "doctor_id": doctor.id,
                "patient_a": patient_a.id,
                "patient_b": patient_b.id,
                "slot_id": slot.id,
            }

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client, ids

        app.dependency_overrides.clear()
        await engine.dispose()
